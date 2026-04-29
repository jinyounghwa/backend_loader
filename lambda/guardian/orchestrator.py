"""Guardian Orchestrator - Coordinates check execution and remediation flow"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from logging import Logger

from guardian.checkers.cost import CostChecker
from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.s3 import S3Checker
from guardian.checkers.cloudtrail import CloudTrailChecker
from guardian.checkers.iam import IAMChecker
from guardian.checkers.guardduty import GuardDutyChecker
from guardian.responders.telegram import TelegramResponder
from guardian.responders.discord import DiscordResponder
from guardian.responders.remediation_service import AutoRemediationResponder
from guardian.storage.dynamodb import DynamoDBStorage
from guardian.config import Config
from guardian.logging_config import log_check_result, log_remediation


class GuardianOrchestrator:
    """
    Orchestrates the execution of all AWS Guardian checks and coordinated responses.
    Manages the flow: checks -> evaluation -> remediation -> notifications -> storage.
    """

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
    ):
        """
        Initialize the orchestrator with required components.

        Args:
            logger: Configured logger instance
            cost_checker: Cost anomaly checker
            ec2_checker: EC2 security checker
            s3_checker: S3 security checker
            storage: DynamoDB storage for event persistence
            telegram_responder: Optional Telegram notification responder
            discord_responder: Optional Discord notification responder
            remediation_responder: Optional auto-remediation responder
            cloudtrail_checker: Optional CloudTrail checker (Sprint 6)
            iam_checker: Optional IAM checker (Sprint 6)
            guardduty_checker: Optional GuardDuty checker (Sprint 6)
        """
        self.logger = logger
        self.cost_checker = cost_checker
        self.ec2_checker = ec2_checker
        self.s3_checker = s3_checker
        self.storage = storage
        self.telegram = telegram_responder
        self.discord = discord_responder
        self.remediation = remediation_responder
        self.is_localstack = Config.is_localstack()

        # Registry pattern: all checkers in a dict for scalability
        self.checkers = {
            'cost': cost_checker,
            'ec2': ec2_checker,
            's3': s3_checker,
            'cloudtrail': cloudtrail_checker,
            'iam': iam_checker,
            'guardduty': guardduty_checker,
        }

    def run_all_checks(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute AWS Guardian checks based on check_type parameter.

        Args:
            event: Lambda event object. Supports 'check_type' parameter:
                   - "security": Run EC2 + S3 + CloudTrail + IAM + GuardDuty checks
                   - "cost": Run cost check only
                   - "all" or omitted: Run all checks (backward compatibility)

        Returns:
            Aggregated results dictionary
        """
        check_type = event.get('check_type', 'all').lower()
        self.logger.info("AWS Guardian orchestration started (check_type=%s)", check_type)

        results = {
            'timestamp': event.get('time', datetime.now(timezone.utc).isoformat()),
            'status': 'success',
            'checks': {},
            'check_type': check_type
        }

        # Determine which checks to run
        checks_to_run = self._get_checks_for_type(check_type)

        # Execute all relevant checks
        all_check_data = {}
        for check_name in checks_to_run:
            if check_name in self.checkers and self.checkers[check_name]:
                try:
                    if check_name in ('cost', 'ec2', 's3'):
                        # Legacy checkers: return (anomaly, data) tuple
                        check_data = self._run_legacy_check(check_name, results)
                    else:
                        # New checkers (Sprint 6): return CheckResult object
                        check_data = self._run_new_check(check_name, results)
                    all_check_data[check_name] = check_data
                except Exception as e:
                    self.logger.error("Error running %s check: %s", check_name, e)
                    results['checks'][check_name] = {'error': f'{check_name}_check_failed'}

        # Determine system health (legacy method - will be enhanced later)
        system_health = self._determine_system_health(
            all_check_data.get('cost', {}),
            all_check_data.get('ec2', {}),
            all_check_data.get('s3', {})
        )

        # Save comprehensive check results
        self._save_check_results(all_check_data, system_health)

        # Send summary
        self._send_summary()

        self.logger.info("AWS Guardian orchestration completed. Health: %s", system_health)
        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }

    def _get_checks_for_type(self, check_type: str) -> List[str]:
        """Determine which checks to run based on check_type."""
        if check_type == 'cost':
            return ['cost']
        elif check_type == 'security':
            return ['ec2', 's3', 'cloudtrail', 'iam', 'guardduty']
        else:  # 'all'
            return ['cost', 'ec2', 's3', 'cloudtrail', 'iam', 'guardduty']

    def _run_legacy_check(self, check_name: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Run legacy checkers (cost, ec2, s3) that return (anomaly, data) tuple."""
        if check_name == 'cost':
            return self._run_cost_check(results)
        elif check_name == 'ec2':
            return self._run_ec2_check(results)
        elif check_name == 's3':
            return self._run_s3_check(results)
        return {}

    def _run_new_check(self, check_name: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Run new checkers (Sprint 6) that return CheckResult object."""
        self.logger.info(f"Checking {check_name.upper()}...")
        checker = self.checkers.get(check_name)
        if not checker:
            return {}

        try:
            check_result = checker.check()
            result_dict = check_result.to_dict()
            results['checks'][check_name] = result_dict

            # Log and notify if not INFO
            if check_result.severity != 'INFO':
                log_check_result(self.logger, check_name, check_result.severity, check_result.message)
                self.storage.save_event(check_name, check_result.severity, result_dict)
                self._notify_new_alert(check_name, result_dict)

            return result_dict

        except Exception as e:
            self.logger.error(f"Error running {check_name} check: {e}")
            results['checks'][check_name] = {'error': f'{check_name}_check_failed'}
            return {}

    def _notify_new_alert(self, check_name: str, alert_data: Dict[str, Any]):
        """Send notifications for Sprint 6 checkers."""
        if self.telegram:
            # New method in TelegramResponder to handle all check types
            self.telegram.send_alert(check_name, alert_data)

    def _run_cost_check(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute cost anomaly check."""
        self.logger.info("Checking AWS costs...")
        try:
            cost_anomaly, cost_data = self.cost_checker.check_cost_anomaly()
            results['checks']['cost'] = cost_data

            if cost_anomaly:
                log_check_result(self.logger, 'cost', 'warning', f"Anomaly: ${cost_data['today_cost']:.2f}")
                self.storage.save_event('cost', 'warning', cost_data)
                self._notify_cost_alert(cost_data)
            else:
                log_check_result(self.logger, 'cost', 'ok', f"Cost: ${cost_data['today_cost']:.2f}")

            return cost_data

        except Exception as e:
            self.logger.error("Error checking costs: %s", e)
            results['checks']['cost'] = {'error': 'cost_check_failed'}
            return {}

    def _run_ec2_check(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute EC2 security check."""
        self.logger.info("Checking EC2 instances...")
        try:
            ec2_anomaly, ec2_data = self.ec2_checker.check_ec2_anomalies()
            results['checks']['ec2'] = ec2_data

            if ec2_anomaly:
                log_check_result(self.logger, 'ec2', 'warning', f"Issues: {len(ec2_data.get('anomalies', []))}")
                self.storage.save_event('ec2', 'critical', ec2_data)
                self._notify_ec2_alert(ec2_data)

                # Auto-remediate exposed instances
                if self.remediation:
                    self.remediation.handle_exposed_instances(ec2_data)
            else:
                log_check_result(self.logger, 'ec2', 'ok', 'All instances secure')

            return ec2_data

        except Exception as e:
            self.logger.error("Error checking EC2: %s", e)
            results['checks']['ec2'] = {'error': 'ec2_check_failed'}
            return {}

    def _run_s3_check(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute S3 security check."""
        self.logger.info("Checking S3 buckets...")
        try:
            s3_anomaly, s3_data = self.s3_checker.check_s3_anomalies()
            results['checks']['s3'] = s3_data

            if s3_anomaly:
                log_check_result(self.logger, 's3', 'warning', f"Issues: {len(s3_data.get('anomalies', []))}")
                self.storage.save_event('s3', 'critical', s3_data)
                self._notify_s3_alert(s3_data)

                # Auto-remediate public buckets
                if self.remediation:
                    self.remediation.handle_public_buckets(s3_data)
            else:
                log_check_result(self.logger, 's3', 'ok', 'All buckets secure')

            return s3_data

        except Exception as e:
            self.logger.error("Error checking S3: %s", e)
            results['checks']['s3'] = {'error': 's3_check_failed'}
            return {}

    def _determine_system_health(self, cost_data: Dict, ec2_data: Dict, s3_data: Dict) -> str:
        """Determine overall system health based on check results."""
        has_critical = (
            cost_data.get('is_anomaly', False)
            or len(ec2_data.get('anomalies', [])) > 0
            or len(s3_data.get('public_buckets', [])) > 0
        )
        has_warning = (
            len(ec2_data.get('new_instances', [])) > 0
            or len(s3_data.get('new_buckets', [])) > 0
        )
        return 'critical' if has_critical else 'warning' if has_warning else 'healthy'

    def _notify_cost_alert(self, cost_data: Dict[str, Any]):
        """Send cost alert notifications."""
        if self.telegram:
            self.telegram.send_cost_alert(cost_data)
        if self.discord:
            self.discord.send_cost_alert(cost_data)

    def _notify_ec2_alert(self, ec2_data: Dict[str, Any]):
        """Send EC2 alert notifications."""
        if self.telegram:
            self.telegram.send_ec2_alert(ec2_data)
        if self.discord:
            self.discord.send_ec2_alert(ec2_data)

    def _notify_s3_alert(self, s3_data: Dict[str, Any]):
        """Send S3 alert notifications."""
        if self.telegram:
            self.telegram.send_s3_alert(s3_data)
        if self.discord:
            self.discord.send_s3_alert(s3_data)

    def _save_check_results(self, all_check_data: Dict[str, Any], system_health: str):
        """Save comprehensive check results to storage."""
        try:
            check_details = {
                **all_check_data,
                'last_check': datetime.now(timezone.utc).isoformat(),
                'system_health': system_health,
            }
            self.storage.save_event('check_result', 'info', check_details)
            self.logger.info("Check result saved. Health: %s", system_health)
        except Exception as e:
            self.logger.warning("Could not save check result: %s", e)

    def _send_summary(self):
        """Send 24-hour event summary."""
        try:
            summary = self.storage.get_event_summary(hours=24)

            if summary.get('total_events', 0) > 0:
                if self.telegram:
                    self.telegram.send_summary(summary)
                if self.discord:
                    self.discord.send_summary_embed(summary)

            self.storage.save_event('summary', 'info', summary)
            self.logger.info("Summary sent. Total events: %d", summary.get('total_events', 0))

        except Exception as e:
            self.logger.warning("Could not send summary: %s", e)
