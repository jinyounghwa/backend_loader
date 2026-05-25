"""Approval Workflow - Risk-based approval requirements for remediation actions."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid


class RiskLevel(Enum):
    """Risk levels for remediation actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(Enum):
    """Approval workflow statuses."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


class ApprovalWorkflow:
    """Manage approval workflows with risk-based requirements."""

    # Risk level to approval requirements mapping
    APPROVAL_REQUIREMENTS = {
        RiskLevel.LOW.value: {'required': False, 'approvers': 0, 'timeout_minutes': 0},
        RiskLevel.MEDIUM.value: {'required': True, 'approvers': 1, 'timeout_minutes': 30},
        RiskLevel.HIGH.value: {'required': True, 'approvers': 2, 'timeout_minutes': 15},
        RiskLevel.CRITICAL.value: {'required': True, 'approvers': 3, 'timeout_minutes': 5}
    }

    def __init__(self, audit_logger):
        """Initialize approval workflow manager."""
        self.audit = audit_logger
        self.approval_requests = {}
        self.approval_tokens = {}

    def determine_risk_level(self, threat: Dict, remediation_plan: Dict) -> str:
        """
        Determine risk level based on threat and remediation details.

        Args:
            threat: Threat detection details
            remediation_plan: Proposed remediation actions

        Returns:
            Risk level: 'low|medium|high|critical'
        """
        threat_severity = threat.get('severity', 5)
        affected_resources = len(remediation_plan.get('steps', []))

        # Risk calculation
        if threat_severity >= 9 and affected_resources > 3:
            return RiskLevel.CRITICAL.value
        elif threat_severity >= 8 or affected_resources >= 3:
            return RiskLevel.HIGH.value
        elif threat_severity >= 6 or affected_resources >= 2:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.LOW.value

    def create_approval_request(self, threat: Dict, remediation_plan: Dict) -> Dict:
        """
        Create approval request with auto-approval for low-risk items.

        Args:
            threat: Threat details
            remediation_plan: Proposed remediation

        Returns:
            {
                'approval_id': uuid,
                'status': 'auto_approved|pending',
                'risk_level': str,
                'approvers_needed': int,
                'token': str,  # For low-risk auto-approved only
                'expires_at': iso_timestamp
            }
        """
        approval_id = str(uuid.uuid4())
        risk_level = self.determine_risk_level(threat, remediation_plan)

        approval_request = {
            'approval_id': approval_id,
            'threat_id': threat.get('threat_id'),
            'risk_level': risk_level,
            'remediation_plan': remediation_plan,
            'created_at': datetime.utcnow().isoformat(),
            'approvals': [],
            'rejected': False,
            'rejection_reason': None
        }

        # Low-risk items are auto-approved
        if risk_level == RiskLevel.LOW.value:
            approval_request['status'] = ApprovalStatus.AUTO_APPROVED.value
            token = self._generate_approval_token(approval_id, 0)  # No timeout for auto-approved
            approval_request['token'] = token
            approval_request['expires_at'] = None

            self.audit.log_approval(approval_id, {
                'action': 'auto_approved',
                'risk_level': risk_level
            })

        else:
            # Higher-risk items require approval
            approval_request['status'] = ApprovalStatus.PENDING.value
            requirements = self.APPROVAL_REQUIREMENTS[risk_level]
            approval_request['approvers_needed'] = requirements['approvers']
            approval_request['timeout_minutes'] = requirements['timeout_minutes']

            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(minutes=requirements['timeout_minutes'])
            approval_request['expires_at'] = expires_at.isoformat()

        # Store approval request
        self.approval_requests[approval_id] = approval_request

        return {
            'approval_id': approval_id,
            'status': approval_request['status'],
            'risk_level': risk_level,
            'approvers_needed': approval_request.get('approvers_needed', 0),
            'token': approval_request.get('token'),
            'expires_at': approval_request.get('expires_at')
        }

    def approve_request(self, approval_id: str, approver_id: str, comments: str = '') -> Dict:
        """
        Record approval from an approver.

        Args:
            approval_id: Approval request ID
            approver_id: ID of approver (user/role)
            comments: Approval comments

        Returns:
            {
                'status': 'approved|pending|rejected|expired',
                'approvals_received': int,
                'approvals_needed': int,
                'token': str  # If now approved
            }
        """
        result = {
            'approval_id': approval_id,
            'approver_id': approver_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        if approval_id not in self.approval_requests:
            result['status'] = 'not_found'
            return result

        approval_request = self.approval_requests[approval_id]

        # Check expiration
        if approval_request.get('expires_at'):
            expires_at = datetime.fromisoformat(approval_request['expires_at'])
            if datetime.utcnow() > expires_at:
                approval_request['status'] = ApprovalStatus.EXPIRED.value
                result['status'] = 'expired'
                return result

        # Prevent duplicate approvals from same approver
        approver_ids = [a['approver_id'] for a in approval_request.get('approvals', [])]
        if approver_id in approver_ids:
            result['status'] = 'duplicate'
            return result

        # Record approval
        approval_request['approvals'].append({
            'approver_id': approver_id,
            'timestamp': result['timestamp'],
            'comments': comments
        })

        result['approvals_received'] = len(approval_request['approvals'])
        result['approvals_needed'] = approval_request.get('approvers_needed', 0)

        # Check if fully approved
        if result['approvals_received'] >= result['approvals_needed']:
            approval_request['status'] = ApprovalStatus.APPROVED.value
            token = self._generate_approval_token(approval_id, 60)  # 60-minute token
            result['status'] = 'approved'
            result['token'] = token

            self.audit.log_approval(approval_id, {
                'action': 'approved',
                'approvers': result['approvals_received']
            })
        else:
            result['status'] = 'pending'

        return result

    def reject_request(self, approval_id: str, rejector_id: str, reason: str = '') -> Dict:
        """Reject an approval request."""
        result = {
            'approval_id': approval_id,
            'rejector_id': rejector_id
        }

        if approval_id not in self.approval_requests:
            result['status'] = 'not_found'
            return result

        approval_request = self.approval_requests[approval_id]
        approval_request['status'] = ApprovalStatus.REJECTED.value
        approval_request['rejected'] = True
        approval_request['rejection_reason'] = reason
        approval_request['rejected_at'] = datetime.utcnow().isoformat()
        approval_request['rejected_by'] = rejector_id

        result['status'] = 'rejected'

        self.audit.log_approval(approval_id, {
            'action': 'rejected',
            'reason': reason
        })

        return result

    def validate_token(self, token: str) -> Dict:
        """Validate an approval token."""
        if token not in self.approval_tokens:
            return {
                'valid': False,
                'error': 'Token not found'
            }

        token_data = self.approval_tokens[token]

        # Check expiration
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.utcnow() > expires_at:
            return {
                'valid': False,
                'error': 'Token expired'
            }

        return {
            'valid': True,
            'approval_id': token_data['approval_id'],
            'expires_at': token_data['expires_at']
        }

    def get_approval_history(self, approval_id: str) -> Dict:
        """Get complete approval history for audit trail."""
        if approval_id not in self.approval_requests:
            return {'status': 'not_found'}

        approval_request = self.approval_requests[approval_id]

        return {
            'approval_id': approval_id,
            'threat_id': approval_request.get('threat_id'),
            'risk_level': approval_request.get('risk_level'),
            'status': approval_request.get('status'),
            'created_at': approval_request.get('created_at'),
            'approvals': approval_request.get('approvals', []),
            'rejected': approval_request.get('rejected', False),
            'rejection_reason': approval_request.get('rejection_reason'),
            'expires_at': approval_request.get('expires_at')
        }

    def _generate_approval_token(self, approval_id: str, timeout_minutes: int) -> str:
        """Generate a time-limited approval token."""
        token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes) if timeout_minutes > 0 else datetime.utcnow() + timedelta(days=1)

        self.approval_tokens[token] = {
            'approval_id': approval_id,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat()
        }

        return token
