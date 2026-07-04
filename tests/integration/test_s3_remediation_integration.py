"""Sprint 46 Phase 2: S3 Remediation Integration Tests (3 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from guardian.remediators.s3_remediator import S3Remediator, RemediationStatus


class TestS3RemediationIntegration:
    """S3 remediation end-to-end integration scenarios."""

    def test_threat_detection_to_s3_block(self):
        """✅ Complete flow: threat detection → S3 block → verification."""
        threat = {
            'threat_id': 'THREAT-S3-INT-001',
            'event_type': 'PublicBucketDetected',
            'severity': 9,
            'bucket_name': 'insecure-bucket',
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'description': 'S3 bucket with public read access detected'
        }

        bucket_name = threat['bucket_name']

        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        # Setup mock responses
        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_bucket_policy.return_value = {
            'Policy': '{"Statement": [{"Effect": "Allow", "Principal": "*"}]}'
        }
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {
                'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            }
        ]
        mock_s3.put_public_access_block.return_value = {}

        # Execute remediation
        result = remediator.remediate_public_bucket(bucket_name, threat)

        # Assertions
        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'blocked'
        assert result['bucket_name'] == bucket_name
        assert result['threat'] == threat['threat_id']
        assert mock_s3.put_public_access_block.called
        assert mock_audit.log_remediation.called

    def test_s3_block_preserves_https(self):
        """✅ HTTPS enforcement is preserved during remediation."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        # Policy that enforces HTTPS
        https_policy = '''{
            "Statement": [{
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": ["arn:aws:s3:::https-bucket/*"],
                "Condition": {
                    "Bool": {"aws:SecureTransport": "false"}
                }
            }]
        }'''

        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_bucket_policy.return_value = {'Policy': https_policy}
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {
                'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            }
        ]
        mock_s3.put_public_access_block.return_value = {}

        threat = {
            'threat_id': 'THREAT-S3-INT-002',
            'description': 'Test'
        }

        result = remediator.remediate_public_bucket('https-bucket', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        # Policy backup includes HTTPS enforcement
        assert 'aws:SecureTransport' in result['policy_backup']['policy']

    def test_s3_block_with_cloudfront(self):
        """✅ CloudFront distribution configuration is preserved."""
        mock_s3 = Mock()
        mock_audit = Mock()

        remediator = S3Remediator(mock_s3, mock_audit)

        # Policy that allows only CloudFront
        cf_policy = '''{
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Service": "cloudfront.amazonaws.com"
                },
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::cdn-bucket/*",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceArn": "arn:aws:cloudfront::123456789012:distribution/E127EXAMPLE51Z"
                    }
                }
            }]
        }'''

        mock_s3.head_bucket.return_value = {}
        mock_s3.get_bucket_tagging.side_effect = Exception("NoSuchTagSet")
        mock_s3.get_bucket_policy.return_value = {'Policy': cf_policy}
        mock_s3.get_public_access_block.side_effect = [
            Exception("NoSuchPublicAccessBlockConfiguration"),
            {
                'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            }
        ]
        mock_s3.put_public_access_block.return_value = {}

        threat = {
            'threat_id': 'THREAT-S3-INT-003',
            'description': 'Test'
        }

        result = remediator.remediate_public_bucket('cdn-bucket', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        # CloudFront configuration is backed up
        assert 'cloudfront.amazonaws.com' in result['policy_backup']['policy']
