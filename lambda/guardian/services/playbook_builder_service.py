"""Playbook Builder Service providing templates and validation for playbook creation."""

from typing import List, Dict


class PlaybookBuilderService:
    """Provides templates and validation for building custom playbooks."""

    def __init__(self):
        """Initialize playbook builder."""
        self.actions = self._initialize_action_templates()
        self.triggers = self._initialize_trigger_templates()
        self.examples = self._initialize_playbook_examples()

    def _initialize_action_templates(self) -> Dict:
        """Initialize available action templates."""
        return {
            'ec2_stop': {
                'name': 'Stop EC2 Instance',
                'description': 'Stop running EC2 instance',
                'category': 'compute',
                'parameters': {
                    'instance_ids': {'type': 'list', 'required': True}
                },
                'skip_on_failure': True,
                'dangerous': False
            },
            'ec2_terminate': {
                'name': 'Terminate EC2 Instance',
                'description': 'Terminate EC2 instance (irreversible)',
                'category': 'compute',
                'parameters': {
                    'instance_ids': {'type': 'list', 'required': True}
                },
                'skip_on_failure': False,
                'dangerous': True
            },
            'ec2_snapshot': {
                'name': 'Create EC2 Snapshot',
                'description': 'Create volume snapshot before remediation',
                'category': 'compute',
                'parameters': {
                    'instance_ids': {'type': 'list', 'required': True}
                },
                'skip_on_failure': True,
                'dangerous': False
            },
            'network_isolate': {
                'name': 'Isolate Network',
                'description': 'Restrict network access via security group',
                'category': 'network',
                'parameters': {
                    'security_group_ids': {'type': 'list', 'required': True},
                    'rule_description': {'type': 'string', 'required': False}
                },
                'skip_on_failure': True,
                'dangerous': False
            },
            'network_restrict_sg': {
                'name': 'Restrict Security Group',
                'description': 'Add deny rule to security group',
                'category': 'network',
                'parameters': {
                    'security_group_ids': {'type': 'list', 'required': True},
                    'ports': {'type': 'list', 'required': False}
                },
                'skip_on_failure': True,
                'dangerous': False
            },
            's3_block_public': {
                'name': 'Block S3 Public Access',
                'description': 'Block all public access to S3 bucket',
                'category': 'storage',
                'parameters': {
                    'bucket_names': {'type': 'list', 'required': True}
                },
                'skip_on_failure': False,
                'dangerous': False
            },
            's3_enable_versioning': {
                'name': 'Enable S3 Versioning',
                'description': 'Enable versioning on S3 bucket',
                'category': 'storage',
                'parameters': {
                    'bucket_names': {'type': 'list', 'required': True}
                },
                'skip_on_failure': True,
                'dangerous': False
            },
            'iam_revoke_roles': {
                'name': 'Revoke IAM Roles',
                'description': 'Remove IAM roles from resources',
                'category': 'identity',
                'parameters': {
                    'role_names': {'type': 'list', 'required': True}
                },
                'skip_on_failure': True,
                'dangerous': True
            },
            'iam_disable_keys': {
                'name': 'Disable IAM Access Keys',
                'description': 'Disable IAM access keys',
                'category': 'identity',
                'parameters': {
                    'access_key_ids': {'type': 'list', 'required': True}
                },
                'skip_on_failure': False,
                'dangerous': True
            },
            'sns_notify': {
                'name': 'Send SNS Notification',
                'description': 'Send notification via SNS topic',
                'category': 'notification',
                'parameters': {
                    'topic_arn': {'type': 'string', 'required': True},
                    'message': {'type': 'string', 'required': True}
                },
                'skip_on_failure': True,
                'dangerous': False
            },
            'lambda_invoke': {
                'name': 'Invoke Lambda Function',
                'description': 'Invoke Lambda function for custom logic',
                'category': 'compute',
                'parameters': {
                    'function_name': {'type': 'string', 'required': True},
                    'payload': {'type': 'object', 'required': False}
                },
                'skip_on_failure': True,
                'dangerous': False
            },
            'webhook_post': {
                'name': 'POST to Webhook',
                'description': 'Send HTTP POST to external webhook',
                'category': 'integration',
                'parameters': {
                    'url': {'type': 'string', 'required': True},
                    'payload': {'type': 'object', 'required': False}
                },
                'skip_on_failure': True,
                'dangerous': False
            }
        }

    def _initialize_trigger_templates(self) -> Dict:
        """Initialize available trigger templates."""
        return {
            'threat_type_match': {
                'name': 'Match Threat Type',
                'description': 'Trigger on specific threat type',
                'parameters': {
                    'threat_type': {'type': 'string', 'required': True}
                }
            },
            'severity_range': {
                'name': 'Match Severity Range',
                'description': 'Trigger based on threat severity',
                'parameters': {
                    'severity_range': {'type': 'array[int]', 'required': True}
                }
            },
            'account_filter': {
                'name': 'Filter by Account',
                'description': 'Trigger only for specific AWS accounts',
                'parameters': {
                    'account_ids': {'type': 'list[string]', 'required': True}
                }
            },
            'resource_type': {
                'name': 'Match Resource Type',
                'description': 'Trigger on resource type (EC2, S3, IAM, etc)',
                'parameters': {
                    'resource_types': {'type': 'list[string]', 'required': True}
                }
            },
            'custom_condition': {
                'name': 'Custom Field Matching',
                'description': 'Match based on custom threat fields',
                'parameters': {
                    'field': {'type': 'string', 'required': True},
                    'operator': {'type': 'string', 'required': True},
                    'value': {'type': 'any', 'required': True}
                }
            }
        }

    def _initialize_playbook_examples(self) -> List[Dict]:
        """Initialize example playbooks for common scenarios."""
        return [
            {
                'name': 'Unauthorized EC2 Response',
                'description': 'Respond to unauthorized EC2 instance detection',
                'threat_types': ['Unauthorized EC2'],
                'triggers': [
                    {
                        'threat_type': 'Unauthorized EC2',
                        'severity_range': [7, 10]
                    }
                ],
                'actions': [
                    {
                        'order': 1,
                        'action_type': 'ec2_snapshot',
                        'skip_on_failure': True
                    },
                    {
                        'order': 2,
                        'action_type': 'network_isolate',
                        'skip_on_failure': True
                    },
                    {
                        'order': 3,
                        'action_type': 'sns_notify',
                        'skip_on_failure': True
                    }
                ],
                'priority': 5
            },
            {
                'name': 'Public Bucket Remediation',
                'description': 'Respond to public S3 bucket detection',
                'threat_types': ['Public Bucket'],
                'triggers': [
                    {
                        'threat_type': 'Public Bucket',
                        'severity_range': [6, 10]
                    }
                ],
                'actions': [
                    {
                        'order': 1,
                        'action_type': 's3_block_public',
                        'skip_on_failure': False
                    },
                    {
                        'order': 2,
                        'action_type': 's3_enable_versioning',
                        'skip_on_failure': True
                    }
                ],
                'priority': 7
            },
            {
                'name': 'Credential Compromise Response',
                'description': 'Critical response to suspected credential compromise',
                'threat_types': ['Credential Compromise'],
                'triggers': [
                    {
                        'threat_type': 'Credential Compromise',
                        'severity_range': [9, 10]
                    }
                ],
                'actions': [
                    {
                        'order': 1,
                        'action_type': 'iam_disable_keys',
                        'skip_on_failure': False
                    },
                    {
                        'order': 2,
                        'action_type': 'iam_revoke_roles',
                        'skip_on_failure': True
                    },
                    {
                        'order': 3,
                        'action_type': 'sns_notify',
                        'skip_on_failure': True
                    }
                ],
                'priority': 1
            }
        ]

    def get_action_templates(self) -> Dict:
        """Return available action templates."""
        return self.actions

    def get_trigger_templates(self) -> Dict:
        """Return available trigger templates."""
        return self.triggers

    def validate_action(self, action_type: str, parameters: Dict) -> Dict:
        """Validate action configuration."""
        if action_type not in self.actions:
            return {
                'is_valid': False,
                'errors': [f'Unknown action type: {action_type}']
            }

        template = self.actions[action_type]
        errors = []

        # Check required parameters
        for param_name, param_spec in template.get('parameters', {}).items():
            if param_spec.get('required', False):
                if param_name not in parameters:
                    errors.append(f'Missing required parameter: {param_name}')

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }

    def validate_trigger(self, trigger_type: str, conditions: Dict) -> Dict:
        """Validate trigger configuration."""
        if trigger_type not in self.triggers:
            return {
                'is_valid': False,
                'errors': [f'Unknown trigger type: {trigger_type}']
            }

        template = self.triggers[trigger_type]
        errors = []

        # Check required conditions
        for param_name, param_spec in template.get('parameters', {}).items():
            if param_spec.get('required', False):
                if param_name not in conditions:
                    errors.append(f'Missing required condition: {param_name}')

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }

    def get_playbook_examples(self) -> List[Dict]:
        """Return example playbooks for common scenarios."""
        return self.examples

    def suggest_playbook_actions(self, threat_type: str) -> List[Dict]:
        """Suggest actions based on threat type."""
        suggestions = []

        for example in self.examples:
            if threat_type in example.get('threat_types', []):
                suggestions.append(example)

        return suggestions
