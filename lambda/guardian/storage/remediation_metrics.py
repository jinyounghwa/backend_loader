"""Remediation outcome tracking and effectiveness metrics"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from guardian.storage.dynamodb import DynamoDBStorage
from guardian.aws_client_provider import AWSClientProvider
import logging

logger = logging.getLogger(__name__)


class RemediationMetricsStorage:

    def __init__(self):
        self.storage = DynamoDBStorage()
        self.table_name = 'guardian-remediation-metrics'

    def save_remediation_outcome(self, action_id: str, action_type: str, resource_id: str,
                                 region: str, status: str, rule_id: str) -> None:
        item = {
            'PK': f'ACTION#{action_id}',
            'SK': f'OUTCOME#{datetime.now(timezone.utc).isoformat()}',
            'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'action_type': action_type,
            'resource_id': resource_id,
            'region': region,
            'status': status,
            'rule_id': rule_id,
            'follow_up_status': 'pending',
            'TTL': int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
        }
        try:
            table = AWSClientProvider.get_resource('dynamodb').Table(self.table_name)
            table.put_item(Item=item)
        except Exception as e:
            logger.error("Error saving remediation outcome: %s", e)

    def update_follow_up_status(self, action_id: str, issue_resolved: bool) -> None:
        try:
            table = AWSClientProvider.get_resource('dynamodb').Table(self.table_name)
            table.update_item(
                Key={'PK': f'ACTION#{action_id}', 'SK': f'ACTION#{action_id}'},
                UpdateExpression='SET follow_up_status = :s, follow_up_timestamp = :t',
                ExpressionAttributeValues={
                    ':s': 'resolved' if issue_resolved else 'recurring',
                    ':t': int(datetime.now(timezone.utc).timestamp()),
                },
            )
        except Exception as e:
            logger.error("Error updating follow-up status for %s: %s", action_id, e)

    def get_rule_effectiveness(self, rule_id: str, days: int = 30) -> Optional[Dict]:
        try:
            table = AWSClientProvider.get_resource('dynamodb').Table(self.table_name)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_ts = int(cutoff.timestamp())

            response = table.scan(
                FilterExpression='rule_id = :rid AND #ts >= :cutoff',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={':rid': rule_id, ':cutoff': cutoff_ts},
                Limit=100,
            )

            items = response.get('Items', [])
            if not items:
                return None

            succeeded = len([i for i in items if i.get('status') == 'success'])
            total = len(items)
            resolved = len([i for i in items if i.get('follow_up_status') == 'resolved'])

            return {
                'rule_id': rule_id,
                'total_actions': total,
                'successful_actions': succeeded,
                'success_rate': (succeeded / total) if total > 0 else 0,
                'resolved_issues': resolved,
                'resolution_rate': (resolved / total) if total > 0 else 0,
                'effectiveness_score': ((succeeded / total) * 0.6 + (resolved / total) * 0.4) if total > 0 else 0,
            }
        except Exception as e:
            logger.error("Error calculating effectiveness for rule %s: %s", rule_id, e)
            return None

    def get_all_rule_metrics(self, days: int = 30) -> List[Dict]:
        try:
            table = AWSClientProvider.get_resource('dynamodb').Table(self.table_name)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_ts = int(cutoff.timestamp())

            response = table.scan(
                FilterExpression='#ts >= :cutoff',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={':cutoff': cutoff_ts},
                Limit=500,
            )

            items = response.get('Items', [])
            rule_groups: Dict[str, List[Dict]] = {}
            for item in items:
                rid = item.get('rule_id', 'unknown')
                if rid not in rule_groups:
                    rule_groups[rid] = []
                rule_groups[rid].append(item)

            metrics = []
            for rule_id, actions in rule_groups.items():
                succeeded = len([a for a in actions if a.get('status') == 'success'])
                resolved = len([a for a in actions if a.get('follow_up_status') == 'resolved'])
                total = len(actions)
                metrics.append({
                    'rule_id': rule_id,
                    'action_type': actions[0].get('action_type', 'unknown') if actions else 'unknown',
                    'total_actions': total,
                    'successful_actions': succeeded,
                    'success_rate': (succeeded / total) if total > 0 else 0,
                    'resolved_issues': resolved,
                    'resolution_rate': (resolved / total) if total > 0 else 0,
                    'effectiveness_score': ((succeeded / total) * 0.6 + (resolved / total) * 0.4) if total > 0 else 0,
                })

            return metrics
        except Exception as e:
            logger.error("Error getting all rule metrics: %s", e)
            return []
