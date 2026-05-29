"""Notification prioritizer for AWS Guardian alerts."""

import logging
from typing import Dict, List, Any
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels."""
    CRITICAL = 1    # Immediate
    HIGH = 2        # 1 min batch
    MEDIUM = 3      # 5 min batch
    LOW = 4         # Daily summary


class NotificationPrioritizer:
    """Prioritize notifications based on threat level."""

    def __init__(self):
        """Initialize prioritizer."""
        self.priority_mapping = {
            'CRITICAL': NotificationPriority.CRITICAL,
            'HIGH': NotificationPriority.HIGH,
            'MEDIUM': NotificationPriority.MEDIUM,
            'LOW': NotificationPriority.LOW,
        }
        
        self.batch_windows = {
            NotificationPriority.CRITICAL: 0,      # No batching
            NotificationPriority.HIGH: 60,         # 1 minute
            NotificationPriority.MEDIUM: 300,      # 5 minutes
            NotificationPriority.LOW: 86400,       # 1 day
        }

    def classify_notification(
        self, alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify notification by priority.
        
        Args:
            alert: Alert dict with severity, type
            
        Returns:
            Classified notification with priority and delivery settings
        """
        severity = alert.get('severity', 'MEDIUM')
        priority = self.priority_mapping.get(severity, NotificationPriority.MEDIUM)
        
        return {
            'priority': priority.name,
            'priority_level': priority.value,
            'batch_window': self.batch_windows[priority],
            'channels': self._get_channels_for_priority(priority),
            'immediate': priority == NotificationPriority.CRITICAL,
        }

    def _get_channels_for_priority(
        self, priority: NotificationPriority
    ) -> List[str]:
        """Get delivery channels based on priority.
        
        Args:
            priority: Priority level
            
        Returns:
            List of delivery channels
        """
        if priority == NotificationPriority.CRITICAL:
            return ['telegram', 'slack', 'pagerduty']
        elif priority == NotificationPriority.HIGH:
            return ['telegram', 'slack', 'email']
        elif priority == NotificationPriority.MEDIUM:
            return ['email']
        else:
            return ['email_digest']

    def should_suppress(
        self, notification: Dict[str, Any], user_schedule: Dict[str, Any]
    ) -> bool:
        """Check if notification should be suppressed.
        
        Args:
            notification: Notification dict
            user_schedule: User's do-not-disturb schedule
            
        Returns:
            True if should suppress
        """
        priority = notification.get('priority')
        
        # Never suppress CRITICAL
        if priority == 'CRITICAL':
            return False
        
        # Check DND schedule
        dnd_enabled = user_schedule.get('do_not_disturb_enabled', False)
        if not dnd_enabled:
            return False
        
        # For DND, queue notification for delivery later
        return True

    def rank_notifications(
        self, notifications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank notifications by priority.
        
        Args:
            notifications: List of notifications
            
        Returns:
            Sorted list by priority
        """
        return sorted(
            notifications,
            key=lambda n: self.priority_mapping.get(
                n.get('severity', 'MEDIUM'),
                NotificationPriority.MEDIUM
            ).value
        )

    def calculate_notification_score(
        self, alert: Dict[str, Any]
    ) -> int:
        """Calculate notification urgency score (0-100).
        
        Args:
            alert: Alert dict
            
        Returns:
            Score (0-100)
        """
        score = 0
        
        # Severity (0-50)
        severity_map = {
            'CRITICAL': 50,
            'HIGH': 40,
            'MEDIUM': 25,
            'LOW': 10,
        }
        score += severity_map.get(alert.get('severity'), 10)
        
        # Type bonus
        alert_type = alert.get('type')
        if alert_type in ['security', 'compliance']:
            score += 20
        elif alert_type in ['cost', 'performance']:
            score += 10
        
        # Account impact
        if alert.get('account_count', 0) > 1:
            score += 10
        
        return min(score, 100)
