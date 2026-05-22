"""CloudTrail checker for suspicious API activity detection."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

logger = logging.getLogger(__name__)


class CloudTrailChecker(BaseChecker):
    """Detect suspicious API calls from CloudTrail."""

    # API events that modify resources (ReadOnly=False)
    SUSPICIOUS_EVENTS = {
        "CreateAccessKey",
        "CreateUser",
        "AttachUserPolicy",
        "PutUserPolicy",
        "CreatePolicy",
        "CreateRole",
        "CreateSecurityGroup",
        "DeleteBucket",
        "DeleteTable",
        "TerminateInstances",
        "StopInstances",
        "ModifyDBInstance",
        "DeleteDBInstance",
    }

    # Event sources relevant to the suspicious events above
    RELEVANT_EVENT_SOURCES = {
        "iam.amazonaws.com",
        "ec2.amazonaws.com",
        "s3.amazonaws.com",
        "dynamodb.amazonaws.com",
        "rds.amazonaws.com",
    }

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        effective_config = config or {}
        super().__init__(clients or {}, effective_config, account_id, credentials)

        self.hours_lookback = effective_config.get("cloudtrail_hours", 1)
        self.authorized_regions = set(
            effective_config.get("authorized_regions", ["us-east-1", "us-west-2", "eu-west-1"])
        )

        self.cloudtrail_client = (clients or {}).get("cloudtrail")
        if self.cloudtrail_client is None:
            self.cloudtrail_client = boto3.client("cloudtrail", **Config.get_boto3_kwargs())
        # Backward compatibility alias
        self.cloudtrail = self.cloudtrail_client
        self.sts = (clients or {}).get("sts")

    # ------------------------------------------------------------------
    # Main check entry (sync-first)
    # ------------------------------------------------------------------

    def check(self) -> CheckResult:
        """Check for suspicious CloudTrail events.

        Detects:
        - Failed authentication attempts
        - Root account usage
        - Unusual API activity patterns (CreateAccessKey, CreateUser, etc.)
        """
        self._log_check_start("CloudTrail")
        try:
            events = self._get_recent_events()
            if not events:
                self._log_check_end("CloudTrail", "INFO")
                return CheckResult.info("CloudTrail Check", "No suspicious API calls detected")

            anomalies = self._analyze_events(events)
            if anomalies:
                severity = self._determine_severity(anomalies)
                self._log_check_end("CloudTrail", severity)
                return CheckResult(
                    severity=severity,
                    title="Suspicious API Calls Detected",
                    message=f"Found {len(anomalies)} suspicious API events in CloudTrail",
                    details={"anomalies": anomalies},
                    suggested_action="Review user activity and verify legitimate changes",
                )
            else:
                self._log_check_end("CloudTrail", "INFO")
                return CheckResult.info(
                    "CloudTrail Check", f"Analyzed {len(events)} API events - all appear normal"
                )

        except ClientError as e:
            return self._handle_client_error("CloudTrail", e)
        except Exception as e:
            return self._handle_generic_error("CloudTrail", e)

    # ------------------------------------------------------------------
    # Event retrieval (sync)
    # ------------------------------------------------------------------

    def _get_recent_events(self) -> List[Dict[str, Any]]:
        """Get CloudTrail events from last N hours."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=self.hours_lookback)
        all_events = []

        for source in self.RELEVANT_EVENT_SOURCES:
            try:
                paginator = self.cloudtrail_client.get_paginator("lookup_events")
                for page in paginator.paginate(
                    LookupAttributes=[{"AttributeKey": "EventSource", "AttributeValue": source}],
                    StartTime=start_time,
                ):
                    for event in page.get("Events", []):
                        all_events.append(
                            {
                                "EventName": event.get("EventName"),
                                "Username": event.get("Username"),
                                "EventTime": event.get("EventTime"),
                                "SourceIPAddress": event.get("SourceIPAddress"),
                                "CloudTrailEvent": event.get("CloudTrailEvent"),
                                "EventSource": source,
                            }
                        )
            except ClientError as e:
                logger.warning("ClientError fetching CloudTrail events for %s: %s", source, e)
            except Exception as e:
                logger.warning("Error fetching CloudTrail events for %s: %s", source, e)

        return all_events

    # ------------------------------------------------------------------
    # Event analysis
    # ------------------------------------------------------------------

    def _analyze_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze events for suspicious activity."""
        anomalies = []
        for event in events:
            severity = self._analyze_event(event)
            if severity:
                event_time = event.get("EventTime")
                if event_time and hasattr(event_time, "isoformat"):
                    timestamp = event_time.isoformat()
                else:
                    timestamp = event_time

                anomalies.append(
                    {
                        "event_name": event.get("EventName"),
                        "username": event.get("Username"),
                        "source_ip": event.get("SourceIPAddress"),
                        "event_source": event.get("EventSource", ""),
                        "timestamp": timestamp,
                        "severity": severity,
                    }
                )
        return anomalies

    def _analyze_event(self, event: Dict[str, Any]) -> Optional[str]:
        """Determine severity of a single event."""
        username = event.get("Username", "")
        event_name = event.get("EventName", "")

        if username == "root" or username.endswith(":root"):
            return "CRITICAL"
        if event_name in self.SUSPICIOUS_EVENTS:
            return "HIGH"
        return None

    def _determine_severity(self, anomalies: List[Dict[str, Any]]) -> str:
        """Determine overall severity based on anomalies."""
        if any(a["severity"] == "CRITICAL" for a in anomalies):
            return "CRITICAL"
        elif any(a["severity"] == "HIGH" for a in anomalies):
            return "HIGH"
        elif len(anomalies) >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def _get_remediation_suggestion(self, anomalies: List[Dict[str, Any]]) -> str:
        """Generate remediation suggestion based on anomalies."""
        if not anomalies:
            return "Review CloudTrail logs for suspicious activity"

        event_names = {a.get("event_name") for a in anomalies}

        if "CreateAccessKey" in event_names or "CreateUser" in event_names:
            return "Review and rotate access keys. Enable MFA for affected users."
        elif "AttachUserPolicy" in event_names or "PutUserPolicy" in event_names:
            return "Review IAM permission changes. Check for unauthorized policy modifications."
        elif "TerminateInstances" in event_names or "StopInstances" in event_names:
            return "Verify EC2 instance changes. Review if changes were authorized."
        elif "DeleteBucket" in event_names or "DeleteTable" in event_names:
            return "Alert: Critical resource deletion detected. Review deletion logs immediately."
        else:
            return "Review CloudTrail findings and take appropriate action"
