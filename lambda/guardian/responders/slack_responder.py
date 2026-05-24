"""Slack Bot Responder for Alert Notifications"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SlackResponder:
    """Send alerts to Slack channels with interactive buttons"""

    def __init__(self, slack_client):
        """
        Args:
            slack_client: Slack Bot API client (from slack_sdk)
        """
        self.client = slack_client

    def send_alert(self, alert: Dict, channel: str = '#security-alerts') -> Dict:
        """
        Send alert to Slack channel

        Args:
            alert: Alert message
            channel: Target Slack channel

        Returns:
            Slack API response
        """
        try:
            block = self.create_alert_block(alert)

            response = self.client.chat_postMessage(
                channel=channel,
                blocks=[block],
                text=alert.get('message', 'Security Alert')
            )

            logger.info(f"Sent Slack alert to {channel}: {alert.get('alert_id')}")
            return {
                'status': 'success',
                'channel': channel,
                'alert_id': alert.get('alert_id'),
                'ts': response.get('ts')
            }

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def create_alert_block(self, threat: Dict) -> Dict:
        """
        Create Slack message block for threat alert

        Args:
            threat: Threat/Alert details

        Returns:
            Slack block format
        """
        try:
            severity = threat.get('severity', 5)
            threat_type = threat.get('threatType', 'Unknown Threat')
            principal = threat.get('principal', 'Unknown')

            # Map severity to color
            color = '#FF0000' if severity >= 8 else '#FFA500' if severity >= 5 else '#00FF00'

            block = {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*{threat_type}*\n"
                           f"Severity: {severity}/10\n"
                           f"Principal: `{principal}`\n"
                           f"Resource: `{threat.get('resource', 'N/A')}`"
                },
                'accessory': {
                    'type': 'button',
                    'text': {
                        'type': 'plain_text',
                        'text': 'View Details'
                    },
                    'value': threat.get('eventId', 'unknown'),
                    'action_id': 'view_details'
                }
            }

            logger.debug(f"Created alert block for {threat_type}")
            return block

        except Exception as e:
            logger.error(f"Failed to create alert block: {str(e)}")
            return {'type': 'section', 'text': {'type': 'mrkdwn', 'text': 'Alert'}}

    def add_buttons(self, message: Dict, actions: List[Dict]) -> Dict:
        """
        Add action buttons to Slack message

        Args:
            message: Slack message object
            actions: List of actions with label and action_id

        Returns:
            Updated message with buttons
        """
        try:
            if 'blocks' not in message:
                message['blocks'] = []

            # Create button block
            button_elements = []
            for action in actions[:5]:  # Slack limits to 5 buttons
                button_elements.append({
                    'type': 'button',
                    'text': {
                        'type': 'plain_text',
                        'text': action.get('label', 'Action')
                    },
                    'action_id': action.get('action_id', 'unknown'),
                    'value': action.get('value', 'action')
                })

            actions_block = {
                'type': 'actions',
                'elements': button_elements
            }

            message['blocks'].append(actions_block)

            logger.info(f"Added {len(button_elements)} buttons to message")
            return message

        except Exception as e:
            logger.error(f"Failed to add buttons: {str(e)}")
            return message

    def handle_interactive_action(self, payload: Dict) -> Dict:
        """
        Handle interactive button/action from Slack

        Args:
            payload: Slack interaction payload

        Returns:
            Action result
        """
        try:
            action_id = payload.get('actions', [{}])[0].get('action_id', '')
            value = payload.get('actions', [{}])[0].get('value', '')

            result = {
                'status': 'handled',
                'action_id': action_id,
                'value': value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Handled Slack action: {action_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to handle interaction: {str(e)}")
            return {'error': str(e), 'status': 'failed'}
