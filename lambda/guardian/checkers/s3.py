"""S3 bucket security checker for AWS Guardian"""
import boto3
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta, timezone
import json

# Import config
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import Config

class S3Checker:
    def __init__(self):
        """Initialize S3 checker"""
        boto3_kwargs = Config.get_boto3_kwargs()
        self.s3_client = boto3.client('s3', **boto3_kwargs)
        self.is_localstack = Config.is_localstack()

    def is_bucket_public_acl(self, bucket_name: str) -> bool:
        """Check if bucket has public ACL permissions"""
        try:
            acl = self.s3_client.get_bucket_acl(Bucket=bucket_name)

            for grant in acl.get('Grants', []):
                grantee = grant.get('Grantee', {})
                # Check for public access
                if grantee.get('Type') == 'Group':
                    uri = grantee.get('URI', '')
                    if 'AuthenticatedUsers' in uri or 'AllUsers' in uri:
                        return True

            return False
        except Exception as e:
            print(f"Error checking ACL for {bucket_name}: {e}")
            return False

    def is_bucket_public_policy(self, bucket_name: str) -> Tuple[bool, Dict]:
        """Check if bucket policy allows public access"""
        try:
            policy_response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
            policy_str = policy_response['Policy']

            if isinstance(policy_str, str):
                policy = json.loads(policy_str)
            else:
                policy = policy_str

            for statement in policy.get('Statement', []):
                principal = statement.get('Principal')

                # Check for wildcard principals
                if principal == '*' or (isinstance(principal, dict) and principal.get('AWS') == '*'):
                    effect = statement.get('Effect', '').upper()
                    if effect == 'ALLOW':
                        return True, statement

            return False, {}
        except Exception as e:
            # Handle both real AWS and LocalStack exceptions
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', str(type(e).__name__))

            # NoSuchBucketPolicy is expected - bucket just doesn't have a policy
            if 'NoSuchBucketPolicy' in str(error_code) or 'NoSuchBucketPolicy' in str(e):
                return False, {}

            # Log other errors
            print(f"Error checking policy for {bucket_name}: {error_code} - {e}")
            return False, {}

    def is_bucket_public_block_disabled(self, bucket_name: str) -> bool:
        """Check if bucket has public access block settings disabled"""
        try:
            response = self.s3_client.get_public_access_block(Bucket=bucket_name)
            config = response['PublicAccessBlockConfiguration']

            # If any setting is False, public access is not fully blocked
            return not (
                config.get('BlockPublicAcls', False) and
                config.get('BlockPublicPolicy', False) and
                config.get('IgnorePublicAcls', False) and
                config.get('RestrictPublicBuckets', False)
            )
        except self.s3_client.exceptions.NoSuchPublicAccessBlockConfiguration:
            # If no public access block is set, it's not protected
            return True
        except Exception as e:
            print(f"Error checking public access block for {bucket_name}: {e}")
            return False

    def get_public_buckets(self) -> List[Dict]:
        """Identify all public buckets"""
        public_buckets = []

        try:
            # List all buckets
            buckets_response = self.s3_client.list_buckets()

            for bucket in buckets_response.get('Buckets', []):
                bucket_name = bucket['Name']
                is_public = False
                public_reasons = []

                # Check ACL
                if self.is_bucket_public_acl(bucket_name):
                    is_public = True
                    public_reasons.append('Public ACL')

                # Check policy
                has_public_policy, policy = self.is_bucket_public_policy(bucket_name)
                if has_public_policy:
                    is_public = True
                    public_reasons.append('Public Bucket Policy')

                # Check public access block
                if self.is_bucket_public_block_disabled(bucket_name):
                    is_public = True
                    public_reasons.append('Public Access Block Disabled')

                if is_public:
                    public_buckets.append({
                        'bucket_name': bucket_name,
                        'creation_date': bucket['CreationDate'].isoformat(),
                        'public_reasons': public_reasons
                    })

            return public_buckets
        except Exception as e:
            print(f"Error listing public buckets: {e}")
            return []

    def get_new_buckets(self, hours: int = 24) -> List[Dict]:
        """Detect new S3 buckets created in the last N hours"""
        new_buckets = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        try:
            buckets_response = self.s3_client.list_buckets()

            for bucket in buckets_response.get('Buckets', []):
                creation_date = bucket['CreationDate']
                if hasattr(creation_date, 'replace'):
                    creation_date = creation_date.replace(tzinfo=None)

                if creation_date > cutoff_time:
                    new_buckets.append({
                        'bucket_name': bucket['Name'],
                        'creation_date': creation_date.isoformat()
                    })

            return new_buckets
        except Exception as e:
            print(f"Error detecting new buckets: {e}")
            return []

    def check_s3_anomalies(self) -> Tuple[bool, Dict[str, Any]]:
        """Check for S3 security anomalies"""
        anomalies = []
        result = {
            'is_anomaly': False,
            'public_buckets': [],
            'new_buckets': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Check for public buckets
        public_buckets = self.get_public_buckets()
        if public_buckets:
            result['public_buckets'] = public_buckets
            for bucket in public_buckets:
                anomalies.append(f"Public bucket detected: {bucket['bucket_name']} ({', '.join(bucket['public_reasons'])})")

        # Check for new buckets
        new_buckets = self.get_new_buckets()
        if new_buckets:
            result['new_buckets'] = new_buckets
            anomalies.append(f"Detected {len(new_buckets)} new buckets in last 24 hours")

        result['is_anomaly'] = len(anomalies) > 0
        result['anomalies'] = anomalies

        return result['is_anomaly'], result

    def block_public_access(self, bucket_name: str) -> bool:
        """Block public access to a bucket"""
        try:
            self.s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            return True
        except Exception as e:
            print(f"Error blocking public access for {bucket_name}: {e}")
            return False
