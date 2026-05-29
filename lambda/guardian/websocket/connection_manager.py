"""Dashboard Connection Manager for WebSocket connection lifecycle."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
import uuid


class DashboardConnectionManager:
    """Manages WebSocket connection lifecycle and subscriptions."""

    def __init__(self):
        """Initialize connection manager."""
        self.connections = {}
        self.subscriptions = {}  # threat_id -> [connection_ids]
        self.account_subscriptions = {}  # account_id -> [connection_ids]

    def register_connection(self, connection_id: str, user_id: str,
                          account_id: Optional[str] = None) -> Dict:
        """Register new WebSocket connection."""
        connection = {
            'connection_id': connection_id,
            'user_id': user_id,
            'account_id': account_id,
            'connected_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'last_activity': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'subscriptions': [],
            'status': 'active'
        }

        self.connections[connection_id] = connection
        return connection

    def unregister_connection(self, connection_id: str) -> bool:
        """Unregister closed WebSocket connection."""
        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]

        # Remove from all subscriptions
        for threat_id in list(self.subscriptions.keys()):
            if connection_id in self.subscriptions[threat_id]:
                self.subscriptions[threat_id].remove(connection_id)
                if not self.subscriptions[threat_id]:
                    del self.subscriptions[threat_id]

        # Remove from account subscriptions
        for account_id in list(self.account_subscriptions.keys()):
            if connection_id in self.account_subscriptions[account_id]:
                self.account_subscriptions[account_id].remove(connection_id)
                if not self.account_subscriptions[account_id]:
                    del self.account_subscriptions[account_id]

        del self.connections[connection_id]
        return True

    def subscribe_to_threat(self, connection_id: str, threat_id: str) -> bool:
        """Subscribe client to specific threat updates."""
        if connection_id not in self.connections:
            return False

        if threat_id not in self.subscriptions:
            self.subscriptions[threat_id] = []

        if connection_id not in self.subscriptions[threat_id]:
            self.subscriptions[threat_id].append(connection_id)
            self.connections[connection_id]['subscriptions'].append(threat_id)

        return True

    def subscribe_to_account(self, connection_id: str, account_id: str) -> bool:
        """Subscribe client to account-wide threat updates."""
        if connection_id not in self.connections:
            return False

        if account_id not in self.account_subscriptions:
            self.account_subscriptions[account_id] = []

        if connection_id not in self.account_subscriptions[account_id]:
            self.account_subscriptions[account_id].append(connection_id)
            self.connections[connection_id]['subscriptions'].append(f'account:{account_id}')

        return True

    def unsubscribe_from_threat(self, connection_id: str, threat_id: str) -> bool:
        """Unsubscribe from threat."""
        if threat_id not in self.subscriptions:
            return False

        if connection_id in self.subscriptions[threat_id]:
            self.subscriptions[threat_id].remove(connection_id)
            if not self.subscriptions[threat_id]:
                del self.subscriptions[threat_id]

            if connection_id in self.connections:
                if threat_id in self.connections[connection_id]['subscriptions']:
                    self.connections[connection_id]['subscriptions'].remove(threat_id)

            return True

        return False

    def get_subscriptions(self, connection_id: str) -> List[str]:
        """Get all subscriptions for connection."""
        if connection_id not in self.connections:
            return []

        return self.connections[connection_id].get('subscriptions', [])

    def get_subscribers(self, threat_id: str) -> List[str]:
        """Get all clients subscribed to threat."""
        return self.subscriptions.get(threat_id, [])

    def get_account_subscribers(self, account_id: str) -> List[str]:
        """Get all clients subscribed to account."""
        return self.account_subscriptions.get(account_id, [])

    def update_connection_activity(self, connection_id: str) -> bool:
        """Update last activity timestamp for connection."""
        if connection_id not in self.connections:
            return False

        self.connections[connection_id]['last_activity'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        return True

    def get_stale_connections(self, timeout_minutes: int = 30) -> List[str]:
        """Get connections with no activity (for cleanup)."""
        cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=timeout_minutes)
        stale = []

        for connection_id, connection in self.connections.items():
            last_activity = datetime.fromisoformat(connection['last_activity'])
            if last_activity < cutoff_time:
                stale.append(connection_id)

        return stale

    def cleanup_stale_connections(self, timeout_minutes: int = 30) -> int:
        """Remove idle connections."""
        stale = self.get_stale_connections(timeout_minutes)
        count = 0

        for connection_id in stale:
            if self.unregister_connection(connection_id):
                count += 1

        return count

    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            'total_connections': len(self.connections),
            'active_connections': sum(1 for c in self.connections.values()
                                       if c.get('status') == 'active'),
            'total_subscriptions': sum(len(v) for v in self.subscriptions.values()),
            'total_threat_subscriptions': len(self.subscriptions),
            'total_account_subscriptions': len(self.account_subscriptions)
        }

    def get_connection_info(self, connection_id: str) -> Optional[Dict]:
        """Get information about specific connection."""
        return self.connections.get(connection_id)

    def list_all_connections(self) -> List[Dict]:
        """List all active connections."""
        return list(self.connections.values())
