"""Account Registry Storage"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AccountRegistry:
    """Persistent storage for account configurations"""

    def __init__(self, dynamodb_table):
        """
        Args:
            dynamodb_table: DynamoDB table for account storage
        """
        self.table = dynamodb_table

    def add_account(self, account_config: Dict) -> Dict:
        """
        Add a new account to registry

        Args:
            account_config: Account configuration dict
                - account_id: AWS account ID
                - role_arn: IAM role ARN
                - account_name: Friendly name
                - region: Primary region (optional)

        Returns:
            Added account with metadata
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

            # Store in DynamoDB
            self.table.put_item(Item=account)

            logger.info(f"Added account {account['account_name']} ({account['account_id']})")
            return account

        except Exception as e:
            logger.error(f"Failed to add account: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def get_account(self, account_id: str) -> Dict:
        """
        Get account configuration by ID

        Args:
            account_id: AWS account ID

        Returns:
            Account configuration or None if not found
        """
        try:
            response = self.table.get_item(Key={'account_id': account_id})
            account = response.get('Item')

            if account:
                logger.debug(f"Retrieved account {account_id}")
                return account
            else:
                logger.debug(f"Account {account_id} not found")
                return None

        except Exception as e:
            logger.error(f"Failed to get account: {str(e)}")
            return None

    def update_account(self, account_id: str, updates: Dict) -> Dict:
        """
        Update account configuration

        Args:
            account_id: AWS account ID
            updates: Fields to update

        Returns:
            Updated account configuration
        """
        try:
            # Get current account
            current = self.get_account(account_id)

            if not current:
                logger.warning(f"Account {account_id} not found for update")
                return {'error': f'Account {account_id} not found', 'status': 'not_found'}

            # Merge updates
            account = {**current, **updates}
            account['last_updated'] = datetime.now(timezone.utc).isoformat()

            # Store updated account
            self.table.put_item(Item=account)

            logger.info(f"Updated account {account_id}")
            return account

        except Exception as e:
            logger.error(f"Failed to update account: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def remove_account(self, account_id: str) -> bool:
        """
        Remove account from registry

        Args:
            account_id: AWS account ID

        Returns:
            True if removed successfully
        """
        try:
            self.table.delete_item(Key={'account_id': account_id})
            logger.info(f"Removed account {account_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove account: {str(e)}")
            return False

    def list_accounts(self, status: Optional[str] = None) -> List[Dict]:
        """
        List all registered accounts

        Args:
            status: Optional status filter (active, inactive, etc.)

        Returns:
            List of account configurations
        """
        try:
            response = self.table.scan()
            accounts = response.get('Items', [])

            # Filter by status if provided
            if status:
                accounts = [acc for acc in accounts if acc.get('status') == status]

            logger.info(f"Retrieved {len(accounts)} accounts")
            return accounts

        except Exception as e:
            logger.error(f"Failed to list accounts: {str(e)}")
            return []

    def list_accounts_by_status(self, status: str = 'active') -> List[Dict]:
        """
        Get accounts filtered by status

        Args:
            status: Account status (active, inactive, etc.)

        Returns:
            List of accounts with specified status
        """
        try:
            accounts = self.list_accounts(status=status)
            logger.info(f"Retrieved {len(accounts)} {status} accounts")
            return accounts

        except Exception as e:
            logger.error(f"Failed to get accounts by status: {str(e)}")
            return []

    def update_last_checked(self, account_id: str) -> bool:
        """
        Update last check timestamp for an account

        Args:
            account_id: AWS account ID

        Returns:
            True if updated successfully
        """
        try:
            updates = {
                'last_checked': datetime.now(timezone.utc).isoformat()
            }

            self.update_account(account_id, updates)
            logger.debug(f"Updated last_checked for account {account_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update last_checked: {str(e)}")
            return False

    def get_account_count(self, status: Optional[str] = None) -> int:
        """
        Get total count of registered accounts

        Args:
            status: Optional status filter

        Returns:
            Number of accounts
        """
        try:
            accounts = self.list_accounts(status=status)
            return len(accounts)

        except Exception as e:
            logger.error(f"Failed to get account count: {str(e)}")
            return 0
