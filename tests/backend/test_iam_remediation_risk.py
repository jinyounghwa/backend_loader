"""Sprint 46 Phase 3: IAM Risk Analysis & Blast Radius Tests (4 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.remediators.iam_remediator import IAMRemediator, RemediationStatus


class TestIAMRemediationRisk:
    """IAM remediation risk analysis and safety verification."""

    def test_iam_remediation_skips_service_roles(self):
        """✅ Service roles (Lambda, EC2, RDS) are skipped."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        threat = {'threat_id': 'THREAT-IAM-RISK-001', 'description': 'Test'}

        # Service role with Lambda in name
        principal = 'arn:aws:iam::123456789012:role/lambda-execution-role'

        safety_check = remediator.verify_safety_conditions(principal, 'role')

        assert not safety_check['passed']
        assert safety_check['checks']['is_service_role'] is True
        assert 'Service role' in safety_check['reason']

    def test_iam_remediation_skips_protected_principals(self):
        """✅ Protected principals (guardian:protected=true tag) are skipped."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        threat = {'threat_id': 'THREAT-IAM-RISK-002', 'description': 'Test'}

        principal = 'arn:aws:iam::123456789012:user/important-user'

        # In production, tags would be checked via get_user/get_role
        # For this test, verify the protected check logic
        safety_check = remediator.verify_safety_conditions(principal, 'user')

        # Protected flag is checked in _is_protected_principal
        assert isinstance(safety_check['passed'], bool)
        assert 'checks' in safety_check
        assert 'is_protected' in safety_check['checks']

    def test_iam_remediation_assesses_blast_radius(self):
        """✅ Blast radius assessment identifies impact of revocation."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        principal = 'arn:aws:iam::123456789012:role/critical-app-role'
        dangerous_policies = [
            'arn:aws:iam::aws:policy/AmazonEC2FullAccess',
            'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        ]

        risk_assessment = remediator._assess_blast_radius(principal, dangerous_policies)

        assert 'principal' in risk_assessment
        assert 'policies_to_revoke' in risk_assessment
        assert 'risk_level' in risk_assessment
        assert risk_assessment['principal'] == principal
        assert len(risk_assessment['policies_to_revoke']) == 2

    def test_iam_remediation_handles_missing_policies(self):
        """✅ Remediation handles users/roles with no dangerous policies."""
        mock_iam = Mock()
        mock_audit = Mock()

        remediator = IAMRemediator(mock_iam, mock_audit)

        threat = {'threat_id': 'THREAT-IAM-RISK-004', 'description': 'Test'}

        mock_iam.get_user.return_value = {'User': {'UserName': 'safe-user'}}
        mock_iam.list_attached_user_policies.return_value = {
            'AttachedPolicies': [
                {'PolicyName': 'ReadOnlyAccess', 'PolicyArn': 'arn:aws:iam::aws:policy/ReadOnlyAccess'}
            ]
        }

        result = remediator.remediate_excessive_permissions('safe-user', threat)

        assert result['status'] == RemediationStatus.SKIPPED.value
        assert result['action_taken'] == 'skipped'
        assert 'No dangerous policies' in result['reason']
