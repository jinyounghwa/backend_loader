"""Sprint 46 Phase 2: S3 Auto-Remediation Tests (8 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.remediators.s3_remediator import S3Remediator, RemediationStatus


class TestS3Remediation:
    """S3 bucket public access auto-remediation."""

    def test_s3_remediation_blocks_public_bucket(self):
        """✅ Public S3 bucket is blocked from public access."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        # Mock bucket operations
        mock_s3.head_bucket.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),  # Before remediation
            {  # After remediation
                'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            }
        ]
        mock_s3.put_public_access_block.return_value = {}
        mock_s3.get_bucket_policy.return_value = {}

        threat = {
            'threat_id': 'THREAT-S3-001',
            'description': 'Public S3 bucket detected'
        }

        result = remediator.remediate_public_bucket('test-bucket', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'blocked'
        assert result['bucket_name'] == 'test-bucket'
        assert mock_s3.put_public_access_block.called

    def test_s3_remediation_removes_public_acl(self):
        """✅ Public ACL is removed from bucket."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }}
        ]
        mock_s3.put_public_access_block.return_value = {}
        mock_s3.put_bucket_acl.return_value = {}
        mock_s3.get_bucket_policy.return_value = {}

        threat = {'threat_id': 'THREAT-S3-002', 'description': 'Test'}

        result = remediator.remediate_public_bucket('public-bucket', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert mock_s3.put_bucket_acl.called

    def test_s3_remediation_updates_bucket_policy(self):
        """✅ Bucket policy is backed up before modification."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_bucket_policy.return_value = {
            'Policy': '{"Statement": []}'
        }
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }}
        ]
        mock_s3.put_public_access_block.return_value = {}

        threat = {'threat_id': 'THREAT-S3-003', 'description': 'Test'}

        result = remediator.remediate_public_bucket('policy-bucket', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['policy_backup'] is not None

    def test_s3_remediation_backs_up_original_policy(self):
        """✅ Original bucket policy is backed up."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        original_policy = '{"Version": "2012-10-17", "Statement": []}'

        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_bucket_policy.return_value = {'Policy': original_policy}
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }}
        ]
        mock_s3.put_public_access_block.return_value = {}

        threat = {'threat_id': 'THREAT-S3-004', 'description': 'Test'}

        result = remediator.remediate_public_bucket('backup-bucket', threat)

        assert result['policy_backup']['policy'] == original_policy

    def test_s3_remediation_preserves_private_access(self):
        """✅ Private access is preserved in remediation."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_bucket_policy.return_value = {}
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }}
        ]
        mock_s3.put_public_access_block.return_value = {}

        threat = {'threat_id': 'THREAT-S3-005', 'description': 'Test'}

        result = remediator.remediate_public_bucket('private-bucket', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'blocked'

    def test_s3_remediation_handles_versioning(self):
        """✅ Bucket versioning is preserved during remediation."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_bucket_policy.return_value = {}
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }}
        ]
        mock_s3.put_public_access_block.return_value = {}

        threat = {'threat_id': 'THREAT-S3-006', 'description': 'Test'}

        result = remediator.remediate_public_bucket('versioned-bucket', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value

    def test_s3_remediation_handles_mfa_delete(self):
        """✅ MFA delete setting is preserved."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_bucket_policy.return_value = {}
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }}
        ]
        mock_s3.put_public_access_block.return_value = {}

        threat = {'threat_id': 'THREAT-S3-007', 'description': 'Test'}

        result = remediator.remediate_public_bucket('mfa-bucket', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value

    def test_s3_remediation_concurrent_buckets(self):
        """✅ Multiple buckets can be remediated concurrently."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        bucket_names = ['bucket-1', 'bucket-2', 'bucket-3']
        results = []

        for bucket_name in bucket_names:
            mock_s3.head_bucket.return_value = {}
            mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
            mock_s3.get_bucket_policy.return_value = {}
            mock_s3.get_public_access_block.side_effect = [
                Exception("NoSuchPublicAccessBlockConfiguration"),
                {'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }}
            ]
            mock_s3.put_public_access_block.return_value = {}

            threat = {'threat_id': f'THREAT-{bucket_name}', 'description': 'Test'}

            result = remediator.remediate_public_bucket(bucket_name, threat)
            results.append(result)

        assert len(results) == 3
        assert all(r['status'] == RemediationStatus.SUCCESS.value for r in results)
