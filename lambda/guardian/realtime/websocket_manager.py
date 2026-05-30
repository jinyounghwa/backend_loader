"""WebSocket real-time updates for live dashboard."""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from collections import defaultdict
import uuid


class WebSocketManager:
    """Manage WebSocket client connections."""

    def __init__(self):
        self.clients: Dict[str, Dict[str, Any]] = {}
        self.user_clients: Dict[str, Set[str]] = defaultdict(set)

    def register_client(self, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """Register new WebSocket client."""
        client_id = client_info.get('client_id')
        user_id = client_info.get('user_id')

        self.clients[client_id] = {
            'client_id': client_id,
            'user_id': user_id,
            'connected_at': datetime.utcnow().isoformat(),
            'status': 'connected',
            'last_heartbeat': datetime.utcnow().isoformat()
        }

        if user_id:
            self.user_clients[user_id].add(client_id)

        return {
            'status': 'connected',
            'client_id': client_id,
            'timestamp': datetime.utcnow().isoformat()
        }

    def unregister_client(self, client_id: str) -> Dict[str, Any]:
        """Unregister and disconnect WebSocket client."""
        if client_id in self.clients:
            client = self.clients[client_id]
            user_id = client.get('user_id')

            if user_id and client_id in self.user_clients[user_id]:
                self.user_clients[user_id].remove(client_id)

            del self.clients[client_id]

            return {
                'status': 'disconnected',
                'client_id': client_id,
                'timestamp': datetime.utcnow().isoformat()
            }

        return {'status': 'not_found', 'client_id': client_id}

    def get_active_connections(self) -> int:
        """Get number of active connections."""
        return len(self.clients)

    def get_client_status(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client connection status."""
        return self.clients.get(client_id)

    def heartbeat(self, client_id: str) -> Dict[str, Any]:
        """Update client heartbeat."""
        if client_id in self.clients:
            self.clients[client_id]['last_heartbeat'] = datetime.utcnow().isoformat()
            return {'status': 'ok', 'client_id': client_id}

        return {'status': 'not_found', 'client_id': client_id}


class EventBroadcaster:
    """Broadcast events to all connected clients."""

    def __init__(self):
        self.broadcast_history: List[Dict[str, Any]] = []
        self.event_count: Dict[str, int] = defaultdict(int)

    def broadcast(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast event to all clients."""
        broadcast_id = str(uuid.uuid4())
        event_type = event.get('event_type', 'UNKNOWN')

        broadcast_record = {
            'broadcast_id': broadcast_id,
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'event': event,
            'status': 'delivered'
        }

        self.broadcast_history.append(broadcast_record)
        self.event_count[event_type] += 1

        return {
            'broadcast_id': broadcast_id,
            'event_type': event_type,
            'status': 'delivered',
            'timestamp': datetime.utcnow().isoformat()
        }

    def get_event_stats(self) -> Dict[str, int]:
        """Get event statistics."""
        return dict(self.event_count)

    def get_broadcast_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get broadcast history."""
        return self.broadcast_history[-limit:]


class SubscriptionManager:
    """Manage client event subscriptions."""

    def __init__(self):
        self.subscriptions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def subscribe(self, client_id: str, filter_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Subscribe client to events with filter criteria."""
        subscription = {
            'client_id': client_id,
            'filter': filter_criteria,
            'subscribed_at': datetime.utcnow().isoformat()
        }

        self.subscriptions[client_id].append(subscription)

        return {
            'status': 'subscribed',
            'client_id': client_id,
            'filter': filter_criteria
        }

    def unsubscribe(self, client_id: str, event_type: str) -> Dict[str, Any]:
        """Unsubscribe client from event type."""
        if client_id in self.subscriptions:
            # Remove subscriptions matching event_type
            before = len(self.subscriptions[client_id])
            self.subscriptions[client_id] = [
                s for s in self.subscriptions[client_id]
                if s['filter'].get('event_type') != event_type
            ]
            after = len(self.subscriptions[client_id])

            if before > after:
                return {
                    'status': 'unsubscribed',
                    'client_id': client_id,
                    'event_type': event_type
                }

        return {'status': 'not_found', 'client_id': client_id}

    def matches_subscription(self, client_id: str, event: Dict[str, Any]) -> bool:
        """Check if event matches client's subscriptions."""
        if client_id not in self.subscriptions:
            return False

        for subscription in self.subscriptions[client_id]:
            filter_criteria = subscription['filter']

            # Check event_type
            if filter_criteria.get('event_type') != event.get('event_type'):
                continue

            # Check severity if specified
            if 'severity' in filter_criteria:
                required_severity = filter_criteria['severity']
                event_severity = event.get('severity')

                if isinstance(required_severity, list):
                    if event_severity not in required_severity:
                        continue
                elif event_severity != required_severity:
                    continue

            return True

        return False

    def get_subscriptions(self, client_id: str) -> List[Dict[str, Any]]:
        """Get client's subscriptions."""
        return self.subscriptions.get(client_id, [])


class MessageRouter:
    """Route messages to appropriate clients."""

    def __init__(self):
        self.subscriptions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def add_subscription(self, client_id: str, filter_criteria: Any) -> None:
        """Add client subscription."""
        if isinstance(filter_criteria, str):
            # Simple event type
            self.subscriptions[client_id].append({
                'event_type': filter_criteria
            })
        else:
            # Complex filter
            self.subscriptions[client_id].append(filter_criteria)

    def route_event(self, event: Dict[str, Any]) -> Set[str]:
        """Route event to matching subscriptions."""
        recipients = set()
        event_type = event.get('event_type')
        event_severity = event.get('severity')

        for client_id, filters in self.subscriptions.items():
            for filter_spec in filters:
                # Check event type
                if filter_spec.get('event_type') != event_type:
                    continue

                # Check severity filter
                if 'severity' in filter_spec:
                    required_severities = filter_spec['severity']

                    if isinstance(required_severities, list):
                        if event_severity not in required_severities:
                            continue
                    else:
                        if event_severity != required_severities:
                            continue

                recipients.add(client_id)
                break

        return recipients

    def get_subscribers(self, event_type: str) -> Set[str]:
        """Get all subscribers for event type."""
        subscribers = set()

        for client_id, filters in self.subscriptions.items():
            for filter_spec in filters:
                if filter_spec.get('event_type') == event_type:
                    subscribers.add(client_id)
                    break

        return subscribers
