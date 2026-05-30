"""Sync local changes when mobile comes online."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


class SyncManager:
    """Manage local changes and sync when online."""

    def __init__(self):
        self.local_actions: List[Dict[str, Any]] = []
        self.sync_history: List[Dict[str, Any]] = []
        self.is_online = True

    def record_local_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Record an action to sync later."""
        action_id = str(uuid.uuid4())

        local_action = {
            'action_id': action_id,
            'action': action.get('action'),
            'resource_id': action.get('instance_id') or action.get('bucket_id'),
            'recorded_at': datetime.utcnow().isoformat(),
            'status': 'pending_sync',
            'action_details': action
        }

        self.local_actions.append(local_action)

        return {
            'action_id': action_id,
            'status': 'recorded',
            'will_sync_when_online': True
        }

    def set_online_status(self, is_online: bool) -> Dict[str, Any]:
        """Set device online/offline status."""
        self.is_online = is_online

        if is_online and len(self.local_actions) > 0:
            return {'status': 'online', 'pending_sync': len(self.local_actions)}

        return {
            'status': 'online' if is_online else 'offline',
            'pending_actions': len(self.local_actions)
        }

    def sync(self) -> Dict[str, Any]:
        """Sync local changes when online."""
        if not self.is_online:
            return {'status': 'offline', 'actions_synced': 0}

        actions_synced = len(self.local_actions)

        # Sync all pending actions
        for action in self.local_actions:
            action['status'] = 'synced'
            action['synced_at'] = datetime.utcnow().isoformat()

        sync_record = {
            'sync_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'actions_synced': actions_synced,
            'status': 'completed'
        }

        self.sync_history.append(sync_record)

        # Clear pending actions
        self.local_actions = []

        return {
            'status': 'synced',
            'actions_synced': actions_synced,
            'sync_id': sync_record['sync_id']
        }

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get list of actions pending sync."""
        return self.local_actions

    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sync history."""
        return sorted(
            self.sync_history[-limit:],
            key=lambda s: s['timestamp'],
            reverse=True
        )
