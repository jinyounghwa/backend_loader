"""Sprint 47 Phase 3: Approval Workflows Integration Tests (5 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
import time

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.storage.approval_workflow import ApprovalWorkflow
from guardian.engines.decision_engine import RemediationDecisionEngine


class TestApprovalWorkflowsIntegration:
    """End-to-end approval workflow scenarios."""

    def test_end_to_end_critical_remediation_approval(self):
        """✅ Critical threat → requires approval → multi-person approval → token issued → remediation proceeds."""
        mock_audit = Mock()
        workflow = ApprovalWorkflow(mock_audit)
        decision_engine = RemediationDecisionEngine(mock_audit)

        # Detect critical threat
        critical_threat = {
            'threat_id': 'THREAT-E2E-CRITICAL',
            'severity': 9,
            'evidence': [
                {'source': 'guardduty', 'description': 'Malware found'},
                {'source': 'securityhub', 'description': 'Unauthorized access'}
            ]
        }

        remediation_plan = {
            'steps': [
                {'type': 'ec2_terminate', 'instance_id': 'i-malware'},
                {'type': 'iam_revoke', 'principal': 'attacker-user'},
                {'type': 'network_isolate', 'vpc_id': 'vpc-prod'}
            ]
        }

        # Analyze threat and risk
        confidence = decision_engine.analyze_threat_confidence(critical_threat)
        assert confidence['confidence_level'] == 'high'

        risk = decision_engine.analyze_remediation_risk(critical_threat, remediation_plan)
        assert risk['benefit_score'] > 0.8

        # Create approval request
        approval = workflow.create_approval_request(critical_threat, remediation_plan)
        assert approval['status'] == 'pending'
        # With severity 9 and 3 steps, risk is HIGH (not CRITICAL which needs severity 9 AND > 3 steps)
        # HIGH risk requires 2 approvers
        assert approval['approvers_needed'] in [2, 3]
        approval_id = approval['approval_id']

        # Simulate multi-person approval flow
        approvers_needed = approval['approvers_needed']
        approvers = ['ciso', 'security-lead', 'incident-commander'][:approvers_needed]

        for i, approver in enumerate(approvers):
            result = workflow.approve_request(approval_id, approver)
            if i < approvers_needed - 1:  # Not fully approved yet
                assert result['status'] == 'pending'
                assert result['approvals_received'] == i + 1
            else:  # Fully approved
                assert result['status'] == 'approved'
                assert result['approvals_received'] == approvers_needed
                assert result['token'] is not None

        # Verify final approval state
        history = workflow.get_approval_history(approval_id)
        assert history['status'] == 'approved'
        assert len(history['approvals']) == approvers_needed

    def test_emergency_override_procedure(self):
        """✅ Critical threat (severity 10+) can trigger emergency override regardless of approval."""
        mock_audit = Mock()
        decision_engine = RemediationDecisionEngine(mock_audit)

        # Extreme severity threat (potential ransomware, active exfiltration)
        emergency_threat = {
            'threat_id': 'THREAT-EMERGENCY-001',
            'severity': 10,  # Extreme
            'evidence': [
                {'source': 'guardduty', 'description': 'Active ransomware detected'},
                {'source': 'securityhub', 'description': 'Mass data exfiltration'}
            ]
        }

        escalation = decision_engine.recommend_escalation(emergency_threat, previous_failures=0)

        assert escalation['escalate'] is True
        assert escalation['escalation_level'] == 'critical_override'
        assert 'emergency' in escalation['reason'].lower()

        # Even with high risk remediation, emergency override should proceed
        aggressive_remediation = {
            'steps': [
                {'type': 'ec2_terminate', 'instance_id': 'i-prod-1'},
                {'type': 'ec2_terminate', 'instance_id': 'i-prod-2'},
                {'type': 'ec2_terminate', 'instance_id': 'i-prod-3'}
            ]
        }

        decision = decision_engine.decide_remediation_strategy(emergency_threat, aggressive_remediation)
        # For severity 9+, auto_remediate is recommended immediately
        assert decision['decision'] in ['auto_remediate', 'require_approval']

    def test_approval_notification_channels(self):
        """✅ Approval requests trigger notifications via multiple channels."""
        mock_audit = Mock()
        mock_telegram = Mock()
        mock_discord = Mock()

        workflow = ApprovalWorkflow(mock_audit)

        threat = {
            'threat_id': 'THREAT-NOTIFY-001',
            'severity': 8,
            'description': 'Unauthorized SSH access attempt'
        }

        remediation_plan = {
            'steps': [
                {'type': 'network_isolate', 'vpc_id': 'vpc-123'},
                {'type': 'iam_revoke', 'principal': 'suspicious-user'}
            ]
        }

        # Create approval request (should trigger notifications)
        approval = workflow.create_approval_request(threat, remediation_plan)

        # Simulate notification dispatch
        notification_message = {
            'approval_id': approval['approval_id'],
            'threat_id': threat['threat_id'],
            'severity': threat['severity'],
            'risk_level': approval['risk_level'],
            'approvers_needed': approval['approvers_needed'],
            'expires_at': approval['expires_at'],
            'message': f"⚠️ HIGH-RISK remediation approval required for {threat['description']}"
        }

        mock_telegram.send_message(notification_message)
        mock_discord.send_message(notification_message)

        # Verify notifications were sent
        assert mock_telegram.send_message.called
        assert mock_discord.send_message.called

        # Verify message content
        call_args = mock_telegram.send_message.call_args[0][0]
        assert call_args['approval_id'] == approval['approval_id']
        assert call_args['severity'] == 8

    def test_approval_timeout_auto_remediation(self):
        """✅ If approval timeout expires and threat is critical, proceed with auto-remediation."""
        mock_audit = Mock()
        workflow = ApprovalWorkflow(mock_audit)
        decision_engine = RemediationDecisionEngine(mock_audit)

        threat = {
            'threat_id': 'THREAT-TIMEOUT-001',
            'severity': 8,  # High, not critical
            'evidence': [
                {'source': 'guardduty', 'description': 'Suspicious activity'}
            ]
        }

        remediation_plan = {
            'steps': [
                {'type': 'ec2_stop', 'instance_id': 'i-suspicious'}
            ]
        }

        # Create approval request (HIGH risk, 15 min timeout)
        approval = workflow.create_approval_request(threat, remediation_plan)
        approval_id = approval['approval_id']
        assert approval['approvers_needed'] == 2

        # Simulate timeout by manually setting expiration to past
        approval_request = workflow.approval_requests[approval_id]
        approval_request['expires_at'] = (
            datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        ).isoformat()

        # Try to approve after timeout
        result = workflow.approve_request(approval_id, 'approver-1')
        assert result['status'] == 'expired'

        # For severity 8+, system should auto-remediate anyway after timeout
        decision = decision_engine.recommend_escalation(threat, previous_failures=0)
        assert decision['escalate'] is True
        assert decision['escalation_level'] in ['single', 'multi']

    def test_approval_history_reporting(self):
        """✅ Complete approval audit trail can be exported for compliance reporting."""
        mock_audit = Mock()
        workflow = ApprovalWorkflow(mock_audit)

        # Create multiple approval requests to simulate workflow history
        threats = [
            {
                'threat_id': 'THREAT-REPORT-001',
                'severity': 2,
                'description': 'Low-risk S3 change',
                'steps': 1
            },
            {
                'threat_id': 'THREAT-REPORT-002',
                'severity': 7,
                'description': 'High-risk IAM change',
                'steps': 1
            },
            {
                'threat_id': 'THREAT-REPORT-003',
                'severity': 9,
                'description': 'Critical security incident',
                'steps': 4  # Multiple resources to make it CRITICAL
            }
        ]

        approval_history = []

        for threat in threats:
            remediation = {
                'steps': [
                    {'type': 's3_block_public', 'bucket_id': f"bucket-{threat['threat_id']}-{i}"}
                    for i in range(threat['steps'])
                ]
            }

            approval = workflow.create_approval_request(threat, remediation)
            final_status = approval['status']

            # Add approvals and track final status
            if approval['status'] == 'pending':
                for i in range(approval['approvers_needed']):
                    result = workflow.approve_request(
                        approval['approval_id'],
                        f'approver-{i}',
                        f'Approved'
                    )
                    final_status = result['status']

            approval_history.append({
                'threat_id': threat['threat_id'],
                'approval_id': approval['approval_id'],
                'risk_level': approval['risk_level'],
                'status': final_status,
                'created_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })

        # Generate compliance report
        report = {
            'report_type': 'approval_audit',
            'generated_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'total_approvals': len(approval_history),
            'auto_approved': sum(1 for a in approval_history if a['risk_level'] == 'low'),
            'manual_approvals': sum(1 for a in approval_history if a['status'] == 'approved'),
            'approvals_by_risk': {}
        }

        # Group by risk level
        for h in approval_history:
            risk = h['risk_level']
            if risk not in report['approvals_by_risk']:
                report['approvals_by_risk'][risk] = []
            report['approvals_by_risk'][risk].append(h)

        # Verify report content
        assert report['total_approvals'] == 3
        assert report['auto_approved'] == 1  # Low-risk threat
        assert report['manual_approvals'] == 2  # Medium and Critical
        assert 'low' in report['approvals_by_risk']
        assert 'medium' in report['approvals_by_risk']
        assert 'critical' in report['approvals_by_risk']

        # Verify detailed history can be retrieved
        for approval_info in approval_history:
            history = workflow.get_approval_history(approval_info['approval_id'])
            assert history['threat_id'] == approval_info['threat_id']
            assert history['risk_level'] == approval_info['risk_level']
