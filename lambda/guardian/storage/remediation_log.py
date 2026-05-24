"""Remediation Action Logging and History"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class RemediationLog:
    """Track and manage remediation action history"""

    def __init__(self, dynamodb_table):
        """
        Args:
            dynamodb_table: DynamoDB table for remediation logs
        """
        self.table = dynamodb_table

    def log_remediation(self, action_record: Dict) -> Dict:
        """
        Log a remediation action to persistent storage

        Args:
            action_record: Record of remediation action
                - action_id: Unique action ID
                - action_type: Type of remediation
                - resource_id: Target resource
                - account_id: AWS account ID
                - status: success/failed
                - details: Additional details

        Returns:
            Logged record with metadata
        """
        try:
            log_entry = {
                'action_id': action_record.get('action_id'),
                'action_type': action_record.get('action_type'),
                'resource_id': action_record.get('resource_id'),
                'account_id': action_record.get('account_id'),
                'status': action_record.get('status', 'unknown'),
                'timestamp': action_record.get('timestamp', datetime.now(timezone.utc).isoformat()),
                'details': action_record.get('details', {}),
                'executed_by': action_record.get('executed_by', 'automated'),
                'error_message': action_record.get('error_message')
            }

            # Store in DynamoDB
            self.table.put_item(Item=log_entry)

            logger.info(f"Logged remediation action {action_record.get('action_id')}: {log_entry['status']}")
            return log_entry

        except Exception as e:
            logger.error(f"Failed to log remediation action: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def get_remediation_history(self, account_id: str, days: int = 30) -> List[Dict]:
        """
        Get remediation action history for an account

        Args:
            account_id: AWS account ID
            days: Number of days to look back (default: 30)

        Returns:
            List of remediation actions
        """
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

            # Query DynamoDB for account history
            response = self.table.scan(
                FilterExpression='#account = :account_id AND #timestamp > :cutoff',
                ExpressionAttributeNames={
                    '#account': 'account_id',
                    '#timestamp': 'timestamp'
                },
                ExpressionAttributeValues={
                    ':account_id': account_id,
                    ':cutoff': cutoff_time
                }
            )

            history = response.get('Items', [])

            # Sort by timestamp descending
            history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            logger.info(f"Retrieved {len(history)} remediation actions for account {account_id}")
            return history

        except Exception as e:
            logger.error(f"Failed to get remediation history: {str(e)}")
            return []

    def get_action_details(self, action_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific action

        Args:
            action_id: Unique action ID

        Returns:
            Action details or None if not found
        """
        try:
            response = self.table.get_item(Key={'action_id': action_id})
            action = response.get('Item')

            if action:
                logger.debug(f"Retrieved action details for {action_id}")
                return action
            else:
                logger.debug(f"Action {action_id} not found")
                return None

        except Exception as e:
            logger.error(f"Failed to get action details: {str(e)}")
            return None

    def log_rollback(self, original_action: Dict, rollback_action: Dict) -> Dict:
        """
        Log a rollback action

        Args:
            original_action: Original remediation action details
            rollback_action: Rollback action details

        Returns:
            Logged rollback record
        """
        try:
            rollback_record = {
                'action_id': f"rollback-{original_action.get('action_id')}",
                'action_type': f"rollback_{original_action.get('action_type')}",
                'original_action_id': original_action.get('action_id'),
                'resource_id': original_action.get('resource_id'),
                'account_id': original_action.get('account_id'),
                'status': rollback_action.get('status', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'rollback_details': {
                    'original_status': original_action.get('status'),
                    'rollback_status': rollback_action.get('status'),
                    'rolled_back_by': rollback_action.get('executed_by', 'automated')
                }
            }

            # Store rollback record
            self.table.put_item(Item=rollback_record)

            logger.info(f"Logged rollback for action {original_action.get('action_id')}")
            return rollback_record

        except Exception as e:
            logger.error(f"Failed to log rollback: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def calculate_remediation_success_rate(self, account_id: str, days: int = 30) -> Dict:
        """
        Calculate success rate of remediation actions

        Args:
            account_id: AWS account ID
            days: Number of days to analyze

        Returns:
            Success rate metrics
        """
        try:
            history = self.get_remediation_history(account_id, days)

            if not history:
                return {
                    'account_id': account_id,
                    'total_actions': 0,
                    'successful_actions': 0,
                    'failed_actions': 0,
                    'success_rate': 0.0,
                    'period_days': days
                }

            total = len(history)
            successful = sum(1 for action in history if action.get('status') == 'success')
            failed = sum(1 for action in history if action.get('status') == 'failed')

            success_rate = (successful / total * 100) if total > 0 else 0.0

            metrics = {
                'account_id': account_id,
                'total_actions': total,
                'successful_actions': successful,
                'failed_actions': failed,
                'success_rate': round(success_rate, 2),
                'period_days': days,
                'actions_by_type': self._count_actions_by_type(history),
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Calculated success rate for {account_id}: {success_rate:.2f}%")
            return metrics

        except Exception as e:
            logger.error(f"Failed to calculate success rate: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def _count_actions_by_type(self, history: List[Dict]) -> Dict:
        """Helper: Count actions grouped by type"""
        counts = {}

        for action in history:
            action_type = action.get('action_type', 'unknown')
            status = action.get('status', 'unknown')
            key = f"{action_type}:{status}"

            counts[key] = counts.get(key, 0) + 1

        return counts

    def get_remediation_statistics(self, account_id: Optional[str] = None) -> Dict:
        """
        Get aggregated remediation statistics

        Args:
            account_id: Optional account filter

        Returns:
            Aggregated statistics
        """
        try:
            stats = {
                'total_remediation_actions': 0,
                'success_count': 0,
                'failure_count': 0,
                'action_types': {},
                'recent_actions': [],
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }

            # Get recent actions
            if account_id:
                history = self.get_remediation_history(account_id)
            else:
                response = self.table.scan()
                history = response.get('Items', [])

            stats['total_remediation_actions'] = len(history)
            stats['success_count'] = sum(1 for a in history if a.get('status') == 'success')
            stats['failure_count'] = sum(1 for a in history if a.get('status') == 'failed')
            stats['action_types'] = self._count_actions_by_type(history)
            stats['recent_actions'] = history[:10]  # Last 10 actions

            logger.info(f"Compiled remediation statistics")
            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {'error': str(e), 'status': 'failed'}
