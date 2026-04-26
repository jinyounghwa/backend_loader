"""EC2 security checker for AWS Guardian"""
import boto3
from typing import Dict, List, Any, Tuple
from datetime import datetime

class EC2Checker:
    def __init__(self, authorized_regions: List[str] = None):
        """
        Initialize EC2 checker

        Args:
            authorized_regions: List of allowed regions (default: all regions)
        """
        self.ec2_client = boto3.client('ec2')
        self.authorized_regions = authorized_regions or []
        self.ssm_client = boto3.client('ssm')

    def get_all_instances(self) -> Dict[str, List[Dict]]:
        """Get all running EC2 instances across regions"""
        instances_by_region = {}

        try:
            # Get all regions
            regions_response = self.ec2_client.describe_regions()
            regions = [r['RegionName'] for r in regions_response['Regions']]

            for region in regions:
                regional_ec2 = boto3.client('ec2', region_name=region)
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
                    print(f"Error checking region {region}: {e}")

            return instances_by_region
        except Exception as e:
            print(f"Error getting all instances: {e}")
            return {}

    def get_unauthorized_regions_instances(self) -> Dict[str, List[Dict]]:
        """Get instances running in unauthorized regions"""
        if not self.authorized_regions:
            return {}

        all_instances = self.get_all_instances()
        unauthorized = {}

        for region, instances in all_instances.items():
            if region not in self.authorized_regions:
                unauthorized[region] = instances

        return unauthorized

    def check_security_group_exposure(self, instance: Dict) -> List[Dict]:
        """Check if instance security groups expose ports to 0.0.0.0/0"""
        exposed_rules = []

        for sg in instance.get('SecurityGroups', []):
            sg_id = sg['GroupId']
            try:
                regional_ec2 = boto3.client('ec2',
                                           region_name=instance['Placement']['AvailabilityZone'][:-1])
                sg_response = regional_ec2.describe_security_groups(
                    GroupIds=[sg_id]
                )

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
                print(f"Error checking security group {sg_id}: {e}")

        return exposed_rules

    def get_new_instances(self) -> List[Dict]:
        """Detect new running instances (launched in last hour)"""
        new_instances = []
        cutoff_time = datetime.utcnow()
        one_hour_ago = cutoff_time.replace(hour=cutoff_time.hour - 1) if cutoff_time.hour > 0 else cutoff_time

        all_instances = self.get_all_instances()

        for region, instances in all_instances.items():
            for instance in instances:
                launch_time = instance['LaunchTime']
                if hasattr(launch_time, 'replace'):
                    launch_time = launch_time.replace(tzinfo=None)

                if launch_time > one_hour_ago:
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
        """Check for EC2 security anomalies"""
        anomalies = []
        result = {
            'is_anomaly': False,
            'unauthorized_region_instances': [],
            'exposed_instances': [],
            'new_instances': [],
            'timestamp': datetime.utcnow().isoformat()
        }

        # Check for unauthorized regions
        if self.authorized_regions:
            unauthorized = self.get_unauthorized_regions_instances()
            if unauthorized:
                result['unauthorized_region_instances'] = unauthorized
                anomalies.append(f"Instances running in unauthorized regions: {list(unauthorized.keys())}")

        # Check for security group exposure
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

        # Check for new instances
        new_instances = self.get_new_instances()
        if new_instances:
            result['new_instances'] = new_instances
            anomalies.append(f"Detected {len(new_instances)} new instances")

        result['is_anomaly'] = len(anomalies) > 0
        result['anomalies'] = anomalies

        return result['is_anomaly'], result

    def stop_instance(self, instance_id: str, region: str) -> bool:
        """Stop a running EC2 instance"""
        try:
            regional_ec2 = boto3.client('ec2', region_name=region)
            regional_ec2.stop_instances(InstanceIds=[instance_id])
            return True
        except Exception as e:
            print(f"Error stopping instance {instance_id}: {e}")
            return False

    def set_authorized_regions(self, regions: List[str]) -> None:
        """Set authorized regions in Parameter Store"""
        try:
            self.ssm_client.put_parameter(
                Name='/aws-guardian/authorized-regions',
                Value=','.join(regions),
                Type='String',
                Overwrite=True
            )
            self.authorized_regions = regions
        except Exception as e:
            print(f"Error setting authorized regions: {e}")

    def get_authorized_regions(self) -> List[str]:
        """Get authorized regions from Parameter Store"""
        try:
            response = self.ssm_client.get_parameter(
                Name='/aws-guardian/authorized-regions'
            )
            self.authorized_regions = response['Parameter']['Value'].split(',')
            return self.authorized_regions
        except:
            return self.authorized_regions
