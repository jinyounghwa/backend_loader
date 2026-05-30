"""Mobile push notification service."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


class NotificationService:
    """Send push notifications to mobile devices."""

    def __init__(self):
        self.sent_notifications: Dict[str, Dict[str, Any]] = {}
        self.notification_queue: List[Dict[str, Any]] = []

    def send_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification to mobile device."""
        notification_id = str(uuid.uuid4())

        record = {
            'notification_id': notification_id,
            'device_token': notification.get('device_token'),
            'title': notification.get('title'),
            'message': notification.get('message'),
            'severity': notification.get('severity'),
            'actions': notification.get('actions', []),
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'sent'
        }

        self.sent_notifications[notification_id] = record
        self.notification_queue.append(record)

        return {
            'notification_id': notification_id,
            'status': 'sent',
            'timestamp': record['timestamp'],
            'actions': record.get('actions')
        }

    def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Send notifications to multiple devices."""
        delivered = 0
        failed = 0

        for notification in notifications:
            try:
                self.send_notification(notification)
                delivered += 1
            except Exception:
                failed += 1

        return {
            'delivered': delivered,
            'failed': failed,
            'status': 'completed',
            'total': len(notifications)
        }

    def get_notification_history(
        self,
        device_token: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notification history for device."""
        device_notifications = [
            n for n in self.sent_notifications.values()
            if n['device_token'] == device_token
        ]

        return sorted(
            device_notifications[-limit:],
            key=lambda n: n['timestamp'],
            reverse=True
        )

    def mark_notification_read(self, notification_id: str) -> Dict[str, Any]:
        """Mark notification as read."""
        if notification_id in self.sent_notifications:
            self.sent_notifications[notification_id]['status'] = 'read'
            return {'status': 'updated', 'notification_id': notification_id}

        return {'status': 'not_found', 'notification_id': notification_id}
