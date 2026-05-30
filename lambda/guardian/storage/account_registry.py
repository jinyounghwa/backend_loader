"""Account registry storage."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AccountRegistry:
    """Store and manage account registrations."""

    def __init__(self, dynamodb_table=None):
        """Initialize registry.
        
        Args:
            dynamodb_table: Optional DynamoDB table for backward compatibility.
        """
        self.table = dynamodb_table
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

    # --- Backward compatibility methods for Sprint 42 / test_multi_account_manager.py ---

    def add_account(self, account_config: Dict) -> Dict:
        """Add a new account to registry.
        
        Args:
            account_config: Configuration dictionary for the account.
            
        Returns:
            Added account dictionary.
        """
        try:
            account = {
                'account_id': account_config.get('account_id'),
                'role_arn': account_config.get('role_arn'),
                'account_name': account_config.get('account_name'),
                'region': account_config.get('region', 'us-east-1'),
                'status': 'active',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_checked': None
            }

            self.accounts[account['account_id']] = account

            if self.table:
                self.table.put_item(Item=account)

            logger.info(f"Added account {account['account_name']} ({account['account_id']})")
            return account
        except Exception as e:
            logger.error(f"Failed to add account: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def get_account(self, account_id: str) -> Optional[Dict]:
        """Get account configuration by ID."""
        try:
            if self.table:
                response = self.table.get_item(Key={'account_id': account_id})
                account = response.get('Item')
                if account:
                    return account
            return self.accounts.get(account_id)
        except Exception as e:
            logger.error(f"Failed to get account: {str(e)}")
            return None

    def update_account(self, account_id: str, updates: Dict) -> Dict:
        """Update account configuration."""
        try:
            current = self.get_account(account_id) or {}
            account = {**current, **updates}
            account['last_updated'] = datetime.now(timezone.utc).isoformat()

            self.accounts[account_id] = account

            if self.table:
                self.table.put_item(Item=account)

            logger.info(f"Updated account {account_id}")
            return account
        except Exception as e:
            logger.error(f"Failed to update account: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def remove_account(self, account_id: str) -> bool:
        """Remove account from registry."""
        try:
            removed = False
            if account_id in self.accounts:
                del self.accounts[account_id]
                removed = True
            if self.table:
                self.table.delete_item(Key={'account_id': account_id})
                removed = True
            logger.info(f"Removed account {account_id}")
            return removed
        except Exception as e:
            logger.error(f"Failed to remove account: {str(e)}")
            return False

    def list_accounts(self, status: Optional[str] = None) -> List[Dict]:
        """List all registered accounts."""
        try:
            if self.table:
                response = self.table.scan()
                accounts = response.get('Items', [])
            else:
                accounts = list(self.accounts.values())

            if status:
                accounts = [acc for acc in accounts if acc.get('status') == status]

            logger.info(f"Retrieved {len(accounts)} accounts")
            return accounts
        except Exception as e:
            logger.error(f"Failed to list accounts: {str(e)}")
            return []

    def list_accounts_by_status(self, status: str = 'active') -> List[Dict]:
        """Get accounts filtered by status."""
        return self.list_accounts(status=status)

    def update_last_checked(self, account_id: str) -> bool:
        """Update last check timestamp for an account."""
        try:
            updates = {
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
            self.update_account(account_id, updates)
            return True
        except Exception as e:
            logger.error(f"Failed to update last_checked: {str(e)}")
            return False

    def get_account_count(self, status: Optional[str] = None) -> int:
        """Get total count of registered accounts."""
        return len(self.list_accounts(status=status))

