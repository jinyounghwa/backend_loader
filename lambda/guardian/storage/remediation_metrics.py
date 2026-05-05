"""Remediation outcome tracking and effectiveness metrics"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from guardian.storage.dynamodb import DynamoDBStorage


class RemediationMetricsStorage:
    """Track remediation actions and calculate effectiveness scores."""

    def __init__(self):
        self.dynamodb = DynamoDBStorage()
        self.table_name = 'guardian-remediation-metrics'

    def save_remediation_outcome(self, action_id: str, action_type: str, resource_id: str,
                                region: str, status: str, rule_id: str) -> None:
        """Save remediation outcome."""
        item = {
            'PK': f'ACTION#{action_id}',
            'SK': f'OUTCOME#{datetime.utcnow().isoformat()}',
            'timestamp': int(datetime.utcnow().timestamp()),
            'action_type': action_type,
            'resource_id': resource_id,
            'region': region,
            'status': status,
            'rule_id': rule_id,
            'follow_up_status': 'pending',
            'TTL': int((datetime.utcnow() + timedelta(days=90)).timestamp()),
        }
        self.dynamodb.put_item(self.table_name, item)

    def update_follow_up_status(self, action_id: str, issue_resolved: bool) -> None:
        """Mark if issue is still present in follow-up check."""
        try:
            self.dynamodb.update_item(
                self.table_name,
                {'PK': f'ACTION#{action_id}'},
                {
                    'follow_up_status': 'resolved' if issue_resolved else 'recurring',
                    'follow_up_timestamp': int(datetime.utcnow().timestamp()),
                },
            )
        except Exception:
            pass

    def get_rule_effectiveness(self, rule_id: str, days: int = 30) -> Optional[Dict]:
        """Calculate effectiveness score for a rule."""
        try:
            response = self.dynamodb.query(
                self.table_name,
                'SK',
                f'RULE#{rule_id}',
                limit=100,
            )
            items = response.get('Items', [])
            if not items:
                return None

            cutoff = datetime.utcnow() - timedelta(days=days)
            recent_items = [i for i in items
                          if int(i.get('timestamp', 0)) > cutoff.timestamp()]

            if not recent_items:
                return None

            succeeded = len([i for i in recent_items if i.get('status') == 'success'])
            total = len(recent_items)
            resolved = len([i for i in recent_items if i.get('follow_up_status') == 'resolved'])

            return {
                'rule_id': rule_id,
                'total_actions': total,
                'successful_actions': succeeded,
                'success_rate': (succeeded / total) if total > 0 else 0,
                'resolved_issues': resolved,
                'resolution_rate': (resolved / total) if total > 0 else 0,
                'effectiveness_score': ((succeeded / total) * 0.6 + (resolved / total) * 0.4) if total > 0 else 0,
            }
        except Exception:
            return None

    def get_all_rule_metrics(self, days: int = 30) -> List[Dict]:
        """Get metrics for all rules."""
        # In production: scan remediation-metrics table, group by rule_id
        # For now: return mock data showing effectiveness
        return [
            {
                'rule_id': 'rule-001',
                'action_type': 'stop_instance',
                'total_actions': 15,
                'successful_actions': 14,
                'success_rate': 0.93,
                'resolved_issues': 13,
                'resolution_rate': 0.87,
                'effectiveness_score': 0.90,
            },
            {
                'rule_id': 'rule-002',
                'action_type': 'stop_instance',
                'total_actions': 8,
                'successful_actions': 7,
                'success_rate': 0.88,
                'resolved_issues': 6,
                'resolution_rate': 0.75,
                'effectiveness_score': 0.82,
            },
            {
                'rule_id': 'rule-003',
                'action_type': 'block_bucket',
                'total_actions': 22,
                'successful_actions': 22,
                'success_rate': 1.0,
                'resolved_issues': 21,
                'resolution_rate': 0.95,
                'effectiveness_score': 0.98,
            },
        ]
