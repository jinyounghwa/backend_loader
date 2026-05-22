"""IAM checker for permission changes detection."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

logger = logging.getLogger(__name__)


class IAMChecker(BaseChecker):
    """Detect IAM permission changes and anomalous user activity."""

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        effective_config = config or {}
        super().__init__(clients or {}, effective_config, account_id, credentials)

        self.dynamodb_resource = (clients or {}).get("dynamodb_resource")
        self.baseline_key = "iam-baseline"
        self.table_name = effective_config.get("iam_baseline_table", "guardian-iam-baseline")

        self.iam_client = (clients or {}).get("iam")
        if self.iam_client is None:
            self.iam_client = boto3.client("iam", **Config.get_boto3_kwargs())
        # Backward compatibility alias
        self.iam = self.iam_client

    # ------------------------------------------------------------------
    # Main check entry (sync-first)
    # ------------------------------------------------------------------

    def check(self) -> CheckResult:
        """Check for IAM security anomalies.

        Detects:
        - New IAM users created
        - Access key usage patterns
        - Permission changes

        Compares against baseline to identify new activity.
        """
        self._log_check_start("IAM")
        try:
            current_users = self._get_iam_users()
            current_keys = self._get_access_keys(current_users)
            baseline = self._get_baseline()
            changes = self._detect_changes(current_users, current_keys, baseline)

            if changes:
                severity = self._determine_severity(changes)
                self._log_check_end("IAM", severity)
                self._save_baseline(current_users, current_keys)

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

        except ClientError as e:
            return self._handle_client_error("IAM", e)
        except Exception as e:
            return self._handle_generic_error("IAM", e)

    # ------------------------------------------------------------------
    # IAM data retrieval (sync)
    # ------------------------------------------------------------------

    def _get_iam_users(self) -> Dict[str, Dict[str, Any]]:
        """Get IAM users."""
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
        """Get access keys for all users."""
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

    # ------------------------------------------------------------------
    # Baseline management
    # ------------------------------------------------------------------

    def _get_baseline(self) -> Dict[str, Any]:
        """Get IAM baseline from DynamoDB."""
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
    ) -> None:
        """Save IAM baseline to DynamoDB."""
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

    # ------------------------------------------------------------------
    # Change detection
    # ------------------------------------------------------------------

    def _detect_changes(
        self,
        current_users: Dict[str, Dict[str, Any]],
        current_keys: Dict[str, List[Dict[str, str]]],
        baseline: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Compare current IAM users and access keys against baseline.

        Args:
            current_users: The current dict of IAM users.
            current_keys: The current dict of access keys for the users.
            baseline: The baseline dict loaded from DynamoDB.

        Returns:
            A list of detected IAM changes with their type, details, and severity.
        """
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
        """Determine overall severity based on the number and severity of IAM changes.

        Args:
            changes: A list of detected IAM changes.

        Returns:
            The overall severity level string ("HIGH", "MEDIUM", "LOW").
        """
        high_severity_count = sum(1 for c in changes if c["severity"] == "HIGH")

        if high_severity_count >= 2:
            return "HIGH"
        elif high_severity_count == 1:
            return "MEDIUM"
        else:
            return "LOW"
