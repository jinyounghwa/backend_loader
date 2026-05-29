"""Batch notification delivery system."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class BatchNotifier:
    """Batch notifications for efficient delivery."""

    def __init__(self):
        """Initialize batch notifier."""
        self.batches = defaultdict(list)
        self.delivery_schedule = {}

    def add_to_batch(
        self,
        notification: Dict[str, Any],
        batch_window: int,
    ) -> bool:
        """Add notification to batch queue.
        
        Args:
            notification: Notification to batch
            batch_window: Batching window in seconds
            
        Returns:
            True if added
        """
        try:
            batch_key = f"{notification['priority']}_{batch_window}"
            
            # Deduplicate
            if not self._is_duplicate(notification, batch_key):
                self.batches[batch_key].append({
                    'notification': notification,
                    'queued_at': datetime.now(timezone.utc).isoformat(),
                })
                
                # Schedule delivery
                self._schedule_delivery(batch_key, batch_window)
                logger.info(f"Batched notification: {batch_key}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to batch notification: {e}")
            return False

    def _is_duplicate(
        self, notification: Dict[str, Any], batch_key: str
    ) -> bool:
        """Check if notification is duplicate.
        
        Args:
            notification: Notification to check
            batch_key: Batch key
            
        Returns:
            True if duplicate
        """
        alert_id = notification.get('id')
        if not alert_id:
            return False
        
        for item in self.batches[batch_key]:
            if item['notification'].get('id') == alert_id:
                return True
        
        return False

    def _schedule_delivery(self, batch_key: str, window_seconds: int):
        """Schedule batch delivery.
        
        Args:
            batch_key: Batch identifier
            window_seconds: Delivery window
        """
        if batch_key not in self.delivery_schedule:
            delivery_time = (
                datetime.now(timezone.utc) +
                timedelta(seconds=window_seconds)
            ).isoformat()
            self.delivery_schedule[batch_key] = delivery_time

    def get_ready_batches(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get batches ready for delivery.
        
        Returns:
            Dict of ready batches
        """
        now = datetime.now(timezone.utc)
        ready = {}
        
        for batch_key, delivery_time_str in list(self.delivery_schedule.items()):
            delivery_time = datetime.fromisoformat(delivery_time_str)
            
            if now >= delivery_time:
                ready[batch_key] = self.batches[batch_key]
                del self.delivery_schedule[batch_key]
        
        return ready

    def aggregate_batch(
        self, batch: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate notifications in batch.
        
        Args:
            batch: List of notifications
            
        Returns:
            Aggregated summary
        """
        if not batch:
            return {}
        
        by_type = defaultdict(int)
        accounts = set()
        total_cost_impact = 0.0
        
        for item in batch:
            notif = item['notification']
            alert_type = notif.get('type')
            by_type[alert_type] += 1
            
            if notif.get('account_id'):
                accounts.add(notif['account_id'])
            
            total_cost_impact += notif.get('cost_impact', 0.0)
        
        return {
            'count': len(batch),
            'by_type': dict(by_type),
            'accounts_affected': len(accounts),
            'total_cost_impact': total_cost_impact,
            'items': batch,
        }

    def apply_rate_limiting(
        self, channel: str, limit_per_hour: int
    ) -> bool:
        """Check rate limiting for channel.
        
        Args:
            channel: Channel name (telegram, email, etc.)
            limit_per_hour: Max messages per hour
            
        Returns:
            True if within limit
        """
        # Simplified rate limiter
        key = f"rate_limit_{channel}"
        count = getattr(self, key, 0)
        
        if count >= limit_per_hour:
            return False
        
        setattr(self, key, count + 1)
        return True

    def prepare_delivery_payload(
        self, batch: Dict[str, Any], channel: str
    ) -> Optional[Dict[str, Any]]:
        """Prepare payload for delivery to channel.
        
        Args:
            batch: Aggregated batch
            channel: Delivery channel
            
        Returns:
            Payload for channel or None
        """
        if not batch:
            return None
        
        if channel == 'telegram':
            return {
                'type': 'telegram',
                'message': f"🚨 {batch['count']} alerts: {batch['by_type']}",
                'notifications': batch['items'],
            }
        elif channel == 'slack':
            return {
                'type': 'slack',
                'blocks': self._format_slack_message(batch),
                'notifications': batch['items'],
            }
        elif channel == 'email':
            return {
                'type': 'email',
                'subject': f"AWS Guardian Alert Summary ({batch['count']} alerts)",
                'body': self._format_email_body(batch),
                'notifications': batch['items'],
            }
        
        return None

    def _format_slack_message(self, batch: Dict[str, Any]) -> List[Dict]:
        """Format batch as Slack message blocks.
        
        Args:
            batch: Aggregated batch
            
        Returns:
            Slack message blocks
        """
        return [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f"🚨 {batch['count']} Alerts",
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*Types:* {batch['by_type']}\n*Accounts:* {batch['accounts_affected']}\n*Cost Impact:* ${batch['total_cost_impact']:.2f}",
                }
            },
        ]

    def _format_email_body(self, batch: Dict[str, Any]) -> str:
        """Format batch as email body.
        
        Args:
            batch: Aggregated batch
            
        Returns:
            Email body text
        """
        return f"""
AWS Guardian Alert Summary

Total Alerts: {batch['count']}
Alert Types: {batch['by_type']}
Accounts Affected: {batch['accounts_affected']}
Estimated Cost Impact: ${batch['total_cost_impact']:.2f}

Review these alerts in your dashboard for details.
"""
