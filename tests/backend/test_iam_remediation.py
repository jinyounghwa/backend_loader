"""Sprint 46 Phase 3: IAM Auto-Remediation Tests (6 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime
from guardian.remediators.iam_remediator import IAMRemediator, RemediationStatus


class TestIAMRemediation:
    """IAM permission auto-remediation functionality."""

    def test_iam_remediation_revokes_admin_access(self):
        """✅ AdministratorAccess policy is revoked from user."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        principal = 'arn:aws:iam::123456789012:user/compromised-user'
        threat = {
            'threat_id': 'THREAT-IAM-001',
            'description': 'User with AdministratorAccess detected'
        }

        # Setup mocks
        mock_iam.get_user.return_value = {'User': {'UserName': 'compromised-user'}}
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyName': 'AdministratorAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/AdministratorAccess'}
            ]
        }
        mock_iam.detach_user_policy.return_value = {}
        mock_iam.list_access_keys.return_value = {'AccessKeyMetadata': []}
        mock_iam.create_access_key.return_value = {
            'AccessKey': {'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE'}
        }

        result = remediator.remediate_excessive_permissions('compromised-user', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert result['action_taken'] == 'revoked'
        assert len(result['policies_revoked']) == 1
        assert 'AdministratorAccess' in result['policies_revoked'][0]
        assert mock_iam.detach_user_policy.called

    def test_iam_remediation_revokes_multiple_policies(self):
        """✅ Multiple dangerous policies are revoked."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        threat = {'threat_id': 'THREAT-IAM-002', 'description': 'Test'}

        mock_iam.get_user.side_effect = Exception("NoSuchEntity")
        mock_iam.get_role.return_value = {'Role': {'RoleName': 'super-role'}}
        mock_iam.list_attached_role_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyName': 'AdministratorAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/AdministratorAccess'},
                {'PolicyName': 'EC2FullAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/AmazonEC2FullAccess'},
                {'PolicyName': 'S3FullAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/AmazonS3FullAccess'}
            ]
        }
        mock_iam.detach_role_policy.return_value = {}

        result = remediator.remediate_excessive_permissions('super-role', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert len(result['policies_revoked']) == 3
        assert mock_iam.detach_role_policy.call_count == 3

    def test_iam_remediation_rotates_user_keys(self):
        """✅ Access keys are rotated for compromised user."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        threat = {'threat_id': 'THREAT-IAM-003', 'description': 'Test'}

        mock_iam.get_user.return_value = {'User': {'UserName': 'user-with-keys'}}
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyName': 'PowerUserAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/PowerUserAccess'}
            ]
        }
        mock_iam.detach_user_policy.return_value = {}
        mock_iam.list_access_keys.return_value = {
            'AccessKeyMetadata': [
                {'AccessKeyId': 'AKIA1111111111111111'}
            ]
        }
        mock_iam.create_access_key.return_value = {
            'AccessKey': {'AccessKeyId': 'AKIA2222222222222222'}
        }
        mock_iam.update_access_key.return_value = {}
        mock_iam.get_role.side_effect = Exception("NoSuchEntity")

        result = remediator.remediate_excessive_permissions('user-with-keys', threat)

        assert result['key_rotation']['new_key_created'] is True
        assert result['key_rotation']['new_key_id'] == 'AKIA2222222222222222'
        assert 'AKIA1111111111111111' in result['key_rotation']['old_keys']

    def test_iam_remediation_creates_session_token(self):
        """✅ Temporary STS session token is created."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        mock_iam.create_session_token.return_value = {
            'Credentials': {
                'AccessKeyId': 'ASIA1234567890ABCDEF',
                'SecretAccessKey': 'secret',
                'SessionToken': 'token',
                'Expiration': '2026-05-25T12:00:00Z'
            }
        }

        result = remediator.create_session_token('test-principal', duration=3600)

        assert result['success'] is True
        assert result['token']['AccessKeyId'] == 'ASIA1234567890ABCDEF'
        assert result['duration_seconds'] == 3600

    def test_iam_remediation_logs_action(self):
        """✅ Remediation action is logged."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        threat = {'threat_id': 'THREAT-IAM-005', 'description': 'Test'}

        mock_iam.get_user.return_value = {'User': {'UserName': 'logged-user'}}
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyName': 'PowerUserAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/PowerUserAccess'}
            ]
        }
        mock_iam.detach_user_policy.return_value = {}
        mock_iam.list_access_keys.return_value = {'AccessKeyMetadata': []}
        mock_iam.create_access_key.return_value = {
            'AccessKey': {'AccessKeyId': 'AKIA3333333333333333'}
        }

        result = remediator.remediate_excessive_permissions('logged-user', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert mock_audit.log_remediation.called
        call_args = mock_audit.log_remediation.call_args
        assert call_args[0][0] == 'logged-user'

    def test_iam_remediation_handles_role_vs_user(self):
        """✅ Remediation handles both IAM roles and users."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        # Test with role
        mock_iam.get_user.side_effect = Exception("NoSuchEntity")
        mock_iam.get_role.return_value = {'Role': {'RoleName': 'service-role'}}
        mock_iam.list_attached_role_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyName': 'IAMFullAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/IAMFullAccess'}
            ]
        }
        mock_iam.detach_role_policy.return_value = {}

        threat = {'threat_id': 'THREAT-IAM-006', 'description': 'Test'}

        result = remediator.remediate_excessive_permissions('service-role', threat)

        assert result['status'] == RemediationStatus.SUCCESS.value
        assert 'IAMFullAccess' in result['policies_revoked'][0]
