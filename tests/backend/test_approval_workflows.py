"""Sprint 47 Phase 3: Approval Workflows & Decision Engine Tests (5 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone
import time
from guardian.storage.approval_workflow import ApprovalWorkflow, RiskLevel
from guardian.engines.decision_engine import RemediationDecisionEngine


class TestApprovalWorkflows:
    """Risk-based approval workflows with auto-approval for low-risk items."""

    def test_low_risk_remediation_auto_approved(self):
        """✅ Low-risk remediation is automatically approved without requiring approvals."""
        mock_audit = Mock()
        workflow = ApprovalWorkflow(mock_audit)

        threat = {
            'threat_id': 'THREAT-LOW-001',
            'severity': 3,  # Low severity
            'description': 'Minor S3 ACL change'
        }

        remediation_plan = {
            'steps': [
                {'type': 's3_block_public', 'bucket_id': 'bucket-123'}
            ]
        }

        # Create approval request
        approval = workflow.create_approval_request(threat, remediation_plan)

        assert approval['status'] == 'auto_approved'
        assert approval['risk_level'] == 'low'
        assert approval['approvers_needed'] == 0
        assert approval['token'] is not None
        assert approval['expires_at'] is None

        # Verify audit logging
        assert mock_audit.log_approval.called

    def test_critical_remediation_requires_multi_approval(self):
        """✅ Critical-severity remediation requires 3-person approval."""
        mock_audit = Mock()
        workflow = ApprovalWorkflow(mock_audit)

        threat = {
            'threat_id': 'THREAT-CRITICAL-001',
            'severity': 9,  # Critical
            'description': 'Unauthorized admin access'
        }

        remediation_plan = {
            'steps': [
                {'type': 'ec2_terminate', 'instance_id': 'i-critical'},
                {'type': 'iam_revoke', 'principal': 'suspicious-user'},
                {'type': 'network_isolate', 'vpc_id': 'vpc-123'},
                {'type': 's3_block_public', 'bucket_id': 'bucket-sensitive'}
            ]
        }

        # Create approval request
        approval = workflow.create_approval_request(threat, remediation_plan)

        assert approval['status'] == 'pending'
        assert approval['risk_level'] == 'critical'
        assert approval['approvers_needed'] == 3
        assert approval['expires_at'] is not None

        # Parse expiration time
        expires_at = datetime.fromisoformat(approval['expires_at'])
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        time_delta = (expires_at - now).total_seconds()

        # Should expire in ~5 minutes (300 seconds)
        assert 295 < time_delta < 305

    def test_approval_token_expiration(self):
        """✅ Approval tokens expire after configured timeout."""
        mock_audit = Mock()
        workflow = ApprovalWorkflow(mock_audit)

        threat = {
            'threat_id': 'THREAT-TOKEN-001',
            'severity': 7,  # High
            'description': 'Unauthorized EC2 instance'
        }

        remediation_plan = {
            'steps': [
                {'type': 'ec2_stop', 'instance_id': 'i-test'}
            ]
        }

        # Create approval request (HIGH risk)
        approval = workflow.create_approval_request(threat, remediation_plan)
        approval_id = approval['approval_id']

        # Add approvals to make it fully approved
        workflow.approve_request(approval_id, 'approver-1')
        approval_result = workflow.approve_request(approval_id, 'approver-2')

        # Should be approved
        assert approval_result['status'] == 'approved'
        token = approval_result['token']

        # Token should be valid now
        validation = workflow.validate_token(token)
        assert validation['valid'] is True

        # Manually expire the token for testing
        workflow.approval_tokens[token]['expires_at'] = (
            datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        ).isoformat()

        # Token should now be expired
        validation = workflow.validate_token(token)
        assert validation['valid'] is False
        assert 'expired' in validation['error'].lower()

    def test_approval_audit_trail(self):
        """✅ All approvals are logged with timestamps and approver IDs."""
        mock_audit = Mock()
        workflow = ApprovalWorkflow(mock_audit)

        threat = {
            'threat_id': 'THREAT-AUDIT-001',
            'severity': 6,  # Medium-High
            'description': 'Suspicious IAM activity'
        }

        remediation_plan = {
            'steps': [
                {'type': 'iam_revoke', 'principal': 'user-123'}
            ]
        }

        # Create approval request
        approval = workflow.create_approval_request(threat, remediation_plan)
        approval_id = approval['approval_id']

        # Add approvals
        workflow.approve_request(approval_id, 'alice', 'Approved - suspicious activity confirmed')
        workflow.approve_request(approval_id, 'bob', 'Approved - risk is acceptable')

        # Get audit trail
        history = workflow.get_approval_history(approval_id)

        assert history['status'] == 'approved'
        assert len(history['approvals']) == 2
        assert history['approvals'][0]['approver_id'] == 'alice'
        assert history['approvals'][0]['comments'] == 'Approved - suspicious activity confirmed'
        assert history['approvals'][1]['approver_id'] == 'bob'
        assert history['approvals'][1]['comments'] == 'Approved - risk is acceptable'
        assert history['approvals'][0]['timestamp']
        assert history['approvals'][1]['timestamp']

    def test_remediation_decision_scoring(self):
        """✅ Decision engine scores threat confidence and remediation risk correctly."""
        mock_audit = Mock()
        decision_engine = RemediationDecisionEngine(mock_audit)

        # Test case 1: High confidence threat with low risk remediation
        high_confidence_threat = {
            'threat_id': 'THREAT-SCORE-001',
            'severity': 9,
            'evidence': [
                {'source': 'guardduty', 'description': 'Malware detected'},
                {'source': 'securityhub', 'description': 'Critical finding'},
                {'source': 'macie', 'description': 'Data exfiltration detected'}
            ]
        }

        low_risk_remediation = {
            'steps': [
                {'type': 's3_block_public', 'bucket_id': 'bucket-123'}
            ]
        }

        confidence = decision_engine.analyze_threat_confidence(high_confidence_threat)
        assert confidence['confidence_level'] == 'high'
        assert confidence['confidence_score'] >= 0.8
        assert confidence['recommendation'] == 'remediate'

        risk = decision_engine.analyze_remediation_risk(high_confidence_threat, low_risk_remediation)
        assert risk['risk_score'] <= 0.1
        assert risk['benefit_score'] > 0.5
        assert risk['net_score'] > 0.5

        # Test case 2: Low confidence threat requires manual review
        low_confidence_threat = {
            'threat_id': 'THREAT-SCORE-002',
            'severity': 2,
            'evidence': []  # No evidence
        }

        high_risk_remediation = {
            'steps': [
                {'type': 'ec2_terminate', 'instance_id': 'i-prod'},
                {'type': 'ec2_terminate', 'instance_id': 'i-prod-2'}
            ]
        }

        confidence = decision_engine.analyze_threat_confidence(low_confidence_threat)
        assert confidence['confidence_level'] == 'low'
        assert confidence['confidence_score'] < 0.6
        assert confidence['recommendation'] == 'monitor'

        # Decision engine should recommend manual review for low confidence
        decision = decision_engine.decide_remediation_strategy(low_confidence_threat, high_risk_remediation)
        assert decision['decision'] == 'manual_review'
        assert decision['required_approvers'] >= 1

        # Test case 3: Medium confidence with balanced risk
        medium_threat = {
            'threat_id': 'THREAT-SCORE-003',
            'severity': 6,
            'evidence': [
                {'source': 'cloudtrail', 'description': 'Suspicious API call'},
                {'source': 'vpc_flow_logs', 'description': 'Unexpected traffic'}
            ]
        }

        medium_remediation = {
            'steps': [
                {'type': 'iam_revoke', 'principal': 'user-123'}
            ]
        }

        confidence = decision_engine.analyze_threat_confidence(medium_threat)
        assert confidence['confidence_level'] == 'medium'
        assert 0.6 <= confidence['confidence_score'] <= 0.8

        risk = decision_engine.analyze_remediation_risk(medium_threat, medium_remediation)
        assert risk['benefit_score'] > 0.4
        assert risk['risk_score'] < 0.2
        assert risk['net_score'] > 0.2
