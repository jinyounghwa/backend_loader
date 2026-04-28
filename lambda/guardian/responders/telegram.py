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
        today_cost = cost_data.get('today_cost', 0)
        threshold = cost_data.get('threshold', 0)
        increase_percent = cost_data.get('increase_percent', 0)

        message = f"""
🚨 <b>AWS Cost Alert</b>
━━━━━━━━━━━━━━━━━━━━
💰 Today's Cost: ${today_cost:.2f}
⚠️ Threshold: ${threshold:.2f}
📈 Increase: {increase_percent}%
📅 Date: {cost_data.get('date', 'N/A')}
━━━━━━━━━━━━━━━━━━━━
<i>비용 임계값 초과!</i>

💬 <b>답장으로 자동 수정:</b>
👉 <code>요금과다 원인수정</code>
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

        if ec2_data.get('anomalies'):
            message += "\n\n💬 <b>답장으로 자동 수정:</b>"
            message += "\n👉 <code>해킹우려 수정</code>"

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

        if s3_data.get('anomalies'):
            message += "\n\n💬 <b>답장으로 자동 수정:</b>"
            message += "\n👉 <code>해킹우려 수정</code>"

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

    def send_cloudtrail_alert(self, cloudtrail_data: Dict[str, Any]) -> bool:
        """Send CloudTrail suspicious API alert (Sprint 6)"""
        severity = cloudtrail_data.get('severity', 'MEDIUM')
        severity_icon = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'

        message = f"""{severity_icon} <b>CloudTrail: Suspicious API Calls</b>
━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Severity: <b>{severity}</b>
"""
        anomalies = cloudtrail_data.get('details', {}).get('anomalies', [])
        if anomalies:
            message += f"\n🔍 <b>Detected Events ({len(anomalies)}):</b>"
            for anomaly in anomalies[:5]:  # Show first 5
                message += f"\n• <b>{anomaly.get('event_name')}</b>"
                message += f"\n  👤 User: <code>{anomaly.get('username')}</code>"
                message += f"\n  🌐 IP: <code>{anomaly.get('source_ip')}</code>"
                message += f"\n  ⏰ Time: {anomaly.get('timestamp', 'N/A')}"

        suggestion = cloudtrail_data.get('suggested_action')
        if suggestion:
            message += f"\n\n💡 <b>Suggested Action:</b>\n{suggestion}"

        message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"

        return self.send_message(message)

    def send_iam_alert(self, iam_data: Dict[str, Any]) -> bool:
        """Send IAM permission changes alert (Sprint 6)"""
        severity = iam_data.get('severity', 'MEDIUM')
        severity_icon = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'

        message = f"""{severity_icon} <b>IAM: Permission Changes Detected</b>
━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Severity: <b>{severity}</b>
"""
        changes = iam_data.get('details', {}).get('changes', [])
        if changes:
            message += f"\n🔐 <b>Changes ({len(changes)}):</b>"
            for change in changes[:5]:  # Show first 5
                change_type = change.get('type', 'UNKNOWN')
                icons = {
                    'NEW_USER': '👤',
                    'DELETED_USER': '🚫',
                    'NEW_ACCESS_KEY': '🔑'
                }
                icon = icons.get(change_type, '⚙️')
                message += f"\n{icon} <b>{change_type}</b>"
                message += f"\n  📝 {change.get('detail')}"

        suggestion = iam_data.get('suggested_action')
        if suggestion:
            message += f"\n\n💡 <b>Suggested Action:</b>\n{suggestion}"

        message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"

        return self.send_message(message)

    def send_guardduty_alert(self, guardduty_data: Dict[str, Any]) -> bool:
        """Send GuardDuty threat detection alert (Sprint 6)"""
        severity = guardduty_data.get('severity', 'MEDIUM')
        severity_icon = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'

        message = f"""{severity_icon} <b>GuardDuty: Threat Detected</b>
━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️  Severity: <b>{severity}</b>
"""
        details = guardduty_data.get('details', {})
        high_findings = details.get('high_severity', [])
        med_findings = details.get('medium_severity', [])

        if high_findings:
            message += f"\n\n🔴 <b>High-Severity Threats ({len(high_findings)}):</b>"
            for finding in high_findings[:3]:  # Show first 3
                message += f"\n• <b>{finding.get('type', 'Unknown')}</b>"
                if finding.get('resource_id'):
                    message += f"\n  🎯 Resource: <code>{finding.get('resource_id')}</code>"
                message += f"\n  📋 {finding.get('title', 'No title')}"

        if med_findings:
            message += f"\n\n🟡 <b>Medium-Severity Threats ({len(med_findings)}):</b>"
            for finding in med_findings[:2]:  # Show first 2
                message += f"\n• <b>{finding.get('type', 'Unknown')}</b>"

        suggestion = guardduty_data.get('suggested_action')
        if suggestion:
            message += f"\n\n💡 <b>Remediation:</b>\n{suggestion}"

        message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"

        return self.send_message(message)

    def send_alert(self, check_name: str, alert_data: Dict[str, Any]) -> bool:
        """
        Generic alert handler for all check types.
        Dispatches to specific alert method based on check_name.
        """
        alert_methods = {
            'cloudtrail': self.send_cloudtrail_alert,
            'iam': self.send_iam_alert,
            'guardduty': self.send_guardduty_alert,
            'cost': self.send_cost_alert,
            'ec2': self.send_ec2_alert,
            's3': self.send_s3_alert,
        }

        handler = alert_methods.get(check_name)
        if handler:
            return handler(alert_data)
        else:
            # Fallback generic alert
            return self._send_generic_alert(check_name, alert_data)

    def _send_generic_alert(self, check_name: str, alert_data: Dict[str, Any]) -> bool:
        """Fallback generic alert for unknown check types"""
        severity = alert_data.get('severity', 'INFO')
        severity_icon = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡' if severity == 'MEDIUM' else 'ℹ️'

        message = f"""{severity_icon} <b>{check_name.upper()} Alert</b>
━━━━━━━━━━━━━━━━━━━
📍 Severity: {severity}
📝 Message: {alert_data.get('message', 'No details')}
"""
        if alert_data.get('suggested_action'):
            message += f"\n💡 Action: {alert_data.get('suggested_action')}"

        message += "\n━━━━━━━━━━━━━━━━━━━"

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
