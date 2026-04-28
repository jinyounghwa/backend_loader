"""IAM checker for permission changes detection."""

from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timezone
import logging

from base import BaseChecker, CheckResult

logger = logging.getLogger(__name__)


class IAMChecker(BaseChecker):
    """Detect IAM permission changes and access key creation."""

    def __init__(self, clients: Dict[str, Any], config: Dict[str, Any]):
        super().__init__(clients, config)
        self.iam = clients.get('iam')
        self.dynamodb = clients.get('dynamodb')
        self.baseline_key = 'iam-baseline'

    def check(self) -> CheckResult:
        """Check for IAM permission changes."""
        self._log_check_start('IAM')

        try:
            # Get current IAM state
            current_users = self._get_iam_users()
            current_keys = self._get_access_keys(current_users)

            # Get baseline from DynamoDB
            baseline = self._get_baseline()

            # Detect changes
            changes = self._detect_changes(current_users, current_keys, baseline)

            if changes:
                severity = self._determine_severity(changes)
                self._log_check_end('IAM', severity)

                # Save current state as new baseline
                self._save_baseline(current_users, current_keys)

                return CheckResult(
                    severity=severity,
                    title='IAM Permission Changes Detected',
                    message=f'Found {len(changes)} IAM changes',
                    details={'changes': changes},
                    suggested_action='Verify all IAM changes match approved requests'
                )
            else:
                self._log_check_end('IAM', 'INFO')
                return CheckResult.info(
                    'IAM Check',
                    f'No IAM permission changes detected ({len(current_users)} users)'
                )

        except Exception as e:
            self._log_error('IAM', e)
            return CheckResult.error(
                'IAM Check Failed',
                f'Failed to check IAM: {str(e)}'
            )

    def _get_iam_users(self) -> Dict[str, Dict[str, Any]]:
        """Get all IAM users."""
        if not self.iam:
            return {}

        users = {}
        try:
            paginator = self.iam.get_paginator('list_users')
            for page in paginator.paginate():
                for user in page.get('Users', []):
                    users[user['UserName']] = {
                        'arn': user['Arn'],
                        'create_date': user['CreateDate'].isoformat(),
                        'path': user.get('Path', '/')
                    }
        except Exception as e:
            logger.warning(f"Error fetching IAM users: {str(e)}")

        return users

    def _get_access_keys(self, users: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Get access keys for each user."""
        if not self.iam:
            return {}

        keys = {}
        try:
            for username in users.keys():
                user_keys = []
                paginator = self.iam.get_paginator('list_access_keys')
                for page in paginator.paginate(UserName=username):
                    for key in page.get('AccessKeyMetadata', []):
                        user_keys.append({
                            'key_id': key['AccessKeyId'],
                            'status': key['Status'],
                            'create_date': key['CreateDate'].isoformat()
                        })
                keys[username] = user_keys
        except Exception as e:
            logger.warning(f"Error fetching IAM access keys: {str(e)}")

        return keys

    def _get_baseline(self) -> Dict[str, Any]:
        """Get baseline IAM state from DynamoDB."""
        if not self.dynamodb:
            return {'users': {}, 'keys': {}}

        try:
            response = self.dynamodb.get_item(
                TableName='guardian-iam-baseline',
                Key={'baseline_id': {'S': self.baseline_key}}
            )
            if 'Item' in response:
                import json
                item = response['Item']
                return {
                    'users': json.loads(item.get('users', {}).get('S', '{}')),
                    'keys': json.loads(item.get('keys', {}).get('S', '{}'))
                }
        except Exception as e:
            logger.warning(f"Error fetching IAM baseline: {str(e)}")

        return {'users': {}, 'keys': {}}

    def _detect_changes(
        self,
        current_users: Dict[str, Dict[str, Any]],
        current_keys: Dict[str, List[Dict[str, str]]],
        baseline: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Detect IAM changes."""
        changes = []

        baseline_users = set(baseline.get('users', {}).keys())
        current_user_set = set(current_users.keys())

        # New users
        for username in current_user_set - baseline_users:
            changes.append({
                'type': 'NEW_USER',
                'detail': f'User {username} created',
                'severity': 'HIGH'
            })

        # Deleted users
        for username in baseline_users - current_user_set:
            changes.append({
                'type': 'DELETED_USER',
                'detail': f'User {username} deleted',
                'severity': 'MEDIUM'
            })

        # New access keys
        baseline_keys = baseline.get('keys', {})
        for username in current_keys:
            current_key_ids = {k['key_id'] for k in current_keys[username]}
            baseline_key_ids = {
                k['key_id'] for k in baseline_keys.get(username, [])
            }

            for key_id in current_key_ids - baseline_key_ids:
                changes.append({
                    'type': 'NEW_ACCESS_KEY',
                    'detail': f'New access key {key_id[:4]}... created for {username}',
                    'severity': 'MEDIUM'
                })

        return changes

    def _determine_severity(self, changes: List[Dict[str, str]]) -> str:
        """Determine overall severity."""
        high_severity_count = sum(1 for c in changes if c['severity'] == 'HIGH')

        if high_severity_count >= 2:
            return 'HIGH'
        elif high_severity_count == 1:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _save_baseline(
        self,
        users: Dict[str, Dict[str, Any]],
        keys: Dict[str, List[Dict[str, str]]]
    ):
        """Save current state as baseline to DynamoDB."""
        if not self.dynamodb:
            return

        try:
            import json
            self.dynamodb.put_item(
                TableName='guardian-iam-baseline',
                Item={
                    'baseline_id': {'S': self.baseline_key},
                    'users': {'S': json.dumps(users)},
                    'keys': {'S': json.dumps(keys)},
                    'timestamp': {'S': datetime.now(timezone.utc).isoformat()}
                }
            )
        except Exception as e:
            logger.warning(f"Error saving IAM baseline: {str(e)}")
