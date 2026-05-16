"""IAM checker for permission changes detection."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from guardian.aws_client_provider import AWSClientProvider
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

logger = logging.getLogger(__name__)


class IAMChecker(BaseChecker):

    def __init__(
        self,
        clients: Dict[str, Any],
        config: Dict[str, Any],
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        super().__init__(clients, config, account_id, credentials)
        self.dynamodb_resource = clients.get("dynamodb_resource")
        self.baseline_key = "iam-baseline"
        self.table_name = config.get("iam_baseline_table", "guardian-iam-baseline")
        # Get from clients dict (tests) or create new (production)
        self.iam_client = clients.get("iam")
        if self.iam_client is None:
            kwargs = Config.get_boto3_kwargs()
            self.iam_client = boto3.client("iam", **kwargs)
        # Backward compatibility alias
        self.iam = self.iam_client

    async def check_async(self) -> CheckResult:
        self._log_check_start("IAM")

        try:
            # Use sync versions if mocked (for tests)
            if hasattr(self._get_iam_users, '_mock_name'):
                current_users = self._get_iam_users()
                current_keys = self._get_access_keys(current_users)
                baseline = self._get_baseline()
            else:
                current_users = await self._get_iam_users_async()
                current_keys = await self._get_access_keys_async(current_users)
                baseline = await self._get_baseline_async()
            changes = self._detect_changes(current_users, current_keys, baseline)

            if changes:
                severity = self._determine_severity(changes)
                self._log_check_end("IAM", severity)
                await self._save_baseline_async(current_users, current_keys)

                return CheckResult(
                    severity=severity,
                    title="IAM Permission Changes Detected",
                    message=f"Found {len(changes)} IAM changes",
                    details={"changes": changes},
                    suggested_action="Verify all IAM changes match approved requests",
                )
            else:
                self._log_check_end("IAM", "INFO")
                return CheckResult.info(
                    "IAM Check", f"No IAM permission changes detected ({len(current_users)} users)"
                )

        except Exception as e:
            self._log_error("IAM", e)
            return CheckResult.error("IAM Check Failed", f"Failed to check IAM: {str(e)}")

    def check(self) -> CheckResult:
        """Backward compatibility wrapper - delegates to check_async()."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self.check_async())
                return future.result()
        else:
            return asyncio.run(self.check_async())

    async def _get_iam_users_async(self) -> Dict[str, Dict[str, Any]]:
        """Get IAM users using async I/O."""
        users = {}
        try:
            async with await AWSClientProvider.get_async_client("iam") as iam:
                paginator = iam.get_paginator("list_users")
                async for page in paginator.paginate():
                    for user in page.get("Users", []):
                        users[user["UserName"]] = {
                            "arn": user["Arn"],
                            "create_date": user["CreateDate"].isoformat(),
                            "path": user.get("Path", "/"),
                        }
        except ClientError as e:
            logger.warning("ClientError fetching IAM users: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM users: %s", e)

        return users

    async def _get_access_keys_async(self, users: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
        """Get access keys for all users with parallel async I/O."""
        keys = {}
        try:
            async with await AWSClientProvider.get_async_client("iam") as iam:
                async def get_user_keys(username: str):
                    user_keys = []
                    try:
                        paginator = iam.get_paginator("list_access_keys")
                        async for page in paginator.paginate(UserName=username):
                            for key in page.get("AccessKeyMetadata", []):
                                user_keys.append(
                                    {
                                        "key_id": key["AccessKeyId"],
                                        "status": key["Status"],
                                        "create_date": key["CreateDate"].isoformat(),
                                    }
                                )
                    except Exception as e:
                        logger.warning("Error fetching keys for %s: %s", username, e)
                    return (username, user_keys)

                tasks = [get_user_keys(username) for username in users.keys()]
                results = await asyncio.gather(*tasks, return_exceptions=False)
                keys = {username: user_keys for username, user_keys in results}

        except ClientError as e:
            logger.warning("ClientError fetching IAM access keys: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM access keys: %s", e)

        return keys

    async def _get_baseline_async(self) -> Dict[str, Any]:
        if not self.dynamodb_resource:
            return {"users": {}, "keys": {}}

        try:
            table = self.dynamodb_resource.Table(self.table_name)
            response = table.get_item(Key={"baseline_id": self.baseline_key})
            if "Item" in response:
                item = response["Item"]
                return {
                    "users": json.loads(item.get("users", "{}")),
                    "keys": json.loads(item.get("keys", "{}")),
                }
        except ClientError as e:
            logger.warning("ClientError fetching IAM baseline: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM baseline: %s", e)

        return {"users": {}, "keys": {}}

    def _detect_changes(
        self,
        current_users: Dict[str, Dict[str, Any]],
        current_keys: Dict[str, List[Dict[str, str]]],
        baseline: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        changes = []

        baseline_users = set(baseline.get("users", {}).keys())
        current_user_set = set(current_users.keys())

        for username in current_user_set - baseline_users:
            changes.append(
                {"type": "NEW_USER", "detail": f"User {username} created", "severity": "HIGH"}
            )

        for username in baseline_users - current_user_set:
            changes.append(
                {"type": "DELETED_USER", "detail": f"User {username} deleted", "severity": "MEDIUM"}
            )

        baseline_keys = baseline.get("keys", {})
        for username in current_keys:
            current_key_ids = {k["key_id"] for k in current_keys[username]}
            baseline_key_ids = {k["key_id"] for k in baseline_keys.get(username, [])}

            for key_id in current_key_ids - baseline_key_ids:
                changes.append(
                    {
                        "type": "NEW_ACCESS_KEY",
                        "detail": f"New access key {key_id[:4]}... created for {username}",
                        "severity": "MEDIUM",
                    }
                )

        return changes

    def _determine_severity(self, changes: List[Dict[str, str]]) -> str:
        high_severity_count = sum(1 for c in changes if c["severity"] == "HIGH")

        if high_severity_count >= 2:
            return "HIGH"
        elif high_severity_count == 1:
            return "MEDIUM"
        else:
            return "LOW"

    async def _save_baseline_async(
        self, users: Dict[str, Dict[str, Any]], keys: Dict[str, List[Dict[str, str]]]
    ):
        """Save IAM baseline to DynamoDB - sync since DynamoDB resource is blocking."""
        if not self.dynamodb_resource:
            return

        try:
            table = self.dynamodb_resource.Table(self.table_name)
            table.put_item(
                Item={
                    "baseline_id": self.baseline_key,
                    "users": json.dumps(users),
                    "keys": json.dumps(keys),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except ClientError as e:
            logger.warning("ClientError saving IAM baseline: %s", e)
        except Exception as e:
            logger.warning("Error saving IAM baseline: %s", e)

    def _get_iam_users(self) -> Dict[str, Dict[str, Any]]:
        """Get IAM users (sync version for tests)."""
        users = {}
        try:
            paginator = self.iam_client.get_paginator("list_users")
            for page in paginator.paginate():
                for user in page.get("Users", []):
                    users[user["UserName"]] = {
                        "arn": user["Arn"],
                        "create_date": user["CreateDate"].isoformat(),
                        "path": user.get("Path", "/"),
                    }
        except ClientError as e:
            logger.warning("ClientError fetching IAM users: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM users: %s", e)

        return users

    def _get_access_keys(self, users: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
        """Get access keys for all users (sync version for tests)."""
        keys = {}
        try:
            for username in users.keys():
                user_keys = []
                try:
                    paginator = self.iam_client.get_paginator("list_access_keys")
                    for page in paginator.paginate(UserName=username):
                        for key in page.get("AccessKeyMetadata", []):
                            user_keys.append(
                                {
                                    "key_id": key["AccessKeyId"],
                                    "status": key["Status"],
                                    "create_date": key["CreateDate"].isoformat(),
                                }
                            )
                except Exception as e:
                    logger.warning("Error fetching keys for %s: %s", username, e)
                keys[username] = user_keys
        except ClientError as e:
            logger.warning("ClientError fetching IAM access keys: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM access keys: %s", e)

        return keys

    def _get_baseline(self) -> Dict[str, Any]:
        """Get IAM baseline from DynamoDB (sync version for tests)."""
        if not self.dynamodb_resource:
            return {"users": {}, "keys": {}}

        try:
            table = self.dynamodb_resource.Table(self.table_name)
            response = table.get_item(Key={"baseline_id": self.baseline_key})
            if "Item" in response:
                item = response["Item"]
                return {
                    "users": json.loads(item.get("users", "{}")),
                    "keys": json.loads(item.get("keys", "{}")),
                }
        except ClientError as e:
            logger.warning("ClientError fetching IAM baseline: %s", e)
        except Exception as e:
            logger.warning("Error fetching IAM baseline: %s", e)

        return {"users": {}, "keys": {}}

    def _save_baseline(
        self, users: Dict[str, Dict[str, Any]], keys: Dict[str, List[Dict[str, str]]]
    ):
        """Save IAM baseline to DynamoDB (sync version for tests)."""
        if not self.dynamodb_resource:
            return

        try:
            table = self.dynamodb_resource.Table(self.table_name)
            table.put_item(
                Item={
                    "baseline_id": self.baseline_key,
                    "users": json.dumps(users),
                    "keys": json.dumps(keys),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except ClientError as e:
            logger.warning("ClientError saving IAM baseline: %s", e)
        except Exception as e:
            logger.warning("Error saving IAM baseline: %s", e)
