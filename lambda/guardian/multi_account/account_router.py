"""Route events to correct account handlers."""

from typing import Dict, Any, Optional, List
from datetime import datetime


class EventRouter:
    """Route cross-account events to correct handlers."""

    def __init__(self):
        self.disabled_accounts: set = set()
        self.account_handlers: Dict[str, callable] = {}

    def route_event(self, event: Dict[str, Any]) -> Optional[str]:
        """Route event to correct account."""
        account_id = event.get('account_id')

        if not account_id:
            return None

        # Check if account is disabled
        if account_id in self.disabled_accounts:
            return None

        return account_id

    def register_handler(self, account_id: str, handler: callable) -> None:
        """Register handler for account."""
        self.account_handlers[account_id] = handler

    def handle_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route and handle event."""
        account_id = self.route_event(event)

        if not account_id:
            return None

        handler = self.account_handlers.get(account_id)

        if handler:
            return handler(event)

        return {'account_id': account_id, 'routed': True}

    def disable_account(self, account_id: str) -> None:
        """Disable account from receiving events."""
        self.disabled_accounts.add(account_id)

    def enable_account(self, account_id: str) -> None:
        """Enable account to receive events."""
        self.disabled_accounts.discard(account_id)


class AccountContext:
    """Manage account context for request handling."""

    def __init__(self):
        self.current_account: Optional[str] = None
        self.credentials: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

    def set_account(self, account_id: str) -> None:
        """Set current account context."""
        self.current_account = account_id

    def get_account(self) -> Optional[str]:
        """Get current account."""
        return self.current_account

    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        """Set account credentials."""
        self.credentials = credentials

    def get_credentials(self) -> Dict[str, Any]:
        """Get credentials for current account."""
        if not self.current_account:
            return {}

        return {
            'account_id': self.current_account,
            'credentials': self.credentials,
            'set_at': datetime.utcnow().isoformat()
        }

    def set_metadata(self, key: str, value: Any) -> None:
        """Set account metadata."""
        self.metadata[key] = value

    def get_metadata(self, key: str) -> Optional[Any]:
        """Get account metadata."""
        return self.metadata.get(key)


class MultiAccountOrchestrator:
    """Orchestrate operations across multiple accounts."""

    def __init__(self):
        self.registry: Dict[str, Any] = {}
        self.router = EventRouter()

    def register_account(self, account_id: str, config: Dict[str, Any]) -> bool:
        """Register account in orchestrator."""
        self.registry[account_id] = config
        return True

    def execute_across_accounts(
        self,
        operation: callable,
        accounts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute operation across multiple accounts."""
        if accounts is None:
            accounts = list(self.registry.keys())

        results = {}

        for account_id in accounts:
            if account_id in self.registry:
                try:
                    context = AccountContext()
                    context.set_account(account_id)
                    results[account_id] = operation(context)
                except Exception as e:
                    results[account_id] = {'error': str(e)}

        return results

    def aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from multiple accounts."""
        return {
            'total_accounts': len(results),
            'successful': len([r for r in results.values() if 'error' not in r]),
            'failed': len([r for r in results.values() if 'error' in r]),
            'results': results
        }
