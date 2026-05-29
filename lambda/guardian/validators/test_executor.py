"""Rule Test Executor for Sprint 35 Phase 1

Executes rules against sample logs for testing and validation.
Provides detailed results on rule matches and threat detection.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import time
import uuid


@dataclass
class TestResult:
    """Result of rule test execution"""
    rule_id: str
    total_logs: int
    matched_logs: int
    detected_threats: List[Dict[str, Any]]
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class TestExecutor:
    """Executes rules against sample logs for testing"""

    def __init__(self, anomaly_detector=None):
        """
        Initialize test executor
        Args:
            anomaly_detector: AnomalyDetector instance for threat detection
        """
        self.anomaly_detector = anomaly_detector

    def execute_test(
        self,
        rule: Dict[str, Any],
        test_logs: List[Dict[str, Any]],
        account_id: Optional[str] = None
    ) -> TestResult:
        """
        Execute a rule against sample logs
        Args:
            rule: Rule definition with rule_type, condition, action, priority
            test_logs: List of sample logs to test against
            account_id: Account ID for context
        Returns:
            TestResult with matched logs and detected threats
        """
        start_time = time.time()

        try:
            if not rule or not test_logs:
                return TestResult(
                    rule_id=rule.get("rule_id", "unknown") if rule else "unknown",
                    total_logs=len(test_logs),
                    matched_logs=0,
                    detected_threats=[],
                    execution_time_ms=0,
                    success=False,
                    error_message="Rule or test logs are empty"
                )

            # Evaluate rule against sample logs
            matched_logs = self._evaluate_rule_against_logs(rule, test_logs)

            # Generate threats if matches found
            detected_threats = []
            if matched_logs and self.anomaly_detector:
                detected_threats = self._generate_test_threats(
                    rule, matched_logs, account_id
                )

            execution_time_ms = (time.time() - start_time) * 1000

            return TestResult(
                rule_id=rule.get("rule_id", "test-rule"),
                total_logs=len(test_logs),
                matched_logs=len(matched_logs),
                detected_threats=detected_threats,
                execution_time_ms=execution_time_ms,
                success=True
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return TestResult(
                rule_id=rule.get("rule_id", "unknown") if rule else "unknown",
                total_logs=len(test_logs),
                matched_logs=0,
                detected_threats=[],
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(e)
            )

    def _evaluate_rule_against_logs(
        self,
        rule: Dict[str, Any],
        test_logs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate rule condition against test logs
        Returns list of logs that match the rule condition
        """
        rule_type = rule.get("rule_type")
        condition = rule.get("condition", {})

        matched = []

        for log in test_logs:
            if rule_type == "connection_spike":
                # Check if log is a $connect event
                if log.get("event_type") == "$connect":
                    matched.append(log)

            elif rule_type == "auth_failure":
                # Check if log has authentication failure
                if "auth" in log.get("event_type", "").lower() and "fail" in log.get("status", "").lower():
                    matched.append(log)

            elif rule_type == "unknown_region":
                # Check if log is from unknown region
                allowed_regions = condition.get("allowed_regions", [])
                log_region = log.get("region")
                if log_region and log_region not in allowed_regions:
                    matched.append(log)

            elif rule_type == "public_bucket":
                # Check if log is about S3 bucket creation/update
                if log.get("service") == "s3" and "bucket" in log.get("event_type", "").lower():
                    matched.append(log)

        return matched

    def _generate_test_threats(
        self,
        rule: Dict[str, Any],
        matched_logs: List[Dict[str, Any]],
        account_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate threat objects from matched logs
        """
        threats = []

        threat_base = {
            "threat_id": str(uuid.uuid4()),
            "rule_id": rule.get("rule_id", "test-rule"),
            "severity": rule.get("priority", 5),
            "account_id": account_id or "test-account",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "evidence_count": len(matched_logs),
        }

        if matched_logs:
            threat = {
                **threat_base,
                "message": f"Rule '{rule.get('rule_type')}' triggered by {len(matched_logs)} event(s)",
                "evidence": matched_logs[:10]  # Include first 10 as evidence
            }
            threats.append(threat)

        return threats

    def validate_test_input(
        self,
        rule: Dict[str, Any],
        test_logs: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate test input before execution
        Returns (is_valid, error_message)
        """
        if not rule:
            return False, "Rule is required"

        if not isinstance(rule, dict):
            return False, "Rule must be a dictionary"

        required_fields = ["rule_type", "condition", "action"]
        missing = [f for f in required_fields if f not in rule]
        if missing:
            return False, f"Rule missing required fields: {', '.join(missing)}"

        if not test_logs:
            return False, "At least one test log is required"

        if not isinstance(test_logs, list):
            return False, "Test logs must be a list"

        if not all(isinstance(log, dict) for log in test_logs):
            return False, "All test logs must be dictionaries"

        return True, None
