"""Playbook Definition Service for managing custom remediation playbooks."""

from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid


class PlaybookDefinitionService:
    """Manages custom remediation playbook definitions."""

    def __init__(self, audit_logger=None):
        """Initialize playbook service."""
        self.audit = audit_logger
        self.playbooks = {}

    def create_playbook(self, name: str, description: str, triggers: List[Dict],
                       actions: List[Dict], priority: int) -> Dict:
        """Create new remediation playbook."""
        playbook_id = str(uuid.uuid4())

        playbook = {
            'playbook_id': playbook_id,
            'name': name,
            'description': description,
            'enabled': True,
            'priority': min(max(priority, 1), 10),  # Clamp 1-10
            'triggers': triggers,
            'actions': actions,
            'approval_required': False,
            'approval_group': None,
            'created_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'updated_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'execution_count': 0
        }

        self.playbooks[playbook_id] = playbook
        return playbook

    def update_playbook(self, playbook_id: str, updates: Dict) -> Optional[Dict]:
        """Update existing playbook."""
        if playbook_id not in self.playbooks:
            return None

        playbook = self.playbooks[playbook_id]

        # Update allowed fields
        for field in ['name', 'description', 'triggers', 'actions', 'priority', 'approval_required', 'approval_group']:
            if field in updates:
                if field == 'priority':
                    playbook[field] = min(max(updates[field], 1), 10)
                else:
                    playbook[field] = updates[field]

        playbook['updated_at'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        return playbook

    def delete_playbook(self, playbook_id: str) -> bool:
        """Delete playbook."""
        if playbook_id in self.playbooks:
            del self.playbooks[playbook_id]
            return True
        return False

    def get_playbook(self, playbook_id: str) -> Optional[Dict]:
        """Get playbook details."""
        return self.playbooks.get(playbook_id)

    def list_playbooks(self, enabled_only: bool = False) -> List[Dict]:
        """List all playbooks or only enabled ones."""
        playbooks = list(self.playbooks.values())

        if enabled_only:
            playbooks = [p for p in playbooks if p.get('enabled', True)]

        # Sort by priority (higher priority first), then by creation date
        playbooks.sort(key=lambda p: (-p.get('priority', 5), p.get('created_at', '')))
        return playbooks

    def enable_playbook(self, playbook_id: str) -> bool:
        """Enable playbook for automatic execution."""
        if playbook_id not in self.playbooks:
            return False

        self.playbooks[playbook_id]['enabled'] = True
        self.playbooks[playbook_id]['updated_at'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        return True

    def disable_playbook(self, playbook_id: str) -> bool:
        """Disable playbook temporarily."""
        if playbook_id not in self.playbooks:
            return False

        self.playbooks[playbook_id]['enabled'] = False
        self.playbooks[playbook_id]['updated_at'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        return True

    def validate_playbook(self, playbook: Dict) -> Dict:
        """Validate playbook structure and action syntax."""
        errors = []
        warnings = []

        # Validate name
        if not playbook.get('name'):
            errors.append('Playbook name is required')

        # Validate triggers
        if not playbook.get('triggers'):
            errors.append('At least one trigger is required')
        else:
            for trigger in playbook['triggers']:
                if not trigger.get('threat_type'):
                    errors.append('Trigger must specify threat_type')

        # Validate actions
        if not playbook.get('actions'):
            errors.append('At least one action is required')
        else:
            valid_action_types = [
                'ec2_stop', 'ec2_terminate', 'ec2_snapshot',
                'network_isolate', 'network_restrict_sg',
                's3_block_public', 's3_enable_versioning',
                'iam_revoke_roles', 'iam_disable_keys',
                'sns_notify', 'lambda_invoke', 'webhook_post'
            ]

            for action in playbook['actions']:
                if not action.get('action_type') in valid_action_types:
                    errors.append(f'Invalid action_type: {action.get("action_type")}')
                if action.get('order') is None:
                    warnings.append('Action missing order field')

        # Validate priority
        priority = playbook.get('priority', 5)
        if not (1 <= priority <= 10):
            errors.append('Priority must be between 1 and 10')

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'error_count': len(errors),
            'warning_count': len(warnings)
        }

    def increment_execution_count(self, playbook_id: str) -> None:
        """Increment execution counter for playbook."""
        if playbook_id in self.playbooks:
            self.playbooks[playbook_id]['execution_count'] = \
                self.playbooks[playbook_id].get('execution_count', 0) + 1

    def get_playbook_stats(self) -> Dict:
        """Get statistics about playbooks."""
        playbooks = list(self.playbooks.values())

        return {
            'total_playbooks': len(playbooks),
            'enabled_playbooks': len([p for p in playbooks if p.get('enabled', True)]),
            'disabled_playbooks': len([p for p in playbooks if not p.get('enabled', True)]),
            'approval_required_playbooks': len([p for p in playbooks if p.get('approval_required', False)]),
            'total_executions': sum(p.get('execution_count', 0) for p in playbooks),
            'average_priority': sum(p.get('priority', 5) for p in playbooks) / len(playbooks) if playbooks else 0
        }

    def export_playbook(self, playbook_id: str) -> Optional[Dict]:
        """Export playbook as shareable template."""
        playbook = self.get_playbook(playbook_id)
        if not playbook:
            return None

        return {
            'name': playbook['name'],
            'description': playbook['description'],
            'triggers': playbook['triggers'],
            'actions': playbook['actions'],
            'priority': playbook['priority'],
            'approval_required': playbook.get('approval_required', False)
        }

    def import_playbook(self, template: Dict) -> Dict:
        """Import playbook from template."""
        return self.create_playbook(
            name=template.get('name', 'Imported Playbook'),
            description=template.get('description', ''),
            triggers=template.get('triggers', []),
            actions=template.get('actions', []),
            priority=template.get('priority', 5)
        )
