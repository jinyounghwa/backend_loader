"""Discord notification responder for AWS Guardian"""
import logging
import requests
from typing import Dict, Any, Optional

from guardian.responders.alert_formatter import AlertMessage, severity_icon, check_emoji

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    'CRITICAL': 16711680,   # Red
    'HIGH': 16744192,       # Orange
    'MEDIUM': 16776960,     # Yellow
    'LOW': 5814783,         # Blue
    'INFO': 65280,          # Green
}


class DiscordResponder:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or ''

    def send_embed(self, embed: Dict[str, Any]) -> bool:
        if not self.webhook_url:
            return False
        try:
            response = requests.post(
                self.webhook_url,
                json={'embeds': [embed]},
                timeout=10,
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error("Error sending Discord embed: %s", e)
            return False

    def _render_alert_embed(self, alert: AlertMessage) -> Dict[str, Any]:
        icon = check_emoji(alert.check_name)
        color = SEVERITY_COLORS.get(alert.severity, 5814783)
        fields = []

        for item in alert.items:
            if isinstance(item, dict) and 'label' in item:
                details = item.get('details', [])
                value = item['label']
                if details:
                    value += '\n' + '\n'.join(f"  └ {d}" for d in details[:3])
                fields.append({'name': item.get('type', 'Item'), 'value': value, 'inline': False})
            elif isinstance(item, dict):
                for k, v in item.items():
                    fields.append({'name': k, 'value': str(v), 'inline': True})

        return {
            'title': f'{icon} {alert.title}',
            'color': color,
            'fields': fields if fields else [{'name': 'Status', 'value': alert.summary_line or 'No details', 'inline': False}],
            'description': alert.summary_line or '',
            'footer': {'text': 'AWS Guardian'},
        }

    def send_cost_alert(self, cost_data: Dict[str, Any]) -> bool:
        alert = AlertMessage.from_cost_data(cost_data)
        return self.send_embed(self._render_alert_embed(alert))

    def send_ec2_alert(self, ec2_data: Dict[str, Any]) -> bool:
        alert = AlertMessage.from_ec2_data(ec2_data)
        return self.send_embed(self._render_alert_embed(alert))

    def send_s3_alert(self, s3_data: Dict[str, Any]) -> bool:
        alert = AlertMessage.from_s3_data(s3_data)
        return self.send_embed(self._render_alert_embed(alert))

    def send_status_embed(self, status_data: Dict[str, Any]) -> bool:
        fields = [
            {'name': '💰 Monthly Cost', 'value': f"${status_data.get('monthly_cost', 0):.2f}", 'inline': True},
            {'name': '🏃 Running EC2', 'value': str(status_data.get('running_instances', 0)), 'inline': True},
            {'name': '🪣 S3 Buckets', 'value': str(status_data.get('total_buckets', 0)), 'inline': True},
        ]
        return self.send_embed({
            'title': '📊 AWS Guardian Status',
            'color': 65280,
            'fields': fields,
            'footer': {'text': 'AWS Guardian'},
        })

    def send_summary_embed(self, summary_data: Dict[str, Any]) -> bool:
        total = summary_data.get('total_events', 0)
        by_type = summary_data.get('by_type', {})
        by_severity = summary_data.get('by_severity', {})
        fields = [
            {'name': 'Events by Type', 'value': '\n'.join(f"• {k}: {v}" for k, v in by_type.items()) or 'None', 'inline': False},
            {'name': 'Events by Severity', 'value': '\n'.join(f"• {k}: {v}" for k, v in by_severity.items()) or 'None', 'inline': False},
        ]
        return self.send_embed({
            'title': '📊 AWS Guardian Daily Summary',
            'color': 5814783,
            'description': f'Total Events: {total}',
            'fields': fields,
            'footer': {'text': 'AWS Guardian'},
        })
