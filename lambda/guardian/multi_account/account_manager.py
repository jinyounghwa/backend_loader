"""Multi-account AWS support for Guardian."""

import logging

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from guardian.multi_account.role_assumptioner import RoleAssumptioner

logger = logging.getLogger(__name__)


class AccountRegistry:
    """Manage registered AWS accounts."""

    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.audit_log: Dict[str, List[Dict[str, Any]]] = {}

    def register(self, account_data: Dict[str, Any]) -> bool:
        """Register a new AWS account."""
        account_id = account_data.get('account_id')

        if not account_id:
            return False

        self.accounts[account_id] = {
            'account_id': account_id,
            'account_name': account_data.get('account_name', ''),
            'role_arn': account_data.get('role_arn', ''),
            'enabled': account_data.get('enabled', True),
            'policy': account_data.get('policy', {}),
            'registered_at': datetime.utcnow().isoformat()
        }

        # Initialize audit log
        if account_id not in self.audit_log:
            self.audit_log[account_id] = []

        self.audit_log[account_id].append({
            'action': 'REGISTER',
            'timestamp': datetime.utcnow().isoformat(),
            'data': account_data
        })

        return True

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account details."""
        return self.accounts.get(account_id)

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List all registered accounts."""
        return list(self.accounts.values())

    def update_account(self, account_id: str, updates: Dict[str, Any]) -> bool:
        """Update account settings."""
        if account_id not in self.accounts:
            return False

        self.accounts[account_id].update(updates)

        self.audit_log[account_id].append({
            'action': 'UPDATE',
            'timestamp': datetime.utcnow().isoformat(),
            'updates': updates
        })

        return True

    def get_audit_log(self, account_id: str) -> List[Dict[str, Any]]:
        """Get audit log for account."""
        return self.audit_log.get(account_id, [])

    def health_check(self, account_id: str) -> Dict[str, Any]:
        """Check account health."""
        account = self.get_account(account_id)

        if not account:
            return {'status': 'unhealthy', 'reason': 'not_found'}

        if not account['enabled']:
            return {'status': 'unhealthy', 'reason': 'disabled'}

        return {
            'status': 'healthy',
            'account_id': account_id,
            'last_check': datetime.utcnow().isoformat()
        }


