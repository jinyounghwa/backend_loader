"""Anomaly Detection Engine for Sprint 33 Phase 2

Detects security threats based on configurable rules and audit log patterns.
Evaluates rules against recent events and generates threat alerts.
Sprint 36: Integrated with deployment system - only ACTIVE rules are evaluated.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError


@dataclass
class Threat:
    """Represents a detected threat"""

    threat_id: str
    rule_id: str
    severity: int  # 1-10, higher = more severe
    account_id: Optional[str]
    timestamp: datetime
    message: str
    evidence: List[Dict[str, Any]]


class AnomalyDetector:
    """Detects anomalies in audit logs based on security rules (only ACTIVE deployed rules)"""

    def __init__(self, rules_table_name: str, audit_logs_table_name: str, deployments_table_name: Optional[str] = None):
        self.dynamodb = boto3.resource("dynamodb")
        self.rules_table = self.dynamodb.Table(rules_table_name)
        self.audit_logs_table = self.dynamodb.Table(audit_logs_table_name)
        self.deployments_table_name = deployments_table_name

    def detect_anomalies(
        self,
        account_id: Optional[str] = None,
        lookback_minutes: int = 60,
    ) -> List[Threat]:
        """
        Detect anomalies for account(s) using ACTIVE (deployed) rules.
        Only rules with ACTIVE deployment status are evaluated.
        Args:
            account_id: Specific account to check (None = all accounts)
            lookback_minutes: How far back to look in audit logs
        Returns:
            List of detected threats, sorted by severity
        """
        threats = []

        try:
            # Get enabled rules for this account
            rules = self._get_enabled_rules(account_id)

            # Evaluate each rule against recent logs
            for rule in rules:
                rule_threats = self._evaluate_rule(rule, account_id, lookback_minutes)
                threats.extend(rule_threats)

            # Sort by severity descending
            threats.sort(key=lambda t: t.severity, reverse=True)
            return threats

        except Exception as e:
            print(f"Error detecting anomalies: {e}")
            return []

    def _get_enabled_rules(self, account_id: Optional[str]) -> List[Dict[str, Any]]:
        """Get all ACTIVE (deployed) rules for an account"""
        try:
            # If deployments table is configured, filter by ACTIVE deployment status
            if self.deployments_table_name:
                try:
                    from guardian.storage.rule_deployment import RuleDeploymentRepository
                except ImportError:
                    from ..storage.rule_deployment import RuleDeploymentRepository

                # Get base enabled rules
                if account_id:
                    response = self.rules_table.query(
                        IndexName="AccountIdIndex",
                        KeyConditionExpression="account_id = :aid",
                        ExpressionAttributeValues={":aid": account_id},
                    )
                else:
                    response = self.rules_table.query(
                        IndexName="AccountIdIndex",
                        KeyConditionExpression="account_id = :aid",
                        ExpressionAttributeValues={":aid": "all"},
                    )

                rules = response.get("Items", [])
                enabled_rules = [rule for rule in rules if rule.get("enabled", True)]

                # Filter for ACTIVE deployments only
                deployment_repo = RuleDeploymentRepository(self.deployments_table_name)
                active_rules = []

                for rule in enabled_rules:
                    deployment = deployment_repo.get_active_deployment(rule["rule_id"])
                    if deployment and deployment.status == "ACTIVE":
                        active_rules.append(rule)

                return active_rules
            else:
                # Fallback: return enabled rules without deployment check (for backward compatibility)
                if account_id:
                    response = self.rules_table.query(
                        IndexName="AccountIdIndex",
                        KeyConditionExpression="account_id = :aid",
                        ExpressionAttributeValues={":aid": account_id},
                    )
                else:
                    response = self.rules_table.query(
                        IndexName="AccountIdIndex",
                        KeyConditionExpression="account_id = :aid",
                        ExpressionAttributeValues={":aid": "all"},
                    )

                rules = response.get("Items", [])
                return [rule for rule in rules if rule.get("enabled", True)]

        except ClientError as e:
            print(f"Error getting enabled rules: {e}")
            return []
        except Exception as e:
            print(f"Error checking deployment status: {e}")
            return []

    def _evaluate_rule(
        self,
        rule: Dict[str, Any],
        account_id: Optional[str],
        lookback_minutes: int,
    ) -> List[Threat]:
        """Evaluate a single rule against recent logs"""
        import json

        threats = []
        rule_type = rule.get("rule_type")

        try:
            # Get recent logs for this account
            recent_logs = self._get_recent_logs(account_id, lookback_minutes)

            # Evaluate based on rule type
            if rule_type == "connection_spike":
                threat = self._check_connection_spike(rule, account_id, recent_logs)
                if threat:
                    threats.append(threat)

            elif rule_type == "auth_failure":
                threat = self._check_auth_failure_rate(rule, account_id, recent_logs)
                if threat:
                    threats.append(threat)

            elif rule_type == "unknown_region":
                threat = self._check_unknown_region(rule, account_id, recent_logs)
                if threat:
                    threats.append(threat)

            elif rule_type == "public_bucket":
                threat = self._check_public_bucket(rule, account_id, recent_logs)
                if threat:
                    threats.append(threat)

            return threats

        except Exception as e:
            print(f"Error evaluating rule {rule.get('rule_id')}: {e}")
            return []

    def _get_recent_logs(
        self, account_id: Optional[str], lookback_minutes: int
    ) -> List[Dict[str, Any]]:
        """Get recent audit logs for specified account"""
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            start_time = (now - timedelta(minutes=lookback_minutes)).isoformat()
            end_time = now.isoformat()

            if account_id:
                # Query by account_id using GSI
                response = self.audit_logs_table.query(
                    IndexName="AccountIdTimestampIndex",
                    KeyConditionExpression="account_id = :aid AND #ts BETWEEN :start AND :end",
                    ExpressionAttributeNames={"#ts": "timestamp"},
                    ExpressionAttributeValues={
                        ":aid": account_id,
                        ":start": start_time,
                        ":end": end_time,
                    },
                    Limit=1000,  # Reasonable limit
                )
            else:
                # Scan all recent logs (expensive, but needed for multi-account)
                response = self.audit_logs_table.scan(
                    FilterExpression="#ts BETWEEN :start AND :end",
                    ExpressionAttributeNames={"#ts": "timestamp"},
                    ExpressionAttributeValues={
                        ":start": start_time,
                        ":end": end_time,
                    },
                    Limit=1000,
                )

            return response.get("Items", [])

        except ClientError as e:
            print(f"Error getting recent logs: {e}")
            return []

    def _check_connection_spike(
        self,
        rule: Dict[str, Any],
        account_id: Optional[str],
        logs: List[Dict[str, Any]],
    ) -> Optional[Threat]:
        """Check for connection spike anomaly"""
        import json

        condition = json.loads(rule.get("condition", "{}"))
        threshold = condition.get("threshold", 10)
        window_minutes = condition.get("window_minutes", 5)

        # Filter for $connect events
        connect_events = [
            log
            for log in logs
            if log.get("event_type") == "$connect"
        ]

        # Count events in recent window
        window_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=window_minutes)
        recent_connects = [
            log
            for log in connect_events
            if datetime.fromisoformat(log.get("timestamp", ""))
            > window_start
        ]

        if len(recent_connects) >= threshold:
            return Threat(
                threat_id=f"spike-{rule['rule_id']}-{datetime.now(timezone.utc).timestamp()}",
                rule_id=rule["rule_id"],
                severity=rule.get("priority", 5),
                account_id=account_id,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                message=f"Connection spike detected: {len(recent_connects)} connections in {window_minutes} minutes (threshold: {threshold})",
                evidence=recent_connects[:5],  # Top 5 for evidence
            )

        return None

    def _check_auth_failure_rate(
        self,
        rule: Dict[str, Any],
        account_id: Optional[str],
        logs: List[Dict[str, Any]],
    ) -> Optional[Threat]:
        """Check for excessive authentication failures"""
        import json

        condition = json.loads(rule.get("condition", "{}"))
        threshold = condition.get("threshold", 5)

        # Filter for auth failure events
        auth_failures = [
            log
            for log in logs
            if log.get("status") == "error"
            and log.get("event_type") in ["$auth", "login", "authenticate"]
        ]

        if len(auth_failures) >= threshold:
            return Threat(
                threat_id=f"auth-{rule['rule_id']}-{datetime.now(timezone.utc).timestamp()}",
                rule_id=rule["rule_id"],
                severity=rule.get("priority", 7),
                account_id=account_id,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                message=f"High authentication failure rate: {len(auth_failures)} failures (threshold: {threshold})",
                evidence=auth_failures[:5],
            )

        return None

    def _check_unknown_region(
        self,
        rule: Dict[str, Any],
        account_id: Optional[str],
        logs: List[Dict[str, Any]],
    ) -> Optional[Threat]:
        """Check for operations from unknown regions"""
        import json

        condition = json.loads(rule.get("condition", "{}"))
        allowed_regions = condition.get("allowed_regions", ["ap-northeast-1"])

        # Filter for region-based anomalies
        unknown_region_events = [
            log
            for log in logs
            if log.get("region") and log.get("region") not in allowed_regions
        ]

        if unknown_region_events:
            return Threat(
                threat_id=f"region-{rule['rule_id']}-{datetime.now(timezone.utc).timestamp()}",
                rule_id=rule["rule_id"],
                severity=rule.get("priority", 6),
                account_id=account_id,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                message=f"Operations detected from unknown regions: {len(unknown_region_events)} events",
                evidence=unknown_region_events[:5],
            )

        return None

    def _check_public_bucket(
        self,
        rule: Dict[str, Any],
        account_id: Optional[str],
        logs: List[Dict[str, Any]],
    ) -> Optional[Threat]:
        """Check for public bucket creation/modification"""
        import json

        # Filter for S3 public bucket events
        public_bucket_events = [
            log
            for log in logs
            if "s3" in log.get("service", "").lower()
            and ("CreateBucket" in log.get("event_type", "") or "CreateBucket" in log.get("event_name", "")
                 or "PutBucketPolicy" in log.get("event_type", "") or "PutBucketPolicy" in log.get("event_name", ""))
            and "public" in json.dumps(log.get("details", "")).lower()
        ]

        if public_bucket_events:
            return Threat(
                threat_id=f"bucket-{rule['rule_id']}-{datetime.now(timezone.utc).timestamp()}",
                rule_id=rule["rule_id"],
                severity=rule.get("priority", 9),
                account_id=account_id,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                message=f"Public bucket access detected: {len(public_bucket_events)} events",
                evidence=public_bucket_events[:5],
            )

        return None
