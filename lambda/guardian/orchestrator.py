"""Guardian Orchestrator - Coordinates check execution and remediation flow.

All checkers are now sync-first. The orchestrator runs checks
sequentially (simple, reliable) and dispatches notifications/remediation.
Async parallel execution can be achieved via the base class's
``check_async()`` wrapper (which uses ``run_in_executor``).
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from logging import Logger
from typing import Any, Dict, List, Optional

from guardian.aws_client_provider import AWSClientProvider
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.checkers.cloudtrail import CloudTrailChecker
from guardian.checkers.cost import CostChecker
from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.guardduty import GuardDutyChecker
from guardian.checkers.iam import IAMChecker
from guardian.checkers.iam_policy_analyzer import IAMPolicyAnalyzer
from guardian.checkers.rds import RDSChecker
from guardian.checkers.s3 import S3Checker
from guardian.config import Config
from guardian.handlers.metrics import CloudWatchMetrics
from guardian.logging_config import log_check_result
from guardian.responders.discord import DiscordResponder
from guardian.responders.remediation_service import AutoRemediationResponder
from guardian.responders.telegram import TelegramResponder
from guardian.storage.dynamodb import DynamoDBStorage


class GuardianOrchestrator:
    """Orchestrate all AWS Guardian checks through a unified CheckResult pipeline."""

    def __init__(
        self,
        logger: Logger,
        cost_checker: CostChecker,
        ec2_checker: EC2Checker,
        s3_checker: S3Checker,
        storage: DynamoDBStorage,
        telegram_responder: Optional[TelegramResponder] = None,
        discord_responder: Optional[DiscordResponder] = None,
        remediation_responder: Optional[AutoRemediationResponder] = None,
        cloudtrail_checker: Optional[CloudTrailChecker] = None,
        iam_checker: Optional[IAMChecker] = None,
        guardduty_checker: Optional[GuardDutyChecker] = None,
        rds_checker: Optional[RDSChecker] = None,
        iam_policy_analyzer: Optional[IAMPolicyAnalyzer] = None,
    ):
        self.logger = logger
        self.storage = storage
        self.telegram = telegram_responder
        self.discord = discord_responder
        self.remediation = remediation_responder
        self.is_localstack = Config.is_localstack()

        self.checkers: Dict[str, Optional[BaseChecker]] = {
            "cost": cost_checker,
            "ec2": ec2_checker,
            "s3": s3_checker,
            "cloudtrail": cloudtrail_checker,
            "iam": iam_checker,
            "guardduty": guardduty_checker,
            "rds": rds_checker,
            "iam_policy_analyzer": iam_policy_analyzer,
        }

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    def run_all_checks(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Execute checks based on event['check_type'] and return aggregated results.

        Runs synchronously — checkers are all sync-first.
        """
        start_time = time.time()
        check_type = event.get("check_type", "all").lower()
        self.logger.info("AWS Guardian orchestration started (check_type=%s)", check_type)

        results: Dict[str, Any] = {
            "timestamp": event.get("time", datetime.now(timezone.utc).isoformat()),
            "status": "success",
            "checks": {},
            "check_type": check_type,
            "accounts": [],
        }

        accounts = self._get_accounts()
        checks_to_run = self._get_checks_for_type(check_type)

        all_check_data: Dict[str, Any] = {}
        for account in accounts:
            account_id = account["account_id"]
            account_name = account.get("account_name", account_id)
            self.logger.info("Running checks for account: %s (%s)", account_name, account_id)

            account_checkers = self.checkers
            if Config.is_organizations_enabled() and account_id != "current":
                assumed_role = self._assume_role_for_account(account_id)
                if not assumed_role:
                    self.logger.warning("Skipping account %s - role assumption failed", account_id)
                    continue
                account_checkers = self._create_account_checkers(
                    account_id, assumed_role.get("credentials", {})
                )

            account_check_data: Dict[str, Any] = {}
            for check_name in checks_to_run:
                checker = account_checkers.get(check_name)
                if not checker:
                    continue
                try:
                    check_result = checker.check()
                    result_dict = check_result.to_dict()

                    if check_result.severity != "INFO":
                        log_check_result(
                            self.logger, check_name, check_result.severity, check_result.message
                        )
                        self.storage.save_event(
                            check_name, check_result.severity, result_dict, account_id=account_id
                        )
                        self._notify_alert(
                            check_name,
                            result_dict,
                            account_id=account_id,
                            account_name=account_name,
                        )
                        if self.remediation:
                            self.remediation.handle_check_result(check_name, check_result)
                    else:
                        log_check_result(self.logger, check_name, "ok", check_result.message)

                    account_check_data[check_name] = result_dict
                    results["checks"][f"{check_name}_{account_id}"] = result_dict
                except Exception as exc:
                    self.logger.error("Error in check %s: %s", check_name, exc)
                    results["checks"][f"{check_name}_{account_id}"] = {
                        "error": f"{check_name}_check_failed"
                    }

            all_check_data[account_id] = {
                "account_id": account_id,
                "account_name": account_name,
                "checks": account_check_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results["accounts"].append(all_check_data[account_id])

        first_account_data = list(all_check_data.values())[0] if all_check_data else {}
        checks = first_account_data.get("checks", {})
        system_health = self._determine_system_health(checks)

        self._save_check_results(all_check_data, system_health)
        self._send_summary()

        elapsed_ms = (time.time() - start_time) * 1000
        try:
            CloudWatchMetrics.emit_batch(
                {
                    "Duration": elapsed_ms,
                    "EventsProcessed": len(results.get("accounts", [])),
                    "ErrorCount": sum(
                        1
                        for v in results.get("checks", {}).values()
                        if isinstance(v, dict) and "error" in v
                    ),
                }
            )
        except Exception as metrics_err:
            self.logger.warning("Failed to emit CloudWatch metrics: %s", metrics_err)

        self.logger.info(
            "AWS Guardian orchestration completed. Health: %s. Accounts: %d",
            system_health,
            len(all_check_data),
        )
        return {"statusCode": 200, "body": json.dumps(results)}

    # ------------------------------------------------------------------
    # Async entry point (for backward compat / parallel execution)
    # ------------------------------------------------------------------

    async def run_all_checks_async(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper that runs ``run_all_checks`` in a thread executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.run_all_checks, event)

    # ------------------------------------------------------------------
    # Account management
    # ------------------------------------------------------------------

    def _get_accounts(self) -> List[Dict[str, str]]:
        """Get list of AWS accounts to check."""
        if not Config.is_organizations_enabled():
            return [{"account_id": "current", "account_name": "Current Account"}]

        try:
            orgs = AWSClientProvider.get_client("organizations")
            paginator = orgs.get_paginator("list_accounts")
            accounts = []
            for page in paginator.paginate():
                for account in page.get("Accounts", []):
                    accounts.append(
                        {
                            "account_id": account["Id"],
                            "account_name": account["Name"],
                            "status": account["Status"],
                        }
                    )
            self.logger.info("Retrieved %d accounts from Organizations", len(accounts))
            return accounts
        except Exception as e:
            self.logger.warning("Failed to get accounts from Organizations: %s", e)
            return [{"account_id": "current", "account_name": "Current Account"}]

    def _assume_role_for_account(
        self, account_id: str, role_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            if not role_name:
                role_name = Config.get_cross_account_role_name()
            sts_client = AWSClientProvider.get_client("sts")
            assume_role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
            response = sts_client.assume_role(
                RoleArn=assume_role_arn,
                RoleSessionName=f"guardian-cross-account-{account_id}",
            )
            credentials = response["Credentials"]
            self.logger.info("Assumed role for account %s", account_id)
            return {
                "account_id": account_id,
                "credentials": {
                    "aws_access_key_id": credentials["AccessKeyId"],
                    "aws_secret_access_key": credentials["SecretAccessKey"],
                    "aws_session_token": credentials["SessionToken"],
                },
            }
        except Exception as e:
            self.logger.warning("Failed to assume role for account %s: %s", account_id, e)
            return None

    def _create_account_checkers(
        self, account_id: str, credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create account-specific checkers with cross-account credentials."""
        try:
            account_checkers = dict(self.checkers)

            if self.checkers.get("cloudtrail"):
                ct_clients = {
                    "cloudtrail": AWSClientProvider.get_client_for_account(
                        "cloudtrail", account_id, credentials
                    ),
                    "sts": AWSClientProvider.get_client_for_account("sts", account_id, credentials),
                }
                account_checkers["cloudtrail"] = CloudTrailChecker(
                    ct_clients, {}, account_id=account_id, credentials=credentials
                )

            if self.checkers.get("iam"):
                iam_clients = {
                    "iam": AWSClientProvider.get_client_for_account("iam", account_id, credentials),
                    "dynamodb_resource": AWSClientProvider.get_resource(
                        "dynamodb", region="us-east-1"
                    ),
                }
                account_checkers["iam"] = IAMChecker(
                    iam_clients, {}, account_id=account_id, credentials=credentials
                )

            if self.checkers.get("guardduty"):
                gd_clients = {
                    "guardduty": AWSClientProvider.get_client_for_account(
                        "guardduty", account_id, credentials
                    ),
                }
                account_checkers["guardduty"] = GuardDutyChecker(
                    gd_clients, {}, account_id=account_id, credentials=credentials
                )

            if self.checkers.get("rds"):
                rds_clients = {
                    "rds": AWSClientProvider.get_client_for_account("rds", account_id, credentials),
                }
                account_checkers["rds"] = RDSChecker(
                    rds_clients, {}, account_id=account_id, credentials=credentials
                )

            if self.checkers.get("iam_policy_analyzer"):
                iam_clients = {
                    "iam": AWSClientProvider.get_client_for_account("iam", account_id, credentials),
                }
                account_checkers["iam_policy_analyzer"] = IAMPolicyAnalyzer(
                    iam_clients, {}, account_id=account_id, credentials=credentials
                )

            self.logger.info("Created account-specific checkers for %s", account_id)
            return account_checkers
        except Exception as e:
            self.logger.error(
                "Failed to create account-specific checkers for %s: %s", account_id, e
            )
            return self.checkers

    # ------------------------------------------------------------------
    # Single check execution (public API for tests / external callers)
    # ------------------------------------------------------------------

    def _run_single_check(
        self,
        check_name: str,
        checker: BaseChecker,
        account_id: str = "current",
        account_name: Optional[str] = None,
    ) -> CheckResult:
        """Execute a single checker and process result."""
        self.logger.info("Checking %s...", check_name.upper())
        check_result = checker.check()

        result_dict = check_result.to_dict()
        if check_result.severity == "INFO":
            log_check_result(self.logger, check_name, "ok", check_result.message)
            return check_result

        log_check_result(self.logger, check_name, check_result.severity, check_result.message)
        self.storage.save_event(
            check_name, check_result.severity, result_dict, account_id=account_id
        )
        self._notify_alert(
            check_name,
            result_dict,
            account_id=account_id,
            account_name=account_name or "",
        )
        if self.remediation:
            self.remediation.handle_check_result(check_name, check_result)

        return check_result

    # ------------------------------------------------------------------
    # Check type routing
    # ------------------------------------------------------------------

    _ALL_CHECKS = [
        "cost",
        "ec2",
        "s3",
        "cloudtrail",
        "iam",
        "guardduty",
        "rds",
        "iam_policy_analyzer",
    ]
    _SECURITY_CHECKS = ["ec2", "s3", "cloudtrail", "iam", "guardduty", "rds", "iam_policy_analyzer"]

    def _get_checks_for_type(self, check_type: str) -> List[str]:
        """Map a check_type string to the list of checker names to execute."""
        return {
            "cost": ["cost"],
            "security": self._SECURITY_CHECKS,
        }.get(check_type, self._ALL_CHECKS)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _notify_alert(
        self,
        check_name: str,
        alert_data: Dict[str, Any],
        account_id: str = "current",
        account_name: Optional[str] = None,
    ):
        if self.telegram:
            self.telegram.send_alert(
                check_name,
                alert_data,
                account_id=account_id,
                account_name=account_name,
            )
        if self.discord:
            self.discord.send_alert(
                check_name,
                alert_data,
                account_id=account_id,
                account_name=account_name,
            )

    # ------------------------------------------------------------------
    # Health & persistence
    # ------------------------------------------------------------------

    def _determine_system_health(self, checks: Dict[str, Any]) -> str:
        """Determine system health from check results."""
        severity_priority = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
        max_severity = -1

        for check_data in checks.values():
            if not isinstance(check_data, dict):
                continue
            sev = check_data.get("severity", "")
            max_severity = max(max_severity, severity_priority.get(sev, -1))
            if check_data.get("is_anomaly"):
                max_severity = max(max_severity, 1)
            if check_data.get("new_instances") or check_data.get("new_buckets"):
                max_severity = max(max_severity, 0)

        if max_severity >= 2:
            return "critical"
        if max_severity >= 1:
            return "warning"
        return "healthy"

    def _save_check_results(self, all_check_data: Dict[str, Any], system_health: str):
        try:
            for account_id, account_data in all_check_data.items():
                check_details = {
                    **account_data.get("checks", {}),
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "system_health": system_health,
                }
                if account_data.get("account_name"):
                    check_details["account_name"] = account_data["account_name"]
                self.storage.save_event(
                    "check_result", "info", check_details, account_id=account_id
                )
            self.logger.info("Check results saved. Health: %s", system_health)
        except Exception as e:
            self.logger.warning("Could not save check result: %s", e)

    def _send_summary(self):
        try:
            summary = self.storage.get_event_summary(hours=24)
            if summary.get("total_events", 0) > 0:
                if self.telegram:
                    self.telegram.send_summary(summary)
                if self.discord:
                    self.discord.send_summary_embed(summary)
            self.storage.save_event("summary", "info", summary)
            self.logger.info("Summary sent. Total events: %d", summary.get("total_events", 0))
        except Exception as e:
            self.logger.warning("Could not send summary: %s", e)
