"""Custom rule builder for AWS Guardian."""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import uuid


class RuleBuilder:
    """Build custom rules."""

    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}

    def create(self, rule_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new rule."""
        rule_id = str(uuid.uuid4())

        rule = {
            'rule_id': rule_id,
            'name': rule_spec.get('name', 'Unnamed Rule'),
            'condition': rule_spec.get('condition'),
            'actions': rule_spec.get('actions', []),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'enabled': True
        }

        self.rules[rule_id] = rule
        return rule

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing rule."""
        if rule_id not in self.rules:
            return {'status': 'not_found', 'rule_id': rule_id}

        self.rules[rule_id].update(updates)
        self.rules[rule_id]['updated_at'] = datetime.utcnow().isoformat()

        return {'status': 'updated', 'rule_id': rule_id}

    def delete_rule(self, rule_id: str) -> Dict[str, Any]:
        """Delete a rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return {'status': 'deleted', 'rule_id': rule_id}

        return {'status': 'not_found', 'rule_id': rule_id}

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)

    def list_rules(self) -> List[Dict[str, Any]]:
        """List all rules."""
        return list(self.rules.values())


class RuleValidator:
    """Validate rule syntax and semantics."""

    VALID_ACTIONS = {
        'STOP_INSTANCE', 'ISOLATE', 'BLOCK', 'ALERT', 'NOTIFY_SLACK',
        'ESCALATE', 'ENABLE_MFA', 'BLOCK_PUBLIC_ACCESS', 'REMOVE_ACCESS'
    }

    def validate(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rule."""
        errors = []

        # Check condition
        condition = rule.get('condition')
        if not condition:
            errors.append('Condition is required')
        elif not isinstance(condition, str):
            errors.append('Condition must be a string')

        # Check actions
        actions = rule.get('actions', [])
        if not actions:
            errors.append('At least one action is required')
        else:
            for action in actions:
                if action not in self.VALID_ACTIONS:
                    errors.append(f"Unknown action: {action}")

        # Check condition syntax
        if condition:
            try:
                # Simple syntax check
                if not any(op in condition for op in ['==', '!=', '<', '>', '<=', '>=', 'OR', 'AND']):
                    errors.append('Condition must contain comparison operators')
            except Exception as e:
                errors.append(f"Syntax error: {str(e)}")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def get_valid_actions(self) -> Set[str]:
        """Get list of valid actions."""
        return self.VALID_ACTIONS


class RuleExecutor:
    """Execute rules against events."""

    def execute(self, rule: Dict[str, Any], event: Dict[str, Any]) -> List[str]:
        """Execute rule and return matching actions."""
        condition = rule.get('condition', '')
        actions = rule.get('actions', [])

        # Evaluate condition
        if self._evaluate_condition(condition, event):
            return actions
        else:
            return []

    def _evaluate_condition(self, condition: str, event: Dict[str, Any]) -> bool:
        """Evaluate condition expression."""
        try:
            # Remove parentheses for parsing
            clean_condition = condition.replace('(', '').replace(')', '')

            # Handle nested dictionary access
            # Simple evaluation for basic conditions
            if 'OR' in clean_condition:
                parts = clean_condition.split('OR')
                return any(self._evaluate_simple_condition(p.strip(), event) for p in parts)
            elif 'AND' in clean_condition:
                parts = clean_condition.split('AND')
                return all(self._evaluate_simple_condition(p.strip(), event) for p in parts)
            else:
                return self._evaluate_simple_condition(clean_condition, event)
        except Exception:
            return False

    def _evaluate_simple_condition(self, condition: str, event: Dict[str, Any]) -> bool:
        """Evaluate simple condition like 'threat.severity == CRITICAL'."""
        try:
            # Parse condition
            if '==' in condition:
                left, right = condition.split('==')
                left = left.strip().replace("'", "").replace('"', '')
                right = right.strip().replace("'", "").replace('"', '')

                # Navigate event object
                left_value = self._get_value(left, event)
                right_value = right

                return str(left_value) == str(right_value)
            elif '>' in condition:
                left, right = condition.split('>')
                left = left.strip()
                right = float(right.strip())

                left_value = float(self._get_value(left, event))
                return left_value > right
            elif '<' in condition:
                left, right = condition.split('<')
                left = left.strip()
                right = float(right.strip())

                left_value = float(self._get_value(left, event))
                return left_value < right

            return False
        except Exception:
            return False

    def _get_value(self, path: str, event: Dict[str, Any]) -> Any:
        """Navigate nested path in event."""
        parts = path.split('.')

        # First try full path navigation
        value = event
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                break

        # If we got a value, return it
        if value is not None:
            return value

        # Otherwise, try last part only (for top-level fields)
        if len(parts) > 1:
            return event.get(parts[-1])

        return value


class RuleLibrary:
    """Template library for common rules."""

    TEMPLATES = {
        'stop_critical_threats': {
            'name': 'Stop CRITICAL Threats',
            'condition': "threat.severity == 'CRITICAL'",
            'actions': ['STOP_INSTANCE', 'ISOLATE']
        },
        'high_cost_alert': {
            'name': 'High Cost Alert',
            'condition': "cost.daily > 100",
            'actions': ['ALERT', 'NOTIFY_SLACK']
        },
        'block_public_bucket': {
            'name': 'Block Public Bucket',
            'condition': "s3.bucket.public == True",
            'actions': ['BLOCK_PUBLIC_ACCESS']
        },
        'unauthorized_access': {
            'name': 'Unauthorized Access Alert',
            'condition': "access.unauthorized == True",
            'actions': ['ALERT', 'ESCALATE', 'ENABLE_MFA']
        },
        'malware_detected': {
            'name': 'Malware Detected',
            'condition': "threat.type == 'MALWARE'",
            'actions': ['ISOLATE', 'BLOCK', 'NOTIFY_SLACK']
        }
    }

    def get_templates(self) -> List[Dict[str, Any]]:
        """Get all templates."""
        return list(self.TEMPLATES.values())

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all templates with metadata."""
        templates = []
        for key, template in self.TEMPLATES.items():
            templates.append({
                'id': key,
                'name': template['name'],
                'description': f"Template: {template['name']}",
                'condition': template['condition'],
                'action_count': len(template['actions'])
            })
        return templates

    def create_from_template(self, template_id: str) -> Dict[str, Any]:
        """Create rule from template."""
        if template_id not in self.TEMPLATES:
            return {'status': 'not_found', 'template_id': template_id}

        template = self.TEMPLATES[template_id]
        rule_id = str(uuid.uuid4())

        return {
            'rule_id': rule_id,
            'name': template['name'],
            'condition': template['condition'],
            'actions': template['actions'],
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'from_template': template_id
        }

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID."""
        return self.TEMPLATES.get(template_id)
