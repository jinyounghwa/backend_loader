"""WebSocket Event Broadcaster for real-time threat dashboard updates."""

from typing import Dict, List, Optional, Callable
from datetime import datetime
import uuid


class WebSocketEventBroadcaster:
    """Broadcasts real-time events to connected WebSocket clients."""

    def __init__(self, connection_manager=None):
        """Initialize WebSocket broadcaster."""
        self.connections = {}
        self.manager = connection_manager
        self.message_queue = []

    def broadcast_threat_detected(self, threat: Dict) -> Dict:
        """Broadcast new threat detection to all connected clients."""
        message = {
            'event_type': 'threat_detected',
            'timestamp': datetime.utcnow().isoformat(),
            'threat_id': threat.get('threat_id'),
            'threat_type': threat.get('threat_type'),
            'severity': threat.get('severity'),
            'account_id': threat.get('account_id'),
            'affected_resources': threat.get('affected_resources', []),
            'remediation_recommended': threat.get('remediation_recommended', 'EVALUATE')
        }

        self.broadcast_to_all(message)
        return message

    def broadcast_remediation_started(self, execution_id: str, threat_id: str) -> Dict:
        """Broadcast remediation execution start."""
        message = {
            'event_type': 'remediation_started',
            'timestamp': datetime.utcnow().isoformat(),
            'execution_id': execution_id,
            'threat_id': threat_id,
            'status': 'started'
        }

        self.broadcast_to_all(message)
        return message

    def broadcast_remediation_progress(self, execution_id: str, progress_percent: int,
                                       resources_status: Dict) -> Dict:
        """Broadcast real-time remediation progress."""
        message = {
            'event_type': 'remediation_progress',
            'timestamp': datetime.utcnow().isoformat(),
            'execution_id': execution_id,
            'progress_percent': progress_percent,
            'resources_status': resources_status,
            'current_action': resources_status.get('current_action', '')
        }

        self.broadcast_to_all(message)
        return message

    def broadcast_remediation_completed(self, execution_id: str, status: str,
                                        summary: Dict) -> Dict:
        """Broadcast remediation completion."""
        message = {
            'event_type': 'remediation_completed',
            'timestamp': datetime.utcnow().isoformat(),
            'execution_id': execution_id,
            'status': status,
            'summary': summary
        }

        self.broadcast_to_all(message)
        return message

    def broadcast_compliance_status_change(self, framework: str, new_status: str) -> Dict:
        """Broadcast compliance metric update."""
        message = {
            'event_type': 'compliance_status_changed',
            'timestamp': datetime.utcnow().isoformat(),
            'framework': framework,
            'status': new_status
        }

        self.broadcast_to_all(message)
        return message

    def broadcast_playbook_execution(self, execution_id: str, playbook_name: str,
                                     status: str) -> Dict:
        """Broadcast playbook execution events."""
        message = {
            'event_type': 'playbook_execution',
            'timestamp': datetime.utcnow().isoformat(),
            'execution_id': execution_id,
            'playbook_name': playbook_name,
            'status': status
        }

        self.broadcast_to_all(message)
        return message

    def register_client_connection(self, connection_id: str, filters: Optional[Dict] = None) -> Dict:
        """Register WebSocket client with optional event filters."""
        connection = {
            'connection_id': connection_id,
            'connected_at': datetime.utcnow().isoformat(),
            'filters': filters or {},
            'subscriptions': []
        }

        self.connections[connection_id] = connection
        return connection

    def unregister_client_connection(self, connection_id: str) -> bool:
        """Unregister WebSocket client."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            return True
        return False

    def send_to_client(self, connection_id: str, message: Dict) -> bool:
        """Send message to specific client."""
        if connection_id not in self.connections:
            return False

        # In real implementation, would send via WebSocket
        return True

    def broadcast_to_all(self, message: Dict, filter_fn: Optional[Callable] = None) -> int:
        """Broadcast to all connected clients with optional filtering."""
        recipient_count = 0

        for connection_id in list(self.connections.keys()):
            if filter_fn and not filter_fn(self.connections[connection_id]):
                continue

            self.send_to_client(connection_id, message)
            recipient_count += 1

        return recipient_count

    def broadcast_to_account(self, account_id: str, message: Dict) -> int:
        """Broadcast to clients filtered by account."""
        def account_filter(connection):
            return connection.get('account_id') == account_id or 'account_id' not in connection

        return self.broadcast_to_all(message, filter_fn=account_filter)

    def get_connection_stats(self) -> Dict:
        """Get broadcaster connection statistics."""
        return {
            'total_connections': len(self.connections),
            'active_connections': sum(1 for c in self.connections.values()
                                       if c.get('status') == 'active'),
            'queued_messages': len(self.message_queue)
        }

    def queue_message(self, message: Dict) -> str:
        """Queue message for batch broadcasting."""
        message_id = str(uuid.uuid4())
        self.message_queue.append({
            'id': message_id,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        })
        return message_id

    def flush_queue(self) -> int:
        """Broadcast all queued messages and clear queue."""
        count = 0
        for queued in self.message_queue:
            self.broadcast_to_all(queued['message'])
            count += 1

        self.message_queue.clear()
        return count
