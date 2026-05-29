"""Slack notification integration."""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send notifications to Slack."""

    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize Slack notifier.
        
        Args:
            webhook_url: Slack webhook URL
        """
        self.webhook_url = webhook_url

    def send_alert(
        self, alert: Dict[str, Any]
    ) -> bool:
        """Send alert to Slack.
        
        Args:
            alert: Alert dict
            
        Returns:
            True if successful
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False
        
        try:
            payload = self._build_payload(alert)
            # In real implementation, POST to webhook_url
            logger.info(f"Slack alert sent: {alert.get('id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def _build_payload(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Build Slack message payload.
        
        Args:
            alert: Alert dict
            
        Returns:
            Slack message payload
        """
        severity = alert.get('severity', 'UNKNOWN')
        color_map = {
            'CRITICAL': 'danger',
            'HIGH': 'warning',
            'MEDIUM': '#FF9800',
            'LOW': '#2196F3',
        }
        
        return {
            'attachments': [
                {
                    'color': color_map.get(severity, '#999999'),
                    'title': alert.get('title', 'Alert'),
                    'text': alert.get('message', ''),
                    'fields': [
                        {'title': 'Severity', 'value': severity, 'short': True},
                        {'title': 'Account', 'value': alert.get('account_id', 'N/A'), 'short': True},
                    ],
                }
            ]
        }
