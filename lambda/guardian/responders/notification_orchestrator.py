"""Multi-Channel Notification Orchestrator"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class NotificationOrchestrator:
    """Coordinate notifications across multiple channels (Slack, Teams, etc.)"""

    def __init__(self, slack_client, teams_webhook: str):
        """
        Args:
            slack_client: Slack Bot API client
            teams_webhook: Microsoft Teams webhook URL
        """
        from .slack_responder import SlackResponder
        from .teams_responder import TeamsResponder

        self.slack = SlackResponder(slack_client)
        self.teams = TeamsResponder(teams_webhook)
        self.notification_history = []
        self.throttle_cache = {}

    def send_to_all_channels(self, alert: Dict) -> Dict:
        """
        Send alert to all configured channels

        Args:
            alert: Alert to send

        Returns:
            Delivery result with status for each channel
        """
        try:
            results = {
                'alert_id': alert.get('alert_id'),
                'channels': {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Send to Slack
            slack_result = self.slack.send_alert(alert, channel='#security-alerts')
            results['channels']['slack'] = slack_result['status']

            # Send to Teams
            teams_result = self.teams.send_alert(alert)
            results['channels']['teams'] = teams_result['status']

            # Record in history
            self.notification_history.append({
                'alert_id': alert.get('alert_id'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'slack': slack_result['status'],
                'teams': teams_result['status']
            })

            logger.info(f"Sent alert {alert.get('alert_id')} to all channels")
            return results

        except Exception as e:
            logger.error(f"Failed to send to all channels: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def throttle_notifications(self, alerts: List[Dict], window_seconds: int = 60) -> List[Dict]:
        """
        Throttle notifications to prevent spam

        Args:
            alerts: List of alerts to send
            window_seconds: Time window for deduplication

        Returns:
            Filtered alerts after throttling
        """
        try:
            throttled = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)

            for alert in alerts:
                alert_key = alert.get('threatType', 'unknown')

                # Check if we've sent a similar alert recently
                if alert_key in self.throttle_cache:
                    last_time = self.throttle_cache[alert_key]
                    if last_time > cutoff_time:
                        logger.debug(f"Throttled alert {alert_key} (duplicate within {window_seconds}s)")
                        continue

                # Not throttled, add to output
                throttled.append(alert)
                self.throttle_cache[alert_key] = datetime.now(timezone.utc)

            logger.info(f"Throttled {len(alerts)} alerts to {len(throttled)} (window: {window_seconds}s)")
            return throttled

        except Exception as e:
            logger.error(f"Failed to throttle notifications: {str(e)}")
            return alerts

    def track_notification_delivery(self, notification: Dict) -> Dict:
        """
        Track notification delivery status

        Args:
            notification: Notification with delivery info

        Returns:
            Delivery tracking record
        """
        try:
            tracking = {
                'notification_id': notification.get('alert_id'),
                'channels_contacted': 0,
                'channels_success': 0,
                'channels_failed': 0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'delivery_status': {}
            }

            # Count channel results
            channels = ['slack', 'teams']
            for channel in channels:
                status = notification.get(f'{channel}_status', 'unknown')
                tracking['channels_contacted'] += 1

                if status == 'sent':
                    tracking['channels_success'] += 1
                    tracking['delivery_status'][channel] = 'success'
                else:
                    tracking['channels_failed'] += 1
                    tracking['delivery_status'][channel] = 'failed'

            # Overall status
            if tracking['channels_failed'] == 0:
                tracking['overall_status'] = 'success'
            elif tracking['channels_success'] > 0:
                tracking['overall_status'] = 'partial'
            else:
                tracking['overall_status'] = 'failed'

            logger.info(f"Tracked notification {notification.get('alert_id')}: {tracking['overall_status']}")
            return tracking

        except Exception as e:
            logger.error(f"Failed to track delivery: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def get_notification_stats(self) -> Dict:
        """
        Get notification delivery statistics

        Returns:
            Statistics for recent notifications
        """
        try:
            if not self.notification_history:
                return {
                    'total_notifications': 0,
                    'successful': 0,
                    'failed': 0,
                    'success_rate': 0.0
                }

            total = len(self.notification_history)
            successful = sum(
                1 for n in self.notification_history
                if n.get('slack') == 'success' and n.get('teams') == 'success'
            )
            failed = sum(
                1 for n in self.notification_history
                if n.get('slack') == 'failed' and n.get('teams') == 'failed'
            )

            success_rate = (successful / total * 100) if total > 0 else 0.0

            return {
                'total_notifications': total,
                'successful': successful,
                'failed': failed,
                'partial': total - successful - failed,
                'success_rate': round(success_rate, 2)
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {'error': str(e), 'status': 'failed'}
