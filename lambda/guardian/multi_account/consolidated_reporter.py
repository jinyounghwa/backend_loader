"""Consolidated reporting across multiple accounts."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConsolidatedReporter:
    """Generate consolidated reports across accounts."""

    def __init__(self, account_manager=None):
        """Initialize reporter.
        
        Args:
            account_manager: AccountManager instance
        """
        self.account_manager = account_manager
        self.reports = []

    def generate_cost_report(
        self, costs_by_account: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate consolidated cost report.
        
        Args:
            costs_by_account: Dict of costs by account ID
            
        Returns:
            Cost report with metrics
        """
        total = sum(costs_by_account.values())
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_cost': total,
            'account_count': len(costs_by_account),
            'accounts': [],
            'metrics': {
                'average_cost': total / len(costs_by_account) if costs_by_account else 0,
                'max_cost': max(costs_by_account.values()) if costs_by_account else 0,
                'min_cost': min(costs_by_account.values()) if costs_by_account else 0,
            },
        }
        
        for account_id, cost in sorted(
            costs_by_account.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            report['accounts'].append({
                'account_id': account_id,
                'cost': cost,
                'percentage': (cost / total * 100) if total > 0 else 0,
            })
        
        return report

    def generate_anomaly_report(
        self, anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate consolidated anomaly report.
        
        Args:
            anomalies: List of detected anomalies
            
        Returns:
            Anomaly report
        """
        by_account = {}
        for anomaly in anomalies:
            account_id = anomaly.get('account_id')
            if account_id not in by_account:
                by_account[account_id] = []
            by_account[account_id].append(anomaly)
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_anomalies': len(anomalies),
            'accounts_affected': len(by_account),
            'by_account': by_account,
        }

    def generate_compliance_report(
        self, compliance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate compliance report across accounts.
        
        Args:
            compliance_data: Compliance check results
            
        Returns:
            Compliance report
        """
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_checks': compliance_data.get('total_checks', 0),
            'passed': compliance_data.get('passed', 0),
            'failed': compliance_data.get('failed', 0),
            'compliance_score': (
                (compliance_data.get('passed', 0) /
                 compliance_data.get('total_checks', 1)) * 100
                if compliance_data.get('total_checks', 0) > 0
                else 0
            ),
        }

    def export_report(self, report: Dict[str, Any]) -> str:
        """Export report as JSON.
        
        Args:
            report: Report dict to export
            
        Returns:
            JSON string
        """
        import json
        return json.dumps(report, indent=2)
