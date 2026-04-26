"""Telegram notification responder for AWS Guardian"""
import requests
import os
from typing import Dict, Any, List

class TelegramResponder:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram responder

        Args:
            bot_token: Telegram Bot API token
            chat_id: Target chat ID for notifications
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Send a message to Telegram"""
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': parse_mode
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False

    def send_cost_alert(self, cost_data: Dict[str, Any]) -> bool:
        """Send cost anomaly alert"""
        today_cost = cost_data.get('today_cost', 0)
        threshold = cost_data.get('threshold', 0)
        increase_percent = cost_data.get('increase_percent', 0)

        message = f"""
🚨 <b>AWS Cost Alert</b>
━━━━━━━━━━━━━━━━━━━
💰 Today's Cost: ${today_cost:.2f}
⚠️ Threshold: ${threshold:.2f}
📈 Increase: {increase_percent}%
📅 Date: {cost_data.get('date', 'N/A')}
━━━━━━━━━━━━━━━━━━━
<i>Threshold exceeded! Check your AWS account immediately.</i>
"""
        return self.send_message(message)

    def send_ec2_alert(self, ec2_data: Dict[str, Any]) -> bool:
        """Send EC2 security alert"""
        message = "<b>⚠️ EC2 Security Alert</b>\n━━━━━━━━━━━━━━━━━━━"

        # Unauthorized regions
        unauthorized = ec2_data.get('unauthorized_region_instances', {})
        if unauthorized:
            message += f"\n\n🌍 <b>Unauthorized Region Instances:</b>"
            for region, instances in unauthorized.items():
                message += f"\n• Region: {region} ({len(instances)} instances)"
                for inst in instances:
                    message += f"\n  - ID: <code>{inst['InstanceId']}</code>"

        # Exposed instances
        exposed = ec2_data.get('exposed_instances', [])
        if exposed:
            message += f"\n\n🔓 <b>Exposed to 0.0.0.0/0:</b>"
            for exp in exposed:
                message += f"\n• Instance: <code>{exp['instance_id']}</code> ({exp['region']})"
                for rule in exp['exposed_rules'][:2]:  # Show first 2 rules
                    message += f"\n  - Port {rule['from_port']}/{rule['protocol']}"

        # New instances
        new = ec2_data.get('new_instances', [])
        if new:
            message += f"\n\n🆕 <b>New Instances ({len(new)}):</b>"
            for inst in new[:3]:  # Show first 3
                message += f"\n• {inst['instance_id']} ({inst['region']})"

        message += "\n━━━━━━━━━━━━━━━━━━━\n⚡ Automated response: Stopping instances..."

        return self.send_message(message)

    def send_s3_alert(self, s3_data: Dict[str, Any]) -> bool:
        """Send S3 security alert"""
        message = "<b>🔐 S3 Security Alert</b>\n━━━━━━━━━━━━━━━━━━━"

        # Public buckets
        public = s3_data.get('public_buckets', [])
        if public:
            message += f"\n\n🌐 <b>Public Buckets Detected ({len(public)}):</b>"
            for bucket in public[:3]:  # Show first 3
                message += f"\n• <code>{bucket['bucket_name']}</code>"
                for reason in bucket['public_reasons']:
                    message += f"\n  └ {reason}"

        # New buckets
        new = s3_data.get('new_buckets', [])
        if new:
            message += f"\n\n🆕 <b>New Buckets ({len(new)}):</b>"
            for bucket in new[:3]:  # Show first 3
                message += f"\n• <code>{bucket['bucket_name']}</code>"

        message += "\n━━━━━━━━━━━━━━━━━━━\n⚡ Automated response: Blocking public access..."

        return self.send_message(message)

    def send_auto_response_notification(self, action_type: str, resource_id: str, status: str) -> bool:
        """Send auto-response action notification"""
        status_emoji = "✅" if status == "success" else "❌"
        action_desc = {
            'stop_ec2': 'Stopped EC2 instance',
            'block_s3_public': 'Blocked S3 public access'
        }.get(action_type, f'Executed {action_type}')

        message = f"""
{status_emoji} <b>Auto-Response Action</b>
━━━━━━━━━━━━━━━━━━━
📋 Action: {action_desc}
🎯 Resource: <code>{resource_id}</code>
📊 Status: {status}
━━━━━━━━━━━━━━━━━━━
"""
        return self.send_message(message)

    def send_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Send daily summary"""
        total = summary_data.get('total_events', 0)
        by_type = summary_data.get('by_type', {})
        by_severity = summary_data.get('by_severity', {})

        message = f"""
📊 <b>AWS Guardian Daily Summary</b>
━━━━━━━━━━━━━━━━━━━
📈 Total Events: {total}

<b>By Type:</b>
"""
        for event_type, count in by_type.items():
            message += f"\n• {event_type}: {count}"

        message += f"\n\n<b>By Severity:</b>"
        for severity, count in by_severity.items():
            icon = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "ℹ️"
            message += f"\n{icon} {severity}: {count}"

        message += "\n━━━━━━━━━━━━━━━━━━━"

        return self.send_message(message)
