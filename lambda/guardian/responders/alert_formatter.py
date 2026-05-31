"""Alert formatting utilities for AWS Guardian notifications.

Provides a unified AlertMessage model that both Telegram and Discord
responders use to render alerts, eliminating per-channel formatting duplication.
"""

import html
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def esc(value: Any) -> str:
    """Escape an untrusted value for safe embedding in Telegram HTML messages.

    Telegram's HTML parse mode treats ``<``, ``>`` and ``&`` as markup, so any
    dynamic value derived from AWS resources (bucket names, instance IDs, IAM
    usernames, source IPs, finding types, etc.) must be escaped before it is
    placed inside structural tags like ``<b>`` or ``<code>``. Without this an
    attacker who controls a resource name/tag could forge alert content or
    break message parsing so the alert is silently dropped.
    """
    return html.escape(str(value), quote=False)


SEVERITY_ICONS = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🔵",
    "INFO": "ℹ️",
}

EMOJI = {
    "cost": "💰",
    "ec2": "⚠️",
    "s3": "🔐",
    "cloudtrail": "🕵️",
    "iam": "👤",
    "guardduty": "🛡️",
    "success": "✅",
    "failed": "❌",
}


def severity_icon(severity: str) -> str:
    return SEVERITY_ICONS.get(severity, "ℹ️")


def check_emoji(check_name: str) -> str:
    return EMOJI.get(check_name, "🔍")


def format_account_info(account_id: str, account_name: Optional[str]) -> str:
    if account_id == "current" and not account_name:
        return ""
    label = esc(account_name or account_id)
    return f"{label} ({esc(account_id)})" if account_id != "current" else label


@dataclass
class AlertMessage:
    """Normalized alert data shared across all notification channels."""

    title: str
    severity: str
    check_name: str
    account_info: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    summary_line: str = ""
    suggested_action: Optional[str] = None

    @classmethod
    def from_cost_data(cls, data: Dict[str, Any], account_info: str = "") -> "AlertMessage":
        return cls(
            title="AWS Cost Alert",
            severity="HIGH",
            check_name="cost",
            account_info=account_info,
            items=[
                {
                    "Today Cost": f"${data.get('today_cost', 0):.2f}",
                    "Threshold": f"${data.get('threshold', 0):.2f}",
                    "Increase": f"{data.get('increase_percent', 0)}%",
                    "Date": esc(data.get("date", "N/A")),
                    "Yesterday": f"${data.get('yesterday_cost', 0):.2f}",
                    "Monthly": f"${data.get('monthly_cost', 0):.2f}",
                }
            ],
            summary_line="Cost threshold exceeded!",
            suggested_action="Review top-cost services and scale down",
        )

    @classmethod
    def from_ec2_data(cls, data: Dict[str, Any], account_info: str = "") -> "AlertMessage":
        items = []
        unauthorized = data.get("unauthorized_region_instances", {})
        if unauthorized:
            for region, instances in unauthorized.items():
                items.append(
                    {
                        "type": "unauthorized_region",
                        "label": f"🌍 Unauthorized Region: {esc(region)}",
                        "count": len(instances),
                        "details": [esc(inst.get("InstanceId", "?")) for inst in instances[:3]],
                    }
                )

        for exp in data.get("exposed_instances", []):
            items.append(
                {
                    "type": "exposed",
                    "label": f"🔓 {esc(exp['instance_id'])} ({esc(exp['region'])})",
                    "details": [
                        f"Port {esc(r.get('from_port', '?'))}/{esc(r.get('protocol', '?'))}"
                        for r in exp.get("exposed_rules", [])[:2]
                    ],
                }
            )

        for inst in data.get("new_instances", [])[:3]:
            items.append(
                {
                    "type": "new",
                    "label": f"🆕 {esc(inst['instance_id'])} ({esc(inst['region'])})",
                }
            )

        return cls(
            title="EC2 Security Alert",
            severity="CRITICAL" if data.get("exposed_instances") else "HIGH",
            check_name="ec2",
            account_info=account_info,
            items=items,
            summary_line="Automated response: Stopping exposed instances...",
            suggested_action="Review and authorize or stop instances",
        )

    @classmethod
    def from_s3_data(cls, data: Dict[str, Any], account_info: str = "") -> "AlertMessage":
        items = []
        for bucket in data.get("public_buckets", [])[:3]:
            items.append(
                {
                    "type": "public_bucket",
                    "label": f"🌐 {esc(bucket['bucket_name'])}",
                    "details": [esc(r) for r in bucket.get("public_reasons", [])],
                }
            )
        for bucket in data.get("new_buckets", [])[:3]:
            items.append(
                {
                    "type": "new_bucket",
                    "label": f"🆕 {esc(bucket['bucket_name'])}",
                }
            )
        return cls(
            title="S3 Security Alert",
            severity="CRITICAL" if data.get("public_buckets") else "MEDIUM",
            check_name="s3",
            account_info=account_info,
            items=items,
            summary_line="Automated response: Blocking public access...",
            suggested_action="Review bucket access policies",
        )

    @classmethod
    def from_generic(
        cls, check_name: str, data: Dict[str, Any], account_info: str = ""
    ) -> "AlertMessage":
        suggested = data.get("suggested_action")
        return cls(
            title=f"{esc(check_name.upper())} Alert",
            severity=data.get("severity", "INFO"),
            check_name=check_name,
            account_info=account_info,
            summary_line=esc(data.get("message", "")),
            suggested_action=esc(suggested) if suggested else None,
        )

    @classmethod
    def from_check_data(
        cls, check_name: str, data: Dict[str, Any], account_info: str = ""
    ) -> "AlertMessage":
        builders = {
            "cost": cls.from_cost_data,
            "ec2": cls.from_ec2_data,
            "s3": cls.from_s3_data,
        }
        builder = builders.get(check_name)
        if builder:
            return builder(data, account_info=account_info)
        return cls.from_generic(check_name, data, account_info=account_info)
