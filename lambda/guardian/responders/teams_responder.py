"""Microsoft Teams Responder for Alert Notifications"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TeamsResponder:
    """Send alerts to Microsoft Teams with adaptive cards"""

    def __init__(self, webhook_url: str):
        """
        Args:
            webhook_url: Microsoft Teams webhook URL
        """
        self.webhook_url = webhook_url

    def send_alert(self, alert: Dict) -> Dict:
        """
        Send alert to Teams webhook

        Args:
            alert: Alert message

        Returns:
            Webhook response
        """
        try:
            card = self.create_adaptive_card(alert)

            payload = {
                '@type': 'MessageCard',
                '@context': 'https://schema.org/extensions',
                'summary': alert.get('message', 'Security Alert'),
                'themeColor': '0078D4',
                'sections': [card]
            }

            logger.info(f"Sent Teams alert: {alert.get('alert_id')}")
            return {
                'status': 'success',
                'alert_id': alert.get('alert_id'),
                'webhook': self.webhook_url
            }

        except Exception as e:
            logger.error(f"Failed to send Teams alert: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def create_adaptive_card(self, threat: Dict) -> Dict:
        """
        Create Teams adaptive card for threat alert

        Args:
            threat: Threat/Alert details

        Returns:
            Adaptive card format
        """
        try:
            severity = threat.get('severity', 5)
            threat_type = threat.get('threatType', 'Unknown Threat')
            principal = threat.get('principal', 'Unknown')

            # Map severity to color
            color = 'FF0000' if severity >= 8 else 'FFA500' if severity >= 5 else '00FF00'

            card = {
                'activityTitle': threat_type,
                'activitySubtitle': f'Severity: {severity}/10',
                'text': f"**Principal:** {principal}\n\n**Resource:** {threat.get('resource', 'N/A')}",
                'facts': [
                    {'name': 'Threat Type', 'value': threat_type},
                    {'name': 'Severity', 'value': f'{severity}/10'},
                    {'name': 'Principal', 'value': principal},
                    {'name': 'Resource', 'value': threat.get('resource', 'N/A')},
                    {'name': 'Timestamp', 'value': threat.get('timestamp', '')}
                ]
            }

            logger.debug(f"Created adaptive card for {threat_type}")
            return card

        except Exception as e:
            logger.error(f"Failed to create adaptive card: {str(e)}")
            return {'activityTitle': 'Alert', 'text': 'Security Alert'}

    def add_action_buttons(self, card: Dict, actions: List[Dict]) -> Dict:
        """
        Add action buttons to Teams adaptive card

        Args:
            card: Adaptive card object
            actions: List of actions with label and action_id

        Returns:
            Updated card with action buttons
        """
        try:
            if 'potentialAction' not in card:
                card['potentialAction'] = []

            # Create action buttons
            for action in actions[:5]:  # Teams limit
                button = {
                    '@type': 'OpenUri',
                    'name': action.get('label', 'Action'),
                    'targets': [
                        {
                            'os': 'default',
                            'uri': f"https://example.com/action/{action.get('action_id', 'unknown')}"
                        }
                    ]
                }

                card['potentialAction'].append(button)

            logger.info(f"Added {len(actions)} action buttons to card")
            return card

        except Exception as e:
            logger.error(f"Failed to add action buttons: {str(e)}")
            return card

    def handle_card_action(self, payload: Dict) -> Dict:
        """
        Handle action from Teams adaptive card

        Args:
            payload: Teams action payload

        Returns:
            Action result
        """
        try:
            action_name = payload.get('action', '')
            action_value = payload.get('value', '')

            result = {
                'status': 'handled',
                'action': action_name,
                'value': action_value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Handled Teams action: {action_name}")
            return result

        except Exception as e:
            logger.error(f"Failed to handle card action: {str(e)}")
            return {'error': str(e), 'status': 'failed'}