class RoleAssumer:
    """Assume roles in other AWS accounts."""

    def assume_role(
        self,
        role_arn: str,
        session_name: str = 'guardian-session',
        duration_seconds: int = 3600
    ) -> Optional[Dict[str, Any]]:
        """Assume a role in another account."""
        # In production, this would use boto3 STS AssumeRole
        # For now, return mock session

        if not role_arn or '999999999999' in role_arn:
            return None

        return {
            'session_name': session_name,
            'role_arn': role_arn,
            'duration_seconds': duration_seconds,
            'credentials': {
                'AccessKeyId': f'ASIA{session_name[:20]}',
                'SecretAccessKey': 'mock-secret-key',
                'SessionToken': f'token-{session_name}',
                'Expiration': datetime.utcnow().isoformat()
            },
            'AssumedRoleArn': role_arn,
            'Expiration': datetime.utcnow().isoformat()
        }

    def refresh_session(self, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Refresh expired session."""
        if not session or 'role_arn' not in session:
            return None

        return self.assume_role(
            session['role_arn'],
            session.get('session_name', 'guardian-session'),
            session.get('duration_seconds', 3600)
        )


class AccountAggregator:
    """Aggregate data across multiple accounts."""

    def aggregate_ec2_instances(self, accounts: List[Dict[str, Any]]) -> int:
        """Aggregate EC2 instances across accounts."""
        total = 0

        for account in accounts:
            instances = account.get('instances', 0)
            total += instances

        return total

    def aggregate_iam_risk(self, findings: List[Dict[str, Any]]) -> float:
        """Aggregate IAM risk scores."""
        if not findings:
            return 0

        total_risk = sum(f.get('risk_score', 0) for f in findings)
        avg_risk = total_risk / len(findings)

        return avg_risk

    def aggregate_costs(self, costs: List[Dict[str, Any]]) -> float:
        """Aggregate costs across accounts."""
        total_cost = 0

        for cost in costs:
            monthly = cost.get('monthly_cost', 0)
            total_cost += monthly

        return total_cost

    def aggregate_threats(self, threats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate threat data across accounts."""
        severity_counts = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        }

        for threat in threats:
            severity = threat.get('severity', 'LOW')
            if severity in severity_counts:
                severity_counts[severity] += 1

        return {
            'total_threats': len(threats),
            'by_severity': severity_counts,
            'critical_count': severity_counts['CRITICAL']
        }

    def aggregate_compliance(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate compliance findings."""
        total_findings = len(findings)
        critical_findings = len([f for f in findings if f.get('severity') == 'CRITICAL'])

        compliance_score = 100 - (critical_findings / max(total_findings, 1) * 100)

        return {
            'total_findings': total_findings,
            'critical_findings': critical_findings,
            'compliance_score': max(0, min(100, compliance_score))
        }


class AccountManager:
    """Manage operations across multiple AWS accounts."""

    def __init__(self):
        """Initialize account manager."""
        self.assumptioner = RoleAssumptioner()
        self.registered_accounts = {}

    def register_account(
        self,
        account_id: str,
        account_name: str,
        role_arn: str,
        cost_limit: float,
    ) -> bool:
        """Register a member account.
        
        Args:
            account_id: AWS account ID
            account_name: Friendly name for account
            role_arn: ARN of role to assume
            cost_limit: Monthly cost limit in USD
            
        Returns:
            True if successful
        """
        try:
            self.registered_accounts[account_id] = {
                'account_id': account_id,
                'account_name': account_name,
                'role_arn': role_arn,
                'cost_limit': cost_limit,
                'is_active': True,
            }
            logger.info(f"Registered account {account_id}: {account_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register account: {e}")
            return False

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List all registered accounts.
        
        Returns:
            List of account details
        """
        return list(self.registered_accounts.values())

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get details for specific account.
        
        Args:
            account_id: AWS account ID
            
        Returns:
            Account details or None
        """
        return self.registered_accounts.get(account_id)

    def get_per_account_cost(
        self, account_id: str, cost_data: Dict[str, float]
    ) -> float:
        """Get costs for specific account.
        
        Args:
            account_id: AWS account ID
            cost_data: Dict of costs by account
            
        Returns:
            Cost for account or 0
        """
        return cost_data.get(account_id, 0.0)

    def get_consolidated_cost_view(
        self, costs_by_account: Dict[str, float]
    ) -> Dict[str, Any]:
        """Get consolidated view of costs across all accounts.
        
        Args:
            costs_by_account: Dict mapping account IDs to costs
            
        Returns:
            Consolidated cost analysis
        """
        total_cost = sum(costs_by_account.values())
        
        account_breakdown = []
        for account_id, cost in costs_by_account.items():
            account = self.get_account(account_id)
            account_breakdown.append({
                'account_id': account_id,
                'account_name': account.get('account_name') if account else account_id,
                'cost': cost,
                'cost_limit': account.get('cost_limit', 0) if account else 0,
                'percentage': (cost / total_cost * 100) if total_cost > 0 else 0,
            })
        
        return {
            'total_cost': total_cost,
            'account_count': len(costs_by_account),
            'breakdown': sorted(
                account_breakdown,
                key=lambda x: x['cost'],
                reverse=True
            ),
        }

    def check_cost_threshold(
        self, account_id: str, current_cost: float
    ) -> bool:
        """Check if account exceeds cost limit.
        
        Args:
            account_id: AWS account ID
            current_cost: Current month cost
            
        Returns:
            True if threshold exceeded
        """
        account = self.get_account(account_id)
        if not account:
            return False
        
        return current_cost > account['cost_limit']

    def apply_account_rules(
        self, account_id: str, rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply rules specific to an account.
        
        Args:
            account_id: AWS account ID
            rules: List of rules to apply
            
        Returns:
            List of applied rules
        """
        account = self.get_account(account_id)
        if not account or not account['is_active']:
            return []
        
        # Filter rules for this account
        applied = [r for r in rules if r.get('account_id') is None
                   or r.get('account_id') == account_id]
        
        return applied
