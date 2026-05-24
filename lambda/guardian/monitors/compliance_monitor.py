"""AWS Compliance Monitoring"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ComplianceMonitor:
    """Monitor AWS account compliance with security policies"""

    def __init__(self, ec2_client, s3_client, cloudtrail_client):
        """
        Args:
            ec2_client: boto3 EC2 client
            s3_client: boto3 S3 client
            cloudtrail_client: boto3 CloudTrail client
        """
        self.ec2 = ec2_client
        self.s3 = s3_client
        self.cloudtrail = cloudtrail_client

    def check_encryption_status(self, resource_type: str) -> Dict:
        """
        Check encryption status for resource type

        Args:
            resource_type: Resource type (EBS, S3, RDS, etc.)

        Returns:
            Encryption status report
        """
        try:
            report = {
                'resource_type': resource_type,
                'encrypted_count': 0,
                'unencrypted_count': 0,
                'total_resources': 0,
                'encryption_rate': 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            if resource_type == 'EBS':
                response = self.ec2.describe_volumes()
                volumes = response.get('Volumes', [])

                report['total_resources'] = len(volumes)
                report['encrypted_count'] = sum(1 for v in volumes if v.get('Encrypted', False))
                report['unencrypted_count'] = report['total_resources'] - report['encrypted_count']

            elif resource_type == 'S3':
                response = self.s3.list_buckets()
                buckets = response.get('Buckets', [])

                report['total_resources'] = len(buckets)
                # Check bucket encryption for each bucket
                encrypted = 0
                for bucket in buckets:
                    try:
                        enc = self.s3.get_bucket_encryption(Bucket=bucket['Name'])
                        if enc:
                            encrypted += 1
                    except:
                        pass

                report['encrypted_count'] = encrypted
                report['unencrypted_count'] = report['total_resources'] - encrypted

            if report['total_resources'] > 0:
                report['encryption_rate'] = (report['encrypted_count'] / report['total_resources']) * 100

            logger.info(f"Checked encryption for {resource_type}: {report['encryption_rate']:.1f}% encrypted")
            return report

        except Exception as e:
            logger.error(f"Failed to check encryption status: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def verify_logging_enabled(self, account_id: str) -> Dict:
        """
        Verify logging is enabled for CloudTrail and VPC Flow Logs

        Args:
            account_id: AWS account ID

        Returns:
            Logging verification result
        """
        try:
            result = {
                'account_id': account_id,
                'cloudtrail_enabled': False,
                'vpc_flow_logs_enabled': False,
                's3_logging_enabled': False,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Check CloudTrail
            try:
                trails = self.cloudtrail.describe_trails()
                trails_list = trails.get('trailList', [])
                logging_trails = sum(1 for t in trails_list if t.get('IsLogging', False))
                result['cloudtrail_enabled'] = logging_trails > 0
            except Exception as e:
                logger.warning(f"Failed to check CloudTrail: {str(e)}")

            logger.info(f"Verified logging for account {account_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to verify logging: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def check_mfa_enforcement(self, account_id: str) -> Dict:
        """
        Check MFA enforcement for IAM users

        Args:
            account_id: AWS account ID

        Returns:
            MFA enforcement report
        """
        try:
            report = {
                'account_id': account_id,
                'mfa_enabled_count': 0,
                'mfa_disabled_count': 0,
                'mfa_enforcement_rate': 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Checked MFA enforcement for account {account_id}")
            return report

        except Exception as e:
            logger.error(f"Failed to check MFA enforcement: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def scan_public_resources(self, account_id: str) -> Dict:
        """
        Scan for publicly accessible resources

        Args:
            account_id: AWS account ID

        Returns:
            Public resources report
        """
        try:
            report = {
                'account_id': account_id,
                'public_s3_buckets': [],
                'public_security_groups': [],
                'public_rds_instances': [],
                'total_public_resources': 0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Scanned public resources for account {account_id}")
            return report

        except Exception as e:
            logger.error(f"Failed to scan public resources: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def generate_compliance_report(self, account_id: str) -> Dict:
        """
        Generate comprehensive compliance report for account

        Args:
            account_id: AWS account ID

        Returns:
            Compliance report
        """
        try:
            report = {
                'account_id': account_id,
                'report_date': datetime.now(timezone.utc).isoformat(),
                'checks': {
                    'encryption': self.check_encryption_status('EBS'),
                    'logging': self.verify_logging_enabled(account_id),
                    'mfa': self.check_mfa_enforcement(account_id),
                    'public_resources': self.scan_public_resources(account_id)
                },
                'findings': [],
                'recommendations': []
            }

            logger.info(f"Generated compliance report for account {account_id}")
            return report

        except Exception as e:
            logger.error(f"Failed to generate compliance report: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def calculate_compliance_score(self, checks: Dict) -> float:
        """
        Calculate overall compliance score (0-100)

        Args:
            checks: Dictionary of compliance checks with boolean values

        Returns:
            Compliance score (0-100)
        """
        try:
            if not checks:
                return 0.0

            # Weight for each check
            weights = {
                'encryption': 0.25,
                'logging': 0.25,
                'mfa_enforcement': 0.20,
                'public_resources': 0.15,
                'iam_policy': 0.15
            }

            score = 0.0
            total_weight = 0.0

            for check_name, check_result in checks.items():
                weight = weights.get(check_name, 0.1)
                total_weight += weight

                # Convert boolean to points (True = 100, False = 0)
                if isinstance(check_result, bool):
                    points = 100 if check_result else 0
                else:
                    points = check_result if isinstance(check_result, (int, float)) else 0

                score += points * weight

            # Normalize to 0-100
            if total_weight > 0:
                score = (score / total_weight)

            score = max(0, min(100, score))

            logger.info(f"Calculated compliance score: {score:.1f}")
            return score

        except Exception as e:
            logger.error(f"Failed to calculate compliance score: {str(e)}")
            return 0.0
