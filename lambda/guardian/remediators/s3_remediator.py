"""S3 Bucket Auto-Remediation - Block public access on insecure buckets."""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import json


class RemediationStatus(Enum):
    """Remediation outcome statuses."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class S3Remediator:
    """Automatic remediation for public S3 buckets."""

    def __init__(self, s3_client, audit_logger):
        """Initialize S3 remediation with AWS client and audit logger."""
        self.s3 = s3_client
        self.audit = audit_logger
        self.remediation_history = {}

    def remediate_public_bucket(self, bucket_name: str, threat: Dict) -> Dict:
        """
        Block public access on insecure bucket.

        Remediation steps:
        1. Backup current ACL and policy
        2. Enable BlockPublicAccess
        3. Remove public ACL settings
        4. Verify bucket is private
        5. Log all changes

        Args:
            bucket_name: S3 bucket name
            threat: Threat detection details

        Returns:
            {
                'status': 'success|skipped|failed',
                'bucket_name': bucket_name,
                'action_taken': 'blocked|skipped',
                'reason': explanation,
                'policy_backup': original_policy,
                'timestamp': iso_timestamp
            }
        """
        result = {
            'bucket_name': bucket_name,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'threat': threat.get('threat_id', 'unknown')
        }

        # 1. Verify bucket exists and is accessible
        try:
            bucket_info = self._get_bucket_info(bucket_name)
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Cannot access bucket: {str(e)}"
            self.audit.log_remediation(bucket_name, 'access_failed', result)
            return result

        # 2. Check safety conditions
        safety_check = self.verify_safety_conditions(bucket_name, bucket_info)
        if not safety_check['passed']:
            result['status'] = RemediationStatus.SKIPPED.value
            result['reason'] = safety_check['reason']
            result['action_taken'] = 'skipped'
            self.audit.log_remediation(bucket_name, 'remediation_skipped', result)
            return result

        # 3. Backup current policy and ACL
        try:
            policy_backup = self.backup_bucket_policy(bucket_name)
            result['policy_backup'] = policy_backup
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Policy backup failed: {str(e)}"
            self.audit.log_remediation(bucket_name, 'backup_failed', result)
            return result

        # 4. Enable BlockPublicAccess
        try:
            blocked = self.enable_block_public_access(bucket_name)
            if not blocked:
                result['status'] = RemediationStatus.FAILED.value
                result['reason'] = "Failed to enable BlockPublicAccess"
                self.audit.log_remediation(bucket_name, 'block_failed', result)
                return result
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Block operation failed: {str(e)}"
            self.audit.log_remediation(bucket_name, 'block_failed', result)
            return result

        # 5. Remove public ACL if present
        try:
            acl_removed = self.remove_public_acl(bucket_name)
            result['acl_removed'] = acl_removed
        except Exception as e:
            # ACL removal failure doesn't prevent overall success
            result['acl_error'] = str(e)

        # 6. Verify bucket is now private
        try:
            verify = self._verify_bucket_private(bucket_name)
            if not verify:
                result['status'] = RemediationStatus.FAILED.value
                result['reason'] = "Bucket verification failed - still public"
                self.audit.log_remediation(bucket_name, 'verify_failed', result)
                return result
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Verification failed: {str(e)}"
            self.audit.log_remediation(bucket_name, 'verify_failed', result)
            return result

        result['status'] = RemediationStatus.SUCCESS.value
        result['action_taken'] = 'blocked'
        result['reason'] = f"Bucket blocked due to: {threat.get('description', 'public access detected')}"
        self.audit.log_remediation(bucket_name, 'remediation_success', result)
        return result

    def enable_block_public_access(self, bucket_name: str) -> bool:
        """Enable BlockPublicAccess on the bucket."""
        try:
            self.s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            return True
        except Exception:
            return False

    def backup_bucket_policy(self, bucket_name: str) -> Dict:
        """Backup bucket policy before making changes."""
        try:
            policy = self.s3.get_bucket_policy(Bucket=bucket_name)
            policy_doc = policy.get('Policy', '{}')
            return {
                'policy': policy_doc,
                'backup_time': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'bucket_name': bucket_name
            }
        except Exception:
            # No policy attached is not an error
            return {
                'policy': None,
                'backup_time': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'bucket_name': bucket_name
            }

    def remove_public_acl(self, bucket_name: str) -> bool:
        """Remove public ACL settings from bucket."""
        try:
            # Set bucket ACL to private
            self.s3.put_bucket_acl(
                Bucket=bucket_name,
                ACL='private'
            )
            return True
        except Exception:
            # Some buckets may not allow direct ACL changes
            return False

    def verify_safety_conditions(self, bucket_name: str, bucket_info: Dict = None) -> Dict:
        """
        Verify all safety conditions before remediation.

        Returns:
            {
                'passed': bool,
                'reason': explanation if not passed,
                'checks': {
                    'is_protected_bucket': bool,
                    'is_remediation_disabled': bool,
                    'is_already_private': bool
                }
            }
        """
        if bucket_info is None:
            bucket_info = self._get_bucket_info(bucket_name)

        checks = {}
        reasons = []

        # Check 1: Protected bucket
        is_protected = self._is_protected_bucket(bucket_name)
        checks['is_protected_bucket'] = is_protected
        if is_protected:
            reasons.append("Bucket is marked as protected (guardian:protected=true tag)")

        # Check 2: Remediation disabled
        is_disabled = self._is_remediation_disabled(bucket_name)
        checks['is_remediation_disabled'] = is_disabled
        if is_disabled:
            reasons.append("Remediation disabled (guardian:no-auto-remediation=true tag)")

        # Check 3: Already private
        is_private = self._is_bucket_private(bucket_name)
        checks['is_already_private'] = is_private
        if is_private:
            reasons.append("Bucket is already private")

        passed = not any([is_protected, is_disabled, is_private])
        reason = "; ".join(reasons) if reasons else "All safety checks passed"

        return {
            'passed': passed,
            'reason': reason,
            'checks': checks
        }

    def rollback_remediation(self, bucket_name: str) -> Dict:
        """Attempt to restore bucket to pre-remediation state."""
        result = {
            'bucket_name': bucket_name,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        # Check if we have a backup
        if bucket_name not in self.remediation_history:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = "No remediation history found"
            return result

        history = self.remediation_history[bucket_name]
        policy_backup = history.get('policy_backup')

        if not policy_backup or not policy_backup.get('policy'):
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = "No policy backup available for rollback"
            return result

        # Try to restore the original policy
        try:
            if policy_backup.get('policy'):
                self.s3.put_bucket_policy(
                    Bucket=bucket_name,
                    Policy=policy_backup['policy']
                )
            result['status'] = RemediationStatus.SUCCESS.value
            result['action'] = 'restored'
            result['reason'] = "Bucket policy restored from backup"
            self.audit.log_remediation(bucket_name, 'rollback_success', result)
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Rollback failed: {str(e)}"
            self.audit.log_remediation(bucket_name, 'rollback_failed', result)

        return result

    # Private helper methods
    def _get_bucket_info(self, bucket_name: str) -> Dict:
        """Fetch bucket information."""
        response = self.s3.head_bucket(Bucket=bucket_name)
        return response if response else {}

    def _is_protected_bucket(self, bucket_name: str) -> bool:
        """Check if bucket is marked as protected."""
        try:
            tags = self.s3.get_bucket_tagging(Bucket=bucket_name)
            tag_dict = {tag['Key']: tag['Value'] for tag in tags.get('TagSet', [])}
            return tag_dict.get('guardian:protected', '').lower() == 'true'
        except Exception:
            return False

    def _is_remediation_disabled(self, bucket_name: str) -> bool:
        """Check if auto-remediation is disabled."""
        try:
            tags = self.s3.get_bucket_tagging(Bucket=bucket_name)
            tag_dict = {tag['Key']: tag['Value'] for tag in tags.get('TagSet', [])}
            return tag_dict.get('guardian:no-auto-remediation', '').lower() == 'true'
        except Exception:
            return False

    def _is_bucket_private(self, bucket_name: str) -> bool:
        """Check if bucket is already private."""
        try:
            # Check BlockPublicAccess configuration
            response = self.s3.get_public_access_block(Bucket=bucket_name)
            config = response['PublicAccessBlockConfiguration']
            return all([
                config.get('BlockPublicAcls'),
                config.get('IgnorePublicAcls'),
                config.get('BlockPublicPolicy'),
                config.get('RestrictPublicBuckets')
            ])
        except Exception:
            return False

    def _verify_bucket_private(self, bucket_name: str) -> bool:
        """Verify that bucket is now private."""
        try:
            response = self.s3.get_public_access_block(Bucket=bucket_name)
            config = response['PublicAccessBlockConfiguration']
            return all([
                config.get('BlockPublicAcls'),
                config.get('IgnorePublicAcls'),
                config.get('BlockPublicPolicy'),
                config.get('RestrictPublicBuckets')
            ])
        except Exception:
            return False
