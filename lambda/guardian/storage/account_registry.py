"""Account registry storage."""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class AccountRegistry:
    """Store and manage account registrations."""

    def __init__(self):
        """Initialize registry."""
        self.accounts = {}

    def register(
        self,
        account_id: str,
        account_name: str,
        role_arn: str,
        cost_limit: float,
    ) -> bool:
        """Register account.
        
        Args:
            account_id: AWS account ID
            account_name: Friendly name
            role_arn: IAM role ARN to assume
            cost_limit: Monthly cost limit
            
        Returns:
            True if successful
        """
        try:
            self.accounts[account_id] = {
                'account_id': account_id,
                'account_name': account_name,
                'role_arn': role_arn,
                'cost_limit': cost_limit,
                'is_active': True,
            }
            logger.info(f"Registered account {account_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register account: {e}")
            return False

    def get(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account by ID.
        
        Args:
            account_id: AWS account ID
            
        Returns:
            Account dict or None
        """
        return self.accounts.get(account_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all accounts.
        
        Returns:
            List of account dicts
        """
        return list(self.accounts.values())

    def update(self, account_id: str, updates: Dict[str, Any]) -> bool:
        """Update account.
        
        Args:
            account_id: AWS account ID
            updates: Updates dict
            
        Returns:
            True if successful
        """
        if account_id not in self.accounts:
            return False
        
        self.accounts[account_id].update(updates)
        return True

    def delete(self, account_id: str) -> bool:
        """Delete account.
        
        Args:
            account_id: AWS account ID
            
        Returns:
            True if successful
        """
        if account_id in self.accounts:
            del self.accounts[account_id]
            return True
        return False
