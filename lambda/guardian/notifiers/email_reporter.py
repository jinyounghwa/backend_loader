"""Email report generation."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class EmailReporter:
    """Generate and send email reports."""

    def __init__(self):
        """Initialize email reporter."""
        self.templates = {}

    def generate_daily_summary(
        self, alerts: List[Dict[str, Any]], recipient: str
    ) -> Dict[str, Any]:
        """Generate daily summary email.
        
        Args:
            alerts: List of daily alerts
            recipient: Email recipient
            
        Returns:
            Email payload
        """
        subject = f"AWS Guardian Daily Summary - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        
        body = self._generate_summary_body(alerts)
        
        return {
            'to': recipient,
            'subject': subject,
            'body': body,
            'alert_count': len(alerts),
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

    def _generate_summary_body(self, alerts: List[Dict[str, Any]]) -> str:
        """Generate email body.
        
        Args:
            alerts: List of alerts
            
        Returns:
            Email body HTML
        """
        by_severity = {}
        for alert in alerts:
            sev = alert.get('severity', 'UNKNOWN')
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        return f"""
<html>
<body>
<h2>AWS Guardian Daily Summary</h2>
<p>Total Alerts: {len(alerts)}</p>
<h3>By Severity:</h3>
<ul>
{''.join(f"<li>{k}: {v}</li>" for k, v in by_severity.items())}
</ul>
<p>Log in to your dashboard for full details.</p>
</body>
</html>
"""

    def generate_weekly_report(
        self, metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate weekly performance report.
        
        Args:
            metrics: Weekly metrics
            
        Returns:
            Email payload
        """
        return {
            'subject': 'AWS Guardian Weekly Report',
            'body': self._generate_weekly_body(metrics),
            'metrics': metrics,
        }

    def _generate_weekly_body(self, metrics: Dict[str, Any]) -> str:
        """Generate weekly report body.
        
        Args:
            metrics: Weekly metrics
            
        Returns:
            Email body
        """
        return f"""
Weekly Performance Report
Total Alerts: {metrics.get('total_alerts', 0)}
Cost Savings: ${metrics.get('cost_savings', 0):.2f}
Security Issues Fixed: {metrics.get('security_fixed', 0)}
"""
