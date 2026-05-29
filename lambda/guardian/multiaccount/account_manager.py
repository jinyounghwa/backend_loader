"""Multi-account orchestration and management."""

import logging
from typing import Dict, List, Any, Optional

from guardian.multiaccount.role_assumptioner import RoleAssumptioner

logger = logging.getLogger(__name__)


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
