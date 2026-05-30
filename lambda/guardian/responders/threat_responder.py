"""Real-time threat response automation."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class ThreatResponder:
    """Automatically respond to detected threats."""

    SEVERITY_ACTIONS = {
        'CRITICAL': 'ISOLATE',
        'HIGH': 'BLOCK',
        'MEDIUM': 'ALERT',
        'LOW': 'MONITOR'
    }

    def respond_to_threat(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """Determine and execute response to threat."""
        severity = threat.get('severity', 'LOW')
        action = self.SEVERITY_ACTIONS.get(severity, 'ALERT')

        return {
            'threat_id': threat.get('id'),
            'action': action,
            'resource_id': threat.get('resource_id'),
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat()
        }


class ResponseExecutor:
    """Execute response actions."""

    def __init__(self):
        self.scheduled_actions: Dict[str, Dict[str, Any]] = {}

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a response action."""
        action_type = action.get('action')
        resource_id = action.get('resource_id')

        return {
            'status': 'executed',
            'action': action_type,
            'resource_id': resource_id,
            'timestamp': datetime.utcnow().isoformat()
        }

    def execute_delayed_action(
        self,
        action: Dict[str, Any],
        delay_seconds: int
    ) -> Dict[str, Any]:
        """Schedule an action to execute after delay."""
        action_id = f"action-{len(self.scheduled_actions)}"

        self.scheduled_actions[action_id] = {
            'action': action,
            'delay_seconds': delay_seconds,
            'scheduled_at': datetime.utcnow().isoformat(),
            'execute_at': (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
        }

        return {
            'id': action_id,
            'scheduled': True,
            'delay_seconds': delay_seconds
        }

    def cancel_scheduled_action(self, action_id: str) -> Dict[str, Any]:
        """Cancel a scheduled action."""
        if action_id in self.scheduled_actions:
            del self.scheduled_actions[action_id]
            return {'status': 'cancelled', 'action_id': action_id}

        return {'status': 'not_found', 'action_id': action_id}


class ResponseTracker:
    """Track threat response history and audit trail."""

    def __init__(self):
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self.audit_log: List[Dict[str, Any]] = []

    def track_response(self, response: Dict[str, Any]) -> None:
        """Track a response action."""
        threat_id = response.get('threat_id')

        if threat_id not in self.history:
            self.history[threat_id] = []

        record = {
            'action': response.get('action'),
            'status': response.get('status', 'pending'),
            'timestamp': response.get('timestamp', datetime.utcnow().isoformat()),
            'details': response
        }

        self.history[threat_id].append(record)
        self.audit_log.append(record)

    def get_response_history(self, threat_id: str) -> List[Dict[str, Any]]:
        """Get response history for a threat."""
        return self.history.get(threat_id, [])

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get complete audit log."""
        return self.audit_log

    def get_response_status(self, threat_id: str) -> Optional[str]:
        """Get current response status for threat."""
        history = self.get_response_history(threat_id)
        if history:
            return history[-1]['status']
        return None
