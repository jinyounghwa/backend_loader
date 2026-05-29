"""Report Generator - Daily, weekly, and monthly remediation reports."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum


class ReportType(Enum):
    """Report types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportGenerator:
    """Generate compliance and analytics reports."""

    def __init__(self, audit_logger):
        """Initialize report generator."""
        self.audit = audit_logger

    def generate_daily_report(self, remediation_history: List[Dict], date: str = None) -> Dict:
        """
        Generate daily remediation summary report.

        Args:
            remediation_history: List of remediation records
            date: Report date (YYYY-MM-DD), defaults to today

        Returns:
            {
                'report_type': 'daily',
                'date': str,
                'total_threats_detected': int,
                'total_threats_remediated': int,
                'remediation_success_rate': float,
                'threats_by_severity': {
                    'critical': int,
                    'high': int,
                    'medium': int,
                    'low': int
                },
                'remediation_actions': {
                    'ec2_stop': int,
                    'ec2_terminate': int,
                    'iam_revoke': int,
                    'network_isolate': int,
                    's3_block_public': int
                },
                'average_remediation_time_seconds': float,
                'cost_impact': {
                    'estimated_prevented_cost': float,
                    'remediation_cost': float,
                    'net_savings': float
                },
                'top_threats': [
                    {
                        'threat_type': str,
                        'count': int,
                        'average_severity': float
                    }
                ],
                'summary': str
            }
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # Filter records for the specified date
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        daily_records = [
            r for r in remediation_history
            if datetime.fromisoformat(r.get('timestamp', '')).date() == target_date
        ]

        # Count metrics
        total_detected = len(daily_records)
        total_remediated = sum(1 for r in daily_records if r.get('status') == 'success')
        success_rate = total_remediated / total_detected if total_detected > 0 else 0.0

        # Count by severity
        severity_counts = {
            'critical': sum(1 for r in daily_records if r.get('severity', 0) >= 9),
            'high': sum(1 for r in daily_records if 7 <= r.get('severity', 0) < 9),
            'medium': sum(1 for r in daily_records if 5 <= r.get('severity', 0) < 7),
            'low': sum(1 for r in daily_records if r.get('severity', 0) < 5)
        }

        # Count remediation actions
        action_counts = {
            'ec2_stop': 0,
            'ec2_terminate': 0,
            'iam_revoke': 0,
            'network_isolate': 0,
            's3_block_public': 0
        }
        for record in daily_records:
            for action in record.get('remediation_actions', []):
                action_type = action.get('type', '')
                if action_type in action_counts:
                    action_counts[action_type] += 1

        # Calculate average remediation time
        remediation_times = [
            r.get('remediation_time_seconds', 0)
            for r in daily_records if r.get('remediation_time_seconds')
        ]
        avg_remediation_time = sum(remediation_times) / len(remediation_times) if remediation_times else 0

        # Cost impact
        estimated_prevented = sum(r.get('estimated_cost_prevented', 0) for r in daily_records)
        remediation_cost = sum(r.get('remediation_cost', 0) for r in daily_records)
        net_savings = estimated_prevented - remediation_cost

        # Top threats
        threat_types = {}
        for record in daily_records:
            threat_type = record.get('threat_type', 'Unknown')
            if threat_type not in threat_types:
                threat_types[threat_type] = {'count': 0, 'severities': []}
            threat_types[threat_type]['count'] += 1
            threat_types[threat_type]['severities'].append(record.get('severity', 5))

        top_threats = [
            {
                'threat_type': t,
                'count': data['count'],
                'average_severity': sum(data['severities']) / len(data['severities'])
            }
            for t, data in threat_types.items()
        ]
        top_threats.sort(key=lambda x: x['count'], reverse=True)

        return {
            'report_type': 'daily',
            'date': date,
            'total_threats_detected': total_detected,
            'total_threats_remediated': total_remediated,
            'remediation_success_rate': round(success_rate, 2),
            'threats_by_severity': severity_counts,
            'remediation_actions': action_counts,
            'average_remediation_time_seconds': round(avg_remediation_time, 2),
            'cost_impact': {
                'estimated_prevented_cost': round(estimated_prevented, 2),
                'remediation_cost': round(remediation_cost, 2),
                'net_savings': round(net_savings, 2)
            },
            'top_threats': top_threats,
            'summary': f"Daily Report ({date}): {total_detected} threats detected, {total_remediated} remediated ({success_rate*100:.0f}% success). Net savings: ${net_savings:.2f}",
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def analyze_trends(self, remediation_history: List[Dict], days: int = 7) -> Dict:
        """
        Analyze remediation trends over time.

        Args:
            remediation_history: List of remediation records
            days: Number of days to analyze

        Returns:
            {
                'period_days': int,
                'trend_analysis': {
                    'threats_per_day': [float],
                    'success_rate_trend': [float],
                    'average_severity_trend': [float]
                },
                'insights': [str],
                'recommendations': [str]
            }
        """
        daily_stats = {}

        # Aggregate by date
        for record in remediation_history:
            date = datetime.fromisoformat(record.get('timestamp', '')).strftime('%Y-%m-%d')
            if date not in daily_stats:
                daily_stats[date] = {
                    'total': 0,
                    'remediated': 0,
                    'severities': []
                }
            daily_stats[date]['total'] += 1
            if record.get('status') == 'success':
                daily_stats[date]['remediated'] += 1
            daily_stats[date]['severities'].append(record.get('severity', 5))

        # Get last N days
        sorted_dates = sorted(daily_stats.keys())[-days:]

        threats_per_day = [
            daily_stats[d]['total'] for d in sorted_dates
        ]
        success_rate_trend = [
            daily_stats[d]['remediated'] / daily_stats[d]['total'] if daily_stats[d]['total'] > 0 else 0
            for d in sorted_dates
        ]
        severity_trend = [
            sum(daily_stats[d]['severities']) / len(daily_stats[d]['severities']) if daily_stats[d]['severities'] else 0
            for d in sorted_dates
        ]

        # Generate insights
        insights = []
        if threats_per_day:
            avg_daily = sum(threats_per_day) / len(threats_per_day)
            if avg_daily > 10:
                insights.append(f"High threat volume: {avg_daily:.1f} threats/day on average")
            elif avg_daily > 5:
                insights.append(f"Moderate threat volume: {avg_daily:.1f} threats/day on average")

        if success_rate_trend:
            avg_success = sum(success_rate_trend) / len(success_rate_trend)
            if avg_success > 0.95:
                insights.append(f"Excellent remediation success rate: {avg_success*100:.0f}%")
            elif avg_success < 0.80:
                insights.append(f"Low remediation success rate: {avg_success*100:.0f}% - investigate failures")

        # Generate recommendations
        recommendations = []
        if threats_per_day and max(threats_per_day) > avg_daily * 2:
            recommendations.append("Consider increasing monitoring frequency during high-threat periods")
        if success_rate_trend and min(success_rate_trend) < 0.70:
            recommendations.append("Investigate remediation failures and improve automation")

        return {
            'period_days': len(sorted_dates),
            'trend_analysis': {
                'threats_per_day': [round(x, 2) for x in threats_per_day],
                'success_rate_trend': [round(x, 2) for x in success_rate_trend],
                'average_severity_trend': [round(x, 2) for x in severity_trend]
            },
            'insights': insights,
            'recommendations': recommendations,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def calculate_cost_impact(self, remediation_history: List[Dict], start_date: str, end_date: str) -> Dict:
        """
        Calculate cost impact of remediation actions.

        Args:
            remediation_history: List of remediation records
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            {
                'period': str,
                'start_date': str,
                'end_date': str,
                'total_remediation_cost': float,
                'estimated_prevented_cost': float,
                'net_savings': float,
                'roi_percentage': float,
                'cost_by_action_type': {
                    'ec2_stop': float,
                    'ec2_terminate': float,
                    ...
                },
                'prevented_cost_by_severity': {
                    'critical': float,
                    'high': float,
                    ...
                },
                'summary': str
            }
        """
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Filter records in date range
        filtered_records = [
            r for r in remediation_history
            if start <= datetime.fromisoformat(r.get('timestamp', '')).date() <= end
        ]

        # Calculate totals
        total_remediation_cost = sum(r.get('remediation_cost', 0) for r in filtered_records)
        estimated_prevented = sum(r.get('estimated_cost_prevented', 0) for r in filtered_records)
        net_savings = estimated_prevented - total_remediation_cost

        # ROI
        roi = (net_savings / total_remediation_cost * 100) if total_remediation_cost > 0 else 0

        # Cost by action type
        cost_by_action = {}
        for record in filtered_records:
            for action in record.get('remediation_actions', []):
                action_type = action.get('type', 'unknown')
                cost = action.get('cost', 0)
                cost_by_action[action_type] = cost_by_action.get(action_type, 0) + cost

        # Prevented cost by severity
        prevented_by_severity = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        for record in filtered_records:
            severity = record.get('severity', 5)
            prevented = record.get('estimated_cost_prevented', 0)
            if severity >= 9:
                prevented_by_severity['critical'] += prevented
            elif severity >= 7:
                prevented_by_severity['high'] += prevented
            elif severity >= 5:
                prevented_by_severity['medium'] += prevented
            else:
                prevented_by_severity['low'] += prevented

        return {
            'period': f"{start_date} to {end_date}",
            'start_date': start_date,
            'end_date': end_date,
            'total_remediation_cost': round(total_remediation_cost, 2),
            'estimated_prevented_cost': round(estimated_prevented, 2),
            'net_savings': round(net_savings, 2),
            'roi_percentage': round(roi, 2),
            'cost_by_action_type': {k: round(v, 2) for k, v in cost_by_action.items()},
            'prevented_cost_by_severity': {k: round(v, 2) for k, v in prevented_by_severity.items()},
            'summary': f"Cost Impact ({start_date} to {end_date}): ${estimated_prevented:.2f} prevented vs ${total_remediation_cost:.2f} spent. Net savings: ${net_savings:.2f} (ROI: {roi:.0f}%)",
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def generate_compliance_report(self, remediation_history: List[Dict], account_id: str) -> Dict:
        """
        Generate compliance report for audit trail.

        Args:
            remediation_history: List of remediation records
            account_id: AWS account ID

        Returns:
            {
                'report_type': 'compliance',
                'account_id': str,
                'generated_at': str,
                'total_threats_processed': int,
                'total_remediations': int,
                'approval_required_count': int,
                'auto_approved_count': int,
                'escalations': int,
                'audit_findings': [
                    {
                        'finding_id': str,
                        'severity': str,
                        'title': str,
                        'remediation_status': str,
                        'timestamp': str
                    }
                ],
                'compliance_summary': str
            }
        """
        total_threats = len(remediation_history)
        total_remediations = sum(1 for r in remediation_history if r.get('status') == 'success')
        approval_required = sum(1 for r in remediation_history if r.get('required_approval'))
        auto_approved = sum(1 for r in remediation_history if r.get('auto_approved'))
        escalations = sum(1 for r in remediation_history if r.get('escalated'))

        # Create findings for high-severity threats
        findings = []
        for i, record in enumerate(remediation_history):
            if record.get('severity', 0) >= 8:
                findings.append({
                    'finding_id': f"FINDING-{account_id}-{i:04d}",
                    'severity': 'Critical' if record.get('severity') >= 9 else 'High',
                    'title': f"{record.get('threat_type', 'Unknown Threat')} (Severity: {record.get('severity')})",
                    'remediation_status': record.get('status', 'pending'),
                    'timestamp': record.get('timestamp', '')
                })

        findings.sort(key=lambda x: x['timestamp'], reverse=True)

        return {
            'report_type': 'compliance',
            'account_id': account_id,
            'generated_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'total_threats_processed': total_threats,
            'total_remediations': total_remediations,
            'approval_required_count': approval_required,
            'auto_approved_count': auto_approved,
            'escalations': escalations,
            'audit_findings': findings[:50],  # Top 50 findings
            'compliance_summary': f"Compliance Report for {account_id}: {total_threats} threats processed, {total_remediations} remediated, {escalations} escalations. Approval rate: {approval_required}/{total_threats}."
        }
