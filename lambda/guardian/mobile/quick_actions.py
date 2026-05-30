"""Quick action execution from mobile."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


class QuickActionExecutor:
    """Execute quick actions from mobile app."""

    def __init__(self):
        self.executed_actions: Dict[str, Dict[str, Any]] = {}
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action immediately."""
        action_id = str(uuid.uuid4())
        action_type = action.get('action')

        result = {
            'action_id': action_id,
            'action': action_type,
            'resource_id': action.get('instance_id') or action.get('bucket_id') or action.get('user_id'),
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat(),
            'details': action
        }

        self.executed_actions[action_id] = result

        return result

    def initiate_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate action with confirmation requirement."""
        confirmation_id = str(uuid.uuid4())
        action_type = action.get('action')

        confirmation = {
            'confirmation_id': confirmation_id,
            'action': action_type,
            'resource_id': action.get('role_id') or action.get('instance_id'),
            'status': 'pending_confirmation',
            'initiated_at': datetime.utcnow().isoformat(),
            'action_details': action
        }

        self.pending_confirmations[confirmation_id] = confirmation

        return {
            'confirmation_id': confirmation_id,
            'action': action_type,
            'status': 'pending_confirmation',
            'expires_at': '2026-05-30T15:00:00'
        }

    def confirm_action(self, confirmation_id: str) -> Dict[str, Any]:
        """Confirm and execute pending action."""
        if confirmation_id not in self.pending_confirmations:
            return {'status': 'not_found', 'confirmation_id': confirmation_id}

        confirmation = self.pending_confirmations[confirmation_id]
        action_id = str(uuid.uuid4())

        result = {
            'action_id': action_id,
            'confirmation_id': confirmation_id,
            'action': confirmation['action'],
            'status': 'completed',
            'executed_at': datetime.utcnow().isoformat()
        }

        self.executed_actions[action_id] = result
        del self.pending_confirmations[confirmation_id]

        return result

    def cancel_action(self, confirmation_id: str) -> Dict[str, Any]:
        """Cancel pending action."""
        if confirmation_id in self.pending_confirmations:
            del self.pending_confirmations[confirmation_id]
            return {'status': 'cancelled', 'confirmation_id': confirmation_id}

        return {'status': 'not_found', 'confirmation_id': confirmation_id}

    def get_action_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get history of executed actions."""
        actions = list(self.executed_actions.values())
        return sorted(
            actions[-limit:],
            key=lambda a: a['timestamp'],
            reverse=True
        )
