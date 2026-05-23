"""Alert Handler for Sprint 33 Phase 3

Converts detected threats to alerts and sends them via Telegram/Discord.
Uses NotificationBuffer for batching and AlertHistory for audit trail.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError


class AlertHandler:
    """Converts threats to alerts and sends notifications"""

    def __init__(
        self,
        telegram_responder,
        discord_responder,
        notification_buffer,
        alert_history_table: Optional[str] = None,
    ):
        self.telegram = telegram_responder
        self.discord = discord_responder
        self.buffer = notification_buffer
        self.alert_history_table_name = alert_history_table
        self.dynamodb = boto3.resource("dynamodb") if alert_history_table else None

    async def process_threats(self, threats: List[Any]) -> int:
        """
        Convert threats to alerts and add to notification buffer.
        Args:
            threats: List of Threat objects
        Returns:
            Number of alerts processed
        """
        processed_count = 0

        for threat in threats:
            try:
                alert = self._threat_to_alert(threat)
                await self.buffer.add(alert)
                processed_count += 1
            except Exception as e:
                print(f"Error processing threat {threat.threat_id}: {e}")

        return processed_count

    async def flush_alerts(self) -> int:
        """
        Flush buffered alerts to Telegram and Discord.
        Returns:
            Number of alerts sent
        """
        try:
            alerts = await self.buffer.flush()
            sent_count = 0

            for alert in alerts:
                try:
                    # Send to both channels in parallel
                    results = await asyncio.gather(
                        self.telegram.send_alert(alert),
                        self.discord.send_alert(alert),
                        return_exceptions=True,
                    )

                    # Check for errors
                    errors = [r for r in results if isinstance(r, Exception)]
                    if not errors:
                        sent_count += 1

                    # Save to alert history
                    await self._save_alert_history(
                        alert, success=(len(errors) == 0)
                    )

                except Exception as e:
                    print(f"Error sending alert {alert.get('alert_id')}: {e}")
                    await self._save_alert_history(alert, success=False)

            return sent_count

        except Exception as e:
            print(f"Error flushing alerts: {e}")
            return 0

    def _threat_to_alert(self, threat: Any) -> Dict[str, Any]:
        """Convert a Threat object to alert message format"""
        severity_emoji = self._get_severity_emoji(threat.severity)
        severity_color = self._get_severity_color(threat.severity)

        alert = {
            "alert_id": threat.threat_id,
            "rule_id": threat.rule_id,
            "severity": threat.severity,
            "account_id": threat.account_id,
            "timestamp": threat.timestamp.isoformat(),
            "title": f"{severity_emoji} [{threat.account_id}] {threat.message}",
            "message": threat.message,
            "color": severity_color,
            "evidence_count": len(threat.evidence),
            "evidence": threat.evidence[:3],  # Top 3 for evidence
        }

        return alert

    def _get_severity_emoji(self, severity: int) -> str:
        """Get emoji based on threat severity (1-10)"""
        if severity >= 9:
            return "🚨"  # Critical
        elif severity >= 7:
            return "⚠️"  # High
        elif severity >= 5:
            return "⚡"  # Medium
        else:
            return "ℹ️"  # Low

    def _get_severity_color(self, severity: int) -> str:
        """Get color code for severity (Discord embed color)"""
        if severity >= 9:
            return "#FF0000"  # Red
        elif severity >= 7:
            return "#FF6600"  # Orange
        elif severity >= 5:
            return "#FFFF00"  # Yellow
        else:
            return "#00FF00"  # Green

    async def _save_alert_history(
        self, alert: Dict[str, Any], success: bool = True
    ) -> bool:
        """Save alert to DynamoDB for audit trail"""
        if not self.alert_history_table_name or not self.dynamodb:
            return False

        try:
            table = self.dynamodb.Table(self.alert_history_table_name)

            item = {
                "alert_id": alert.get("alert_id"),
                "rule_id": alert.get("rule_id"),
                "severity": alert.get("severity"),
                "account_id": alert.get("account_id") or "unknown",
                "timestamp": alert.get("timestamp"),
                "message": alert.get("message"),
                "status": "sent" if success else "failed",
                "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }

            table.put_item(Item=item)
            return True

        except ClientError as e:
            print(f"Error saving alert history: {e}")
            return False


class AlertFormatter:
    """Formats threats for display"""

    @staticmethod
    def format_telegram_message(alert: Dict[str, Any]) -> str:
        """Format alert for Telegram"""
        return f"""
{alert.get('title')}

Rule: {alert.get('rule_id')}
Severity: {alert.get('severity')}/10
Account: {alert.get('account_id')}
Evidence: {alert.get('evidence_count')} events

{alert.get('message')}
"""

    @staticmethod
    def format_discord_embed(alert: Dict[str, Any]) -> Dict[str, Any]:
        """Format alert as Discord embed"""
        return {
            "title": alert.get("title"),
            "description": alert.get("message"),
            "color": int(alert.get("color", "#FF0000").lstrip("#"), 16),
            "fields": [
                {
                    "name": "Rule ID",
                    "value": alert.get("rule_id"),
                    "inline": True,
                },
                {
                    "name": "Severity",
                    "value": f"{alert.get('severity')}/10",
                    "inline": True,
                },
                {
                    "name": "Account",
                    "value": alert.get("account_id"),
                    "inline": True,
                },
                {
                    "name": "Evidence",
                    "value": f"{alert.get('evidence_count')} events",
                    "inline": True,
                },
            ],
            "timestamp": alert.get("timestamp"),
        }
