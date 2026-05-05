"""Telegram notification responder for AWS Guardian"""
import logging
import os
import requests
from typing import Dict, Any, Optional

from guardian.responders.alert_formatter import (
    AlertMessage, severity_icon, check_emoji, EMOJI,
)

logger = logging.getLogger(__name__)


class TelegramResponder:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID', '')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={'chat_id': self.chat_id, 'text': message, 'parse_mode': parse_mode},
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("Error sending Telegram message: %s", e)
            return False

    def _render_alert(self, alert: AlertMessage) -> str:
        icon = check_emoji(alert.check_name)
        sev_icon = severity_icon(alert.severity)
        parts = [f"{sev_icon} <b>{icon} {alert.title}</b>"]
        if alert.account_info:
            parts.append(f"🏢 {alert.account_info}")
        parts.append("━━━━━━━━━━━━━━━━━━━")

        for item in alert.items:
            if isinstance(item, dict) and 'label' in item:
                parts.append(f"\n{item['label']}")
                for d in item.get('details', [])[:3]:
                    parts.append(f"  └ {d}")
            elif isinstance(item, dict):
                for k, v in item.items():
                    parts.append(f"{k}: {v}")

        if alert.summary_line:
            parts.append(f"\n━━━━━━━━━━━━━━━━━━━\n⚡ {alert.summary_line}")

        if alert.suggested_action:
            parts.append(f"\n💡 {alert.suggested_action}")

        parts.append("\n━━━━━━━━━━━━━━━━━━━")
        return '\n'.join(parts)

    def send_cost_alert(self, cost_data: Dict[str, Any], account_id: str = 'current',
                        account_name: Optional[str] = None) -> bool:
        alert = AlertMessage.from_cost_data(cost_data, account_info=self._account_info(account_id, account_name))
        return self.send_message(self._render_alert(alert))

    def send_ec2_alert(self, ec2_data: Dict[str, Any], account_id: str = 'current',
                       account_name: Optional[str] = None) -> bool:
        alert = AlertMessage.from_ec2_data(ec2_data, account_info=self._account_info(account_id, account_name))
        return self.send_message(self._render_alert(alert))

    def send_s3_alert(self, s3_data: Dict[str, Any], account_id: str = 'current',
                      account_name: Optional[str] = None) -> bool:
        alert = AlertMessage.from_s3_data(s3_data, account_info=self._account_info(account_id, account_name))
        return self.send_message(self._render_alert(alert))

    def send_cloudtrail_alert(self, cloudtrail_data: Dict[str, Any], account_id: str = 'current',
                              account_name: Optional[str] = None) -> bool:
        sev = cloudtrail_data.get('severity', 'MEDIUM')
        icon = severity_icon(sev)
        acct = self._account_info(account_id, account_name)
        anomalies = cloudtrail_data.get('details', {}).get('anomalies', [])
        msg = f"{icon} <b>CloudTrail: Suspicious API Calls</b> 🏢 {acct}\n━━━━━━━━━━━━━━━━━━━━━━━━"
        msg += f"\n📍 Severity: <b>{sev}</b>"
        if anomalies:
            msg += f"\n🔍 <b>Detected Events ({len(anomalies)}):</b>"
            for a in anomalies[:5]:
                msg += f"\n• <b>{a.get('event_name')}</b>"
                msg += f"\n  👤 <code>{a.get('username')}</code> 🌐 <code>{a.get('source_ip')}</code>"
        suggestion = cloudtrail_data.get('suggested_action')
        if suggestion:
            msg += f"\n\n💡 <b>Suggested Action:</b>\n{suggestion}"
        msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"
        return self.send_message(msg)

    def send_iam_alert(self, iam_data: Dict[str, Any], account_id: str = 'current',
                       account_name: Optional[str] = None) -> bool:
        sev = iam_data.get('severity', 'MEDIUM')
        icon = severity_icon(sev)
        acct = self._account_info(account_id, account_name)
        changes = iam_data.get('details', {}).get('changes', [])
        type_icons = {'NEW_USER': '👤', 'DELETED_USER': '🚫', 'NEW_ACCESS_KEY': '🔑'}
        msg = f"{icon} <b>IAM: Permission Changes Detected</b> 🏢 {acct}\n━━━━━━━━━━━━━━━━━━━━━━━━"
        msg += f"\n📍 Severity: <b>{sev}</b>"
        if changes:
            msg += f"\n🔐 <b>Changes ({len(changes)}):</b>"
            for c in changes[:5]:
                msg += f"\n{type_icons.get(c.get('type'), '⚙️')} <b>{c.get('type')}</b>"
                msg += f"\n  📝 {c.get('detail')}"
        suggestion = iam_data.get('suggested_action')
        if suggestion:
            msg += f"\n\n💡 <b>Suggested Action:</b>\n{suggestion}"
        msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"
        return self.send_message(msg)

    def send_guardduty_alert(self, guardduty_data: Dict[str, Any], account_id: str = 'current',
                            account_name: Optional[str] = None) -> bool:
        sev = guardduty_data.get('severity', 'MEDIUM')
        icon = severity_icon(sev)
        acct = self._account_info(account_id, account_name)
        details = guardduty_data.get('details', {})
        high = details.get('high_severity', [])
        med = details.get('medium_severity', [])
        msg = f"{icon} <b>GuardDuty: Threat Detected</b> 🏢 {acct}\n━━━━━━━━━━━━━━━━━━━━━━━━"
        msg += f"\n🛡️  Severity: <b>{sev}</b>"
        if high:
            msg += f"\n\n🔴 <b>High ({len(high)}):</b>"
            for f in high[:3]:
                msg += f"\n• <b>{f.get('type')}</b> → <code>{f.get('resource_id', '')}</code>"
        if med:
            msg += f"\n\n🟡 <b>Medium ({len(med)}):</b>"
            for f in med[:2]:
                msg += f"\n• <b>{f.get('type')}</b>"
        suggestion = guardduty_data.get('suggested_action')
        if suggestion:
            msg += f"\n\n💡 <b>Remediation:</b>\n{suggestion}"
        msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"
        return self.send_message(msg)

    def send_alert(self, check_name: str, alert_data: Dict[str, Any],
                   account_id: str = 'current', account_name: Optional[str] = None) -> bool:
        dispatch = {
            'cost': self.send_cost_alert,
            'ec2': self.send_ec2_alert,
            's3': self.send_s3_alert,
            'cloudtrail': self.send_cloudtrail_alert,
            'iam': self.send_iam_alert,
            'guardduty': self.send_guardduty_alert,
        }
        handler = dispatch.get(check_name)
        if handler:
            return handler(alert_data, account_id=account_id, account_name=account_name)
        return self._send_generic_alert(check_name, alert_data, account_id=account_id, account_name=account_name)

    def _send_generic_alert(self, check_name: str, alert_data: Dict[str, Any],
                           account_id: str = 'current', account_name: Optional[str] = None) -> bool:
        sev = alert_data.get('severity', 'INFO')
        icon = severity_icon(sev)
        acct = self._account_info(account_id, account_name)
        msg = f"{icon} <b>{check_name.upper()} Alert</b>\n━━━━━━━━━━━━━━━━━━━"
        msg += f"\n🏢 {acct}\n📍 Severity: {sev}\n📝 {alert_data.get('message', '')}"
        if alert_data.get('suggested_action'):
            msg += f"\n💡 {alert_data['suggested_action']}"
        msg += "\n━━━━━━━━━━━━━━━━━━━"
        return self.send_message(msg)

    def send_auto_response_notification(
        self,
        action_type: str,
        resource_id: str,
        status: str,
        region: Optional[str] = None,
        rule_id: Optional[str] = None,
        action_description: Optional[str] = None,
    ) -> bool:
        status_icon = EMOJI.get('success' if status == 'success' else 'failed', '❓')
        action_desc = action_description or {
            'stop_instance': 'Stopped EC2 instance',
            'stop_ec2': 'Stopped EC2 instance',
            'block_bucket': 'Blocked S3 public access',
            'block_s3_public': 'Blocked S3 public access',
        }.get(action_type, f'Executed {action_type}')

        msg = f"""
{status_icon} <b>Auto-Response Action Executed</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Action: {action_desc}
🎯 Resource: <code>{resource_id}</code>"""

        if region:
            msg += f"\n🌍 Region: <code>{region}</code>"

        if rule_id:
            msg += f"\n📜 Rule ID: <code>{rule_id}</code>"

        msg += f"""
📊 Status: <b>{status.upper()}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        return self.send_message(msg)

    def send_summary(self, summary_data: Dict[str, Any]) -> bool:
        total = summary_data.get('total_events', 0)
        by_type = summary_data.get('by_type', {})
        by_severity = summary_data.get('by_severity', {})
        msg = f"\n📊 <b>AWS Guardian Daily Summary</b>\n━━━━━━━━━━━━━━━━━━━\n📈 Total Events: {total}\n\n<b>By Type:</b>"
        for t, c in by_type.items():
            msg += f"\n• {t}: {c}"
        msg += "\n\n<b>By Severity:</b>"
        for s, c in by_severity.items():
            si = "🔴" if s == "critical" else "🟡" if s == "warning" else "ℹ️"
            msg += f"\n{si} {s}: {c}"
        msg += "\n━━━━━━━━━━━━━━━━━━━"
        return self.send_message(msg)

    @staticmethod
    def _account_info(account_id: str, account_name: Optional[str]) -> str:
        if account_id == 'current' and not account_name:
            return ''
        label = account_name or account_id
        return f"{label} ({account_id})" if account_id != 'current' else label
