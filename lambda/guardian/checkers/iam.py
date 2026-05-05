"""IAM checker for permission changes detection."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from guardian.checkers.base import BaseChecker, CheckResult
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class IAMChecker(BaseChecker):

    def __init__(self, clients: Dict[str, Any], config: Dict[str, Any],
                 account_id: Optional[str] = None, credentials: Optional[Dict[str, str]] = None):
        super().__init__(clients, config, account_id, credentials)
        self.iam = clients.get('iam')
        self.dynamodb_resource = clients.get('dynamodb_resource')
        self.baseline_key = 'iam-baseline'
        self.table_name = config.get('iam_baseline_table', 'guardian-iam-baseline')

    def check(self) -> CheckResult:
        self._log_check_start('IAM')

        try:
            current_users = self._get_iam_users()
            current_keys = self._get_access_keys(current_users)
            baseline = self._get_baseline()
            changes = self._detect_changes(current_users, current_keys, baseline)

            if changes:
                severity = self._determine_severity(changes)
                self._log_check_end('IAM', severity)
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
        except ClientError as e:
            logger.warning("ClientError fetching IAM users: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM users: %s", e)

        return users

    def _get_access_keys(self, users: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
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
        except ClientError as e:
            logger.warning("ClientError fetching IAM access keys: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM access keys: %s", e)

        return keys

    def _get_baseline(self) -> Dict[str, Any]:
        if not self.dynamodb_resource:
            return {'users': {}, 'keys': {}}

        try:
            table = self.dynamodb_resource.Table(self.table_name)
            response = table.get_item(
                Key={'baseline_id': self.baseline_key}
            )
            if 'Item' in response:
                item = response['Item']
                return {
                    'users': json.loads(item.get('users', '{}')),
                    'keys': json.loads(item.get('keys', '{}'))
                }
        except ClientError as e:
            logger.warning("ClientError fetching IAM baseline: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM baseline: %s", e)

        return {'users': {}, 'keys': {}}

    def _detect_changes(
        self,
        current_users: Dict[str, Dict[str, Any]],
        current_keys: Dict[str, List[Dict[str, str]]],
        baseline: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        changes = []

        baseline_users = set(baseline.get('users', {}).keys())
        current_user_set = set(current_users.keys())

        for username in current_user_set - baseline_users:
            changes.append({
                'type': 'NEW_USER',
                'detail': f'User {username} created',
                'severity': 'HIGH'
            })

        for username in baseline_users - current_user_set:
            changes.append({
                'type': 'DELETED_USER',
                'detail': f'User {username} deleted',
                'severity': 'MEDIUM'
            })

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
        if not self.dynamodb_resource:
            return

        try:
            table = self.dynamodb_resource.Table(self.table_name)
            table.put_item(Item={
                'baseline_id': self.baseline_key,
                'users': json.dumps(users),
                'keys': json.dumps(keys),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        except ClientError as e:
            logger.warning("ClientError saving IAM baseline: %s", e)
        except Exception as e:
            logger.warning("Error saving IAM baseline: %s", e)
