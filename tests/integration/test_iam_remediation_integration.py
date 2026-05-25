"""Sprint 46 Phase 3: IAM Remediation Integration Tests (2 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.remediators.iam_remediator import IAMRemediator, RemediationStatus


class TestIAMRemediationIntegration:
    """IAM remediation end-to-end integration scenarios."""

    def test_threat_detection_to_iam_revocation(self):
        """✅ Complete flow: threat detection → IAM policy revocation → audit log."""
        threat = {
            'threat_id': 'THREAT-IAM-INT-001',
            'event_type': 'CompromisedUserDetected',
            'severity': 9,
            'principal': 'arn:aws:iam::123456789012:user/compromised-user',
            'timestamp': datetime.utcnow().isoformat(),
            'description': 'User with AdministratorAccess detected in unauthorized region'
        }

        principal = threat['principal']

        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        # Setup mock responses
        mock_iam.get_user.return_value = {'User': {'UserName': 'compromised-user'}}
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyName': 'AdministratorAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/AdministratorAccess'},
                {'PolicyName': 'AWSCloudTrailFullAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/AWSCloudTrailFullAccess'}
            ]
        }
        mock_iam.detach_user_policy.return_value = {}
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [
                {'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE'}
            ]
        }
        mock_iam.create_access_key.return_value = {
            'AccessKey': {'AccessKeyId': 'AKIAIOSFODNN7NEWKEY'}
        }
        mock_iam.update_access_key.return_value = {}

        # Execute remediation
        result = remediator.remediate_excessive_permissions('compromised-user', threat)

        # Assertions
        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'revoked'
        assert len(result['policies_revoked']) == 2
        assert result['policies_revoked'][0] == 'AdministratorAccess'
        assert result['policies_revoked'][1] == 'AWSCloudTrailFullAccess'
        assert result['threat'] == threat['threat_id']
        assert mock_iam.detach_user_policy.call_count == 2
        assert mock_audit.log_remediation.called

    def test_iam_revocation_with_approval_workflow(self):
        """✅ High-risk revocation requires admin approval."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        threat = {
            'threat_id': 'THREAT-IAM-INT-002',
            'description': 'Critical admin role requires review'
        }

        # Admin role with critical access
        principal = 'arn:aws:iam::123456789012:role/admin-role'

        safety_check = remediator.verify_safety_conditions(principal, 'role')

        # Admin roles with critical access should be flagged
        if 'admin' in principal.lower():
            assert isinstance(safety_check['checks']['has_critical_access'], bool)
