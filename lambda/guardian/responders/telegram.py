"""Telegram notification responder for AWS Guardian"""

import logging
import os
from typing import Any, Dict, Optional

import requests
from guardian.responders.alert_formatter import (
    EMOJI,
    AlertMessage,
    check_emoji,
    esc,
    format_account_info,
    severity_icon,
)

logger = logging.getLogger(__name__)


class TelegramResponder:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": message, "parse_mode": parse_mode},
                timeout=10,
                verify=True,
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
            if isinstance(item, dict) and "label" in item:
                parts.append(f"\n{item['label']}")
                for d in item.get("details", [])[:3]:
                    parts.append(f"  └ {d}")
            elif isinstance(item, dict):
                for k, v in item.items():
                    parts.append(f"{k}: {v}")

        if alert.summary_line:
            parts.append(f"\n━━━━━━━━━━━━━━━━━━━\n⚡ {alert.summary_line}")

        if alert.suggested_action:
            parts.append(f"\n💡 {alert.suggested_action}")

        parts.append("\n━━━━━━━━━━━━━━━━━━━")
        return "\n".join(parts)

    def send_alert(
        self,
        check_name: str,
        alert_data: Dict[str, Any],
        account_id: str = "current",
        account_name: Optional[str] = None,
    ) -> bool:
        account_info = format_account_info(account_id, account_name)

        if check_name in ("cost", "ec2", "s3"):
            alert = AlertMessage.from_check_data(check_name, alert_data, account_info=account_info)
            return self.send_message(self._render_alert(alert))

        builder = {
            "cloudtrail": self._render_cloudtrail_alert,
            "iam": self._render_iam_alert,
            "guardduty": self._render_guardduty_alert,
        }
        renderer = builder.get(check_name)
        if renderer:
            return self.send_message(renderer(alert_data, account_info))
        return self._send_generic_alert(check_name, alert_data, account_info=account_info)

    def _render_cloudtrail_alert(self, data: Dict[str, Any], account_info: str) -> str:
        anomalies = data.get("details", {}).get("anomalies", [])
        items = []
        for a in anomalies[:5]:
            items.append(
                {
                    "type": "anomaly",
                    "label": f"🔍 <b>{esc(a.get('event_name'))}</b>",
                    "details": [
                        f"👤 <code>{esc(a.get('username'))}</code>",
                        f"🌐 <code>{esc(a.get('source_ip'))}</code>",
                    ],
                }
            )

        suggested = data.get("suggested_action")
        alert = AlertMessage(
            title="CloudTrail: Suspicious API Calls",
            severity=data.get("severity", "MEDIUM"),
            check_name="cloudtrail",
            account_info=account_info,
            items=items,
            summary_line=f"Detected {len(anomalies)} suspicious events",
            suggested_action=esc(suggested) if suggested else None,
        )
        return self._render_alert(alert)

    def _render_iam_alert(self, data: Dict[str, Any], account_info: str) -> str:
        type_icons = {"NEW_USER": "👤", "DELETED_USER": "🚫", "NEW_ACCESS_KEY": "🔑"}
        changes = data.get("details", {}).get("changes", [])
        items = []
        for c in changes[:5]:
            icon = type_icons.get(c.get("type"), "⚙️")
            items.append(
                {
                    "type": "change",
                    "label": f"{icon} <b>{esc(c.get('type'))}</b>",
                    "details": [esc(c.get("detail", ""))],
                }
            )

        suggested = data.get("suggested_action")
        alert = AlertMessage(
            title="IAM: Permission Changes Detected",
            severity=data.get("severity", "MEDIUM"),
            check_name="iam",
            account_info=account_info,
            items=items,
            summary_line=f"{len(changes)} changes detected",
            suggested_action=esc(suggested) if suggested else None,
        )
        return self._render_alert(alert)

    def _render_guardduty_alert(self, data: Dict[str, Any], account_info: str) -> str:
        details = data.get("details", {})
        high = details.get("high_severity", [])
        med = details.get("medium_severity", [])
        items = []
        if high:
            items.append(
                {
                    "type": "high",
                    "label": f"🔴 High Severity ({len(high)})",
                    "details": [
                        f"<b>{esc(f.get('type'))}</b> → <code>{esc(f.get('resource_id', ''))}</code>"
                        for f in high[:3]
                    ],
                }
            )
        if med:
            items.append(
                {
                    "type": "medium",
                    "label": f"🟡 Medium Severity ({len(med)})",
                    "details": [f"<b>{esc(f.get('type'))}</b>" for f in med[:2]],
                }
            )

        suggested = data.get("suggested_action")
        alert = AlertMessage(
            title="GuardDuty: Threat Detected",
            severity=data.get("severity", "MEDIUM"),
            check_name="guardduty",
            account_info=account_info,
            items=items,
            summary_line=f"Total threats: {details.get('total', 0)}",
            suggested_action=esc(suggested) if suggested else None,
        )
        return self._render_alert(alert)

    def _send_generic_alert(
        self, check_name: str, alert_data: Dict[str, Any], account_info: str = ""
    ) -> bool:
        alert = AlertMessage.from_generic(check_name, alert_data, account_info=account_info)
        return self.send_message(self._render_alert(alert))

    def send_auto_response_notification(
        self,
        action_type: str,
        resource_id: str,
        status: str,
        region: Optional[str] = None,
        rule_id: Optional[str] = None,
        action_description: Optional[str] = None,
    ) -> bool:
        status_icon = EMOJI.get("success" if status == "success" else "failed", "❓")
        action_desc = action_description or {
            "stop_instance": "Stopped EC2 instance",
            "stop_ec2": "Stopped EC2 instance",
            "block_bucket": "Blocked S3 public access",
            "block_s3_public": "Blocked S3 public access",
        }.get(action_type, f"Executed {esc(action_type)}")

        msg = f"""
{status_icon} <b>Auto-Response Action Executed</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Action: {esc(action_desc)}
🎯 Resource: <code>{esc(resource_id)}</code>"""

        if region:
            msg += f"\n🌍 Region: <code>{esc(region)}</code>"

        if rule_id:
            msg += f"\n📜 Rule ID: <code>{esc(rule_id)}</code>"

        msg += f"""
📊 Status: <b>{esc(status.upper())}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        return self.send_message(msg)

    def send_summary(self, summary_data: Dict[str, Any]) -> bool:
        total = summary_data.get("total_events", 0)
        by_type = summary_data.get("by_type", {})
        by_severity = summary_data.get("by_severity", {})
        msg = f"\n📊 <b>AWS Guardian Daily Summary</b>\n━━━━━━━━━━━━━━━━━━━\n📈 Total Events: {total}\n\n<b>By Type:</b>"
        for t, c in by_type.items():
            msg += f"\n• {esc(t)}: {esc(c)}"
        msg += "\n\n<b>By Severity:</b>"
        for s, c in by_severity.items():
            si = "🔴" if s == "critical" else "🟡" if s == "warning" else "ℹ️"
            msg += f"\n{si} {esc(s)}: {esc(c)}"
        msg += "\n━━━━━━━━━━━━━━━━━━━"
        return self.send_message(msg)

    @staticmethod
    def _account_info(account_id: str, account_name: Optional[str]) -> str:
        return format_account_info(account_id, account_name)
