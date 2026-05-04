"""EC2 security checker for AWS Guardian"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)


class EC2Checker(BaseChecker):
    """Detect EC2 security anomalies: unauthorized regions, exposed security groups, new instances."""

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        authorized_regions: Optional[List[str]] = None,
    ):
        effective_config = config or {}
        if authorized_regions:
            effective_config.setdefault('authorized_regions', authorized_regions)
        super().__init__(clients or {}, effective_config, account_id, credentials)

        self.authorized_regions = self.config.get('authorized_regions', [])
        self.is_localstack = Config.is_localstack()

    def check(self) -> CheckResult:
        """Run all EC2 security checks and return unified CheckResult."""
        self._log_check_start('EC2')

        try:
            anomalies: List[str] = []
            details: Dict[str, Any] = {
                'is_anomaly': False,
                'unauthorized_region_instances': {},
                'exposed_instances': [],
                'new_instances': [],
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

            if self.authorized_regions:
                unauthorized = self._get_unauthorized_regions_instances()
                if unauthorized:
                    details['unauthorized_region_instances'] = unauthorized
                    anomalies.append(f"Instances in unauthorized regions: {list(unauthorized.keys())}")

            all_instances = self._get_all_instances()
            for region, instances in all_instances.items():
                for instance in instances:
                    exposed_rules = self._check_security_group_exposure(instance)
                    if exposed_rules:
                        details['exposed_instances'].append({
                            'instance_id': instance['InstanceId'],
                            'region': region,
                            'exposed_rules': exposed_rules,
                        })
                        anomalies.append(f"Instance {instance['InstanceId']} has 0.0.0.0/0 exposure")

            new_instances = self._get_new_instances()
            if new_instances:
                details['new_instances'] = new_instances
                anomalies.append(f"Detected {len(new_instances)} new instances")

            details['is_anomaly'] = len(anomalies) > 0
            details['anomalies'] = anomalies

            if not anomalies:
                self._log_check_end('EC2', 'INFO')
                return CheckResult.info('EC2 Check', 'All instances secure')

            severity = 'CRITICAL' if details['exposed_instances'] else 'HIGH'
            self._log_check_end('EC2', severity)
            return CheckResult(
                severity=severity,
                title='EC2 Security Issues Detected',
                message=f"Found {len(anomalies)} EC2 issues",
                details=details,
                suggested_action='Review and stop unauthorized/exposed instances',
            )

        except Exception as e:
            self._log_error('EC2', e)
            return CheckResult.error('EC2 Check Failed', f'Failed to check EC2: {str(e)}')

    def _get_all_instances(self) -> Dict[str, List[Dict]]:
        instances_by_region: Dict[str, List[Dict]] = {}

        try:
            if self.is_localstack:
                regions = ['us-east-1']
            else:
                regions_response = AWSClientProvider.get_client('ec2').describe_regions()
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

    def _get_unauthorized_regions_instances(self) -> Dict[str, List[Dict]]:
        if not self.authorized_regions:
            return {}
        all_instances = self._get_all_instances()
        return {
            region: instances
            for region, instances in all_instances.items()
            if region not in self.authorized_regions
        }

    def _check_security_group_exposure(self, instance: Dict) -> List[Dict]:
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
                                    'cidr': '0.0.0.0/0',
                                })
            except Exception as e:
                logger.error("Error checking security group %s: %s", sg_id, e)
        return exposed_rules

    def _get_new_instances(self) -> List[Dict]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        all_instances = self._get_all_instances()
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
                        'owner': instance.get('OwnerAlias', 'Unknown'),
                    })
        return new_instances

    def check_ec2_anomalies(self):
        """Backward-compatible entry point returning (is_anomaly, data) tuple."""
        result = self.check()
        return (result.severity != 'INFO', result.details)
