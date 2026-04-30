"""EC2 security checker for AWS Guardian"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Tuple

from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)


class EC2Checker:
    def __init__(self, authorized_regions: List[str] = None):
        self.ec2_client = AWSClientProvider.get_client('ec2')
        self.authorized_regions = authorized_regions or []
        self.ssm_client = AWSClientProvider.get_client('ssm')
        self.is_localstack = Config.is_localstack()

    def get_all_instances(self) -> Dict[str, List[Dict]]:
        instances_by_region = {}

        try:
            if self.is_localstack:
                regions = ['us-east-1']
                logger.info("[LocalStack] Using single region: %s", regions[0])
            else:
                regions_response = self.ec2_client.describe_regions()
                regions = [r['RegionName'] for r in regions_response['Regions']]

            for region in regions:
                regional_ec2 = AWSClientProvider.get_client('ec2', region=region)
                try:
                    response = regional_ec2.describe_instances(
                        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
                    )

                    instances = []
                    for reservation in response['Reservations']:
                        instances.extend(reservation['Instances'])

                    if instances:
                        instances_by_region[region] = instances
                except Exception as e:
                    logger.error("Error checking region %s: %s", region, e)

            return instances_by_region
        except Exception as e:
            logger.error("Error getting all instances: %s", e)
            return {}

    def get_unauthorized_regions_instances(self) -> Dict[str, List[Dict]]:
        if not self.authorized_regions:
            return {}

        all_instances = self.get_all_instances()
        return {
            region: instances
            for region, instances in all_instances.items()
            if region not in self.authorized_regions
        }

    def check_security_group_exposure(self, instance: Dict) -> List[Dict]:
        exposed_rules = []

        for sg in instance.get('SecurityGroups', []):
            sg_id = sg['GroupId']
            try:
                region = instance['Placement']['AvailabilityZone'][:-1]
                regional_ec2 = AWSClientProvider.get_client('ec2', region=region)
                sg_response = regional_ec2.describe_security_groups(GroupIds=[sg_id])

                for sg_detail in sg_response['SecurityGroups']:
                    for rule in sg_detail.get('IpPermissions', []):
                        for ip_range in rule.get('IpRanges', []):
                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                exposed_rules.append({
                                    'group_id': sg_id,
                                    'group_name': sg_detail['GroupName'],
                                    'protocol': rule.get('IpProtocol', 'N/A'),
                                    'from_port': rule.get('FromPort'),
                                    'to_port': rule.get('ToPort'),
                                    'cidr': '0.0.0.0/0'
                                })
            except Exception as e:
                logger.error("Error checking security group %s: %s", sg_id, e)

        return exposed_rules

    def get_new_instances(self) -> List[Dict]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)

        all_instances = self.get_all_instances()
        new_instances = []

        for region, instances in all_instances.items():
            for instance in instances:
                launch_time = instance['LaunchTime']
                if hasattr(launch_time, 'replace') and launch_time.tzinfo is not None:
                    launch_time = launch_time.replace(tzinfo=None)

                if launch_time > cutoff_time.replace(tzinfo=None):
                    new_instances.append({
                        'instance_id': instance['InstanceId'],
                        'instance_type': instance['InstanceType'],
                        'region': region,
                        'launch_time': launch_time.isoformat(),
                        'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])},
                        'owner': instance.get('OwnerAlias', 'Unknown')
                    })

        return new_instances

    def check_ec2_anomalies(self) -> Tuple[bool, Dict[str, Any]]:
        anomalies = []
        result = {
            'is_anomaly': False,
            'unauthorized_region_instances': [],
            'exposed_instances': [],
            'new_instances': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        if self.authorized_regions:
            unauthorized = self.get_unauthorized_regions_instances()
            if unauthorized:
                result['unauthorized_region_instances'] = unauthorized
                anomalies.append(f"Instances running in unauthorized regions: {list(unauthorized.keys())}")

        all_instances = self.get_all_instances()
        for region, instances in all_instances.items():
            for instance in instances:
                exposed_rules = self.check_security_group_exposure(instance)
                if exposed_rules:
                    result['exposed_instances'].append({
                        'instance_id': instance['InstanceId'],
                        'region': region,
                        'exposed_rules': exposed_rules
                    })
                    anomalies.append(f"Instance {instance['InstanceId']} has 0.0.0.0/0 exposure")

        new_instances = self.get_new_instances()
        if new_instances:
            result['new_instances'] = new_instances
            anomalies.append(f"Detected {len(new_instances)} new instances")

        result['is_anomaly'] = len(anomalies) > 0
        result['anomalies'] = anomalies

        return result['is_anomaly'], result

    def stop_instance(self, instance_id: str, region: str) -> bool:
        try:
            regional_ec2 = AWSClientProvider.get_client('ec2', region=region)
            regional_ec2.stop_instances(InstanceIds=[instance_id])
            return True
        except Exception as e:
            logger.error("Error stopping instance %s: %s", instance_id, e)
            return False

    def set_authorized_regions(self, regions: List[str]) -> None:
        try:
            self.ssm_client.put_parameter(
                Name='/guardian/authorized-regions',
                Value=','.join(regions),
                Type='String',
                Overwrite=True
            )
            self.authorized_regions = regions
        except Exception as e:
            logger.error("Error setting authorized regions: %s", e)

    def get_authorized_regions(self) -> List[str]:
        try:
            response = self.ssm_client.get_parameter(
                Name='/guardian/authorized-regions'
            )
            self.authorized_regions = response['Parameter']['Value'].split(',')
            return self.authorized_regions
        except self.ssm_client.exceptions.ParameterNotFound:
            return self.authorized_regions
        except Exception as e:
            logger.warning("Error getting authorized regions from SSM: %s", e)
            return self.authorized_regions
