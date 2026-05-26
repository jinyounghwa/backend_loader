"""Playbook Approval Service for managing approval workflows on automated remediation."""

from typing import List, Dict, Optional
from datetime import datetime
import uuid


class PlaybookApprovalService:
    """Manages approval workflows for playbook execution."""

    def __init__(self, audit_logger=None):
        """Initialize approval service."""
        self.audit = audit_logger
        self.approvals = {}
        self.approval_groups = {}

    def request_approval(self, execution_id: str, threat: Dict, playbook: Dict,
                        actions: List[Dict]) -> Dict:
        """Request approval for playbook execution."""
        approval_id = str(uuid.uuid4())

        approval = {
            'approval_id': approval_id,
            'execution_id': execution_id,
            'playbook_id': playbook['playbook_id'],
            'threat_id': threat.get('threat_id'),
            'threat_type': threat.get('threat_type'),
            'severity': threat.get('severity'),
            'approval_group': playbook.get('approval_group'),
            'status': 'PENDING',
            'actions': actions,
            'requested_at': datetime.utcnow().isoformat(),
            'expires_at': None,
            'approved_by': None,
            'approved_at': None,
            'rejection_reason': None,
            'comments': []
        }

        self.approvals[approval_id] = approval
        return approval

    def approve_execution(self, execution_id: str, approver_id: str,
                         reason: str = '') -> Dict:
        """Approve pending execution."""
        # Find approval by execution_id
        approval = None
        approval_id = None

        for aid, appr in self.approvals.items():
            if appr['execution_id'] == execution_id:
                approval = appr
                approval_id = aid
                break

        if not approval:
            return {
                'success': False,
                'message': 'Approval request not found'
            }

        if approval['status'] != 'PENDING':
            return {
                'success': False,
                'message': f'Cannot approve: status is {approval["status"]}'
            }

        approval['status'] = 'APPROVED'
        approval['approved_by'] = approver_id
        approval['approved_at'] = datetime.utcnow().isoformat()
        approval['approval_reason'] = reason

        return {
            'success': True,
            'approval_id': approval_id,
            'execution_id': execution_id,
            'status': 'APPROVED'
        }

    def reject_execution(self, execution_id: str, approver_id: str,
                        reason: str = '') -> Dict:
        """Reject execution."""
        # Find approval by execution_id
        approval = None
        approval_id = None

        for aid, appr in self.approvals.items():
            if appr['execution_id'] == execution_id:
                approval = appr
                approval_id = aid
                break

        if not approval:
            return {
                'success': False,
                'message': 'Approval request not found'
            }

        if approval['status'] != 'PENDING':
            return {
                'success': False,
                'message': f'Cannot reject: status is {approval["status"]}'
            }

        approval['status'] = 'REJECTED'
        approval['rejected_by'] = approver_id
        approval['rejected_at'] = datetime.utcnow().isoformat()
        approval['rejection_reason'] = reason

        return {
            'success': True,
            'approval_id': approval_id,
            'execution_id': execution_id,
            'status': 'REJECTED'
        }

    def get_pending_approvals(self) -> List[Dict]:
        """Get list of pending approval requests."""
        pending = []
        for approval in self.approvals.values():
            if approval['status'] == 'PENDING':
                pending.append(approval)
        return pending

    def get_approval_status(self, execution_id: str) -> Optional[Dict]:
        """Get approval status for execution."""
        for approval in self.approvals.values():
            if approval['execution_id'] == execution_id:
                return approval
        return None

    def configure_approval_group(self, playbook_id: str, approval_group: str) -> Dict:
        """Configure which team approves this playbook."""
        group_config = {
            'group_id': str(uuid.uuid4()),
            'playbook_id': playbook_id,
            'group_name': approval_group,
            'members': [],
            'required_approvers': 1,
            'created_at': datetime.utcnow().isoformat()
        }

        self.approval_groups[group_config['group_id']] = group_config
        return group_config

    def add_approval_group_member(self, group_id: str, user_id: str) -> bool:
        """Add member to approval group."""
        if group_id in self.approval_groups:
            if user_id not in self.approval_groups[group_id]['members']:
                self.approval_groups[group_id]['members'].append(user_id)
            return True
        return False

    def get_approval_groups(self) -> Dict:
        """Get all approval groups."""
        return self.approval_groups

    def add_approval_comment(self, approval_id: str, commenter_id: str,
                           comment: str) -> Dict:
        """Add comment to approval request."""
        if approval_id not in self.approvals:
            return {'success': False, 'message': 'Approval not found'}

        approval = self.approvals[approval_id]
        comment_obj = {
            'comment_id': str(uuid.uuid4()),
            'commenter_id': commenter_id,
            'text': comment,
            'timestamp': datetime.utcnow().isoformat()
        }

        approval['comments'].append(comment_obj)
        return {
            'success': True,
            'comment_id': comment_obj['comment_id']
        }

    def get_approval_stats(self) -> Dict:
        """Get approval workflow statistics."""
        total = len(self.approvals)
        pending = sum(1 for a in self.approvals.values() if a['status'] == 'PENDING')
        approved = sum(1 for a in self.approvals.values() if a['status'] == 'APPROVED')
        rejected = sum(1 for a in self.approvals.values() if a['status'] == 'REJECTED')

        return {
            'total_approvals': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'approval_rate': (approved / total * 100) if total > 0 else 0
        }
