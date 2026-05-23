"""Rule Validator for Sprint 34 Phase 2

Validates rule conditions and actions against templates.
Performs schema validation and dry-run evaluation against test data.
"""

from typing import Dict, Any, List, Optional
import json
from validators.validation_result import ValidationResult


class RuleValidator:
    """Validates security rules against templates"""

    def __init__(self, template_repo, anomaly_detector):
        """
        Initialize validator with dependencies.

        Args:
            template_repo: TemplateRepository instance
            anomaly_detector: AnomalyDetector instance for dry-run evaluation
        """
        self.template_repo = template_repo
        self.anomaly_detector = anomaly_detector

    def validate(self, rule: Dict[str, Any]) -> ValidationResult:
        """
        Validate a rule against its template.

        Args:
            rule: Dictionary containing rule_id, rule_type, condition, action, template_id, etc.

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        result = ValidationResult(is_valid=True)

        try:
            # Check required fields
            required_fields = ["rule_type", "condition", "action"]
            for field in required_fields:
                if field not in rule:
                    result.add_error(f"Missing required field: {field}")

            if not result.is_valid:
                return result

            # Get template if specified
            template = None
            if rule.get("template_id"):
                template = self.template_repo.get_template(rule["template_id"])
                if not template:
                    result.add_error(f"Template {rule['template_id']} not found")
                    return result

            # Validate rule type
            valid_rule_types = [
                "connection_spike",
                "auth_failure",
                "unknown_region",
                "public_bucket",
            ]
            if rule["rule_type"] not in valid_rule_types:
                result.add_error(f"Invalid rule_type: {rule['rule_type']}")

            # Validate condition
            condition = rule.get("condition", {})
            if not isinstance(condition, dict):
                result.add_error("Condition must be a dictionary")
            else:
                self._validate_condition(rule["rule_type"], condition, template, result)

            # Validate action
            action = rule.get("action", {})
            if not isinstance(action, dict):
                result.add_error("Action must be a dictionary")
            else:
                self._validate_action(action, template, result)

            # Validate priority
            priority = rule.get("priority", 5)
            if not isinstance(priority, int) or priority < 1 or priority > 10:
                result.add_warning(f"Priority should be between 1-10, got {priority}")

            # Validate enabled status
            enabled = rule.get("enabled", True)
            if enabled and not result.is_valid:
                result.add_error("Cannot enable rule with validation errors")

        except Exception as e:
            result.add_error(f"Validation exception: {str(e)}")

        return result

    def _validate_condition(
        self,
        rule_type: str,
        condition: Dict[str, Any],
        template: Optional[Any],
        result: ValidationResult,
    ) -> None:
        """Validate condition based on rule type"""
        if rule_type == "connection_spike":
            if "threshold" not in condition:
                result.add_error("connection_spike rule requires 'threshold' condition")
            elif not isinstance(condition["threshold"], int) or condition["threshold"] < 1:
                result.add_error("threshold must be a positive integer")

            if "window_minutes" in condition:
                if not isinstance(condition["window_minutes"], int) or condition["window_minutes"] < 1:
                    result.add_error("window_minutes must be a positive integer")

        elif rule_type == "auth_failure":
            if "threshold" not in condition:
                result.add_error("auth_failure rule requires 'threshold' condition")
            elif not isinstance(condition["threshold"], int) or condition["threshold"] < 1:
                result.add_error("threshold must be a positive integer")

        elif rule_type == "unknown_region":
            if "allowed_regions" not in condition:
                result.add_error("unknown_region rule requires 'allowed_regions' condition")
            elif not isinstance(condition["allowed_regions"], list):
                result.add_error("allowed_regions must be a list")
            elif len(condition["allowed_regions"]) == 0:
                result.add_warning("allowed_regions is empty - all regions will be flagged as unknown")

        elif rule_type == "public_bucket":
            # public_bucket doesn't require condition parameters
            pass

    def _validate_action(
        self,
        action: Dict[str, Any],
        template: Optional[Any],
        result: ValidationResult,
    ) -> None:
        """Validate action"""
        if "notify" in action:
            if not isinstance(action["notify"], list):
                result.add_error("notify must be a list of channel names")
            else:
                valid_channels = ["telegram", "discord", "slack", "email"]
                for channel in action["notify"]:
                    if channel not in valid_channels:
                        result.add_warning(f"Unknown notification channel: {channel}")

                if len(action["notify"]) == 0:
                    result.add_warning("No notification channels specified")
        else:
            result.add_warning("No notification action specified")

    def test_rule(
        self,
        rule: Dict[str, Any],
        test_logs: List[Dict[str, Any]],
        account_id: Optional[str] = None,
    ) -> ValidationResult:
        """
        Perform dry-run evaluation of rule against test logs.

        Args:
            rule: Dictionary containing rule configuration
            test_logs: List of test audit log entries
            account_id: Account ID to evaluate for

        Returns:
            ValidationResult with dry-run threat detection results
        """
        result = ValidationResult(is_valid=True)

        try:
            # First validate the rule
            validation = self.validate(rule)
            if not validation.is_valid:
                result.errors = validation.errors
                result.warnings = validation.warnings
                result.is_valid = False
                return result

            # Perform dry-run evaluation
            if self.anomaly_detector and len(test_logs) > 0:
                # Mock the rules and logs for the detector
                detector = self.anomaly_detector

                # Temporarily set mock data
                detector.rules_table.query = lambda **kwargs: {
                    "Items": [rule]
                }
                detector.audit_logs_table.query = lambda **kwargs: {
                    "Items": test_logs
                }

                # Run detection
                threats = detector.detect_anomalies(account_id=account_id, lookback_minutes=60)

                # Convert threats to dictionary format
                for threat in threats:
                    threat_dict = {
                        "threat_id": threat.threat_id,
                        "rule_id": threat.rule_id,
                        "severity": threat.severity,
                        "message": threat.message,
                        "account_id": threat.account_id,
                        "timestamp": threat.timestamp.isoformat() if hasattr(threat.timestamp, 'isoformat') else str(threat.timestamp),
                        "evidence_count": len(threat.evidence),
                    }
                    result.add_dry_run_threat(threat_dict)

                if len(threats) == 0:
                    result.add_warning("No threats detected with test data - rule may be too strict")

            result.add_warning(f"Dry-run evaluated against {len(test_logs)} test logs")

        except Exception as e:
            result.add_error(f"Dry-run exception: {str(e)}")

        return result
