"""Rule Validation Lambda Handler for Sprint 34 Phase 2

Handles REST API operations for rule validation:
- POST /validate (validate rule configuration)
- POST /test-run (dry-run test with sample logs)
"""

import json
import os
from typing import Dict, Any
from guardian.http_response import success_response, error_response
from validators.rule_validator import RuleValidator
from storage.rule_template import TemplateRepository
from detectors.anomaly_detector import AnomalyDetector


def get_table_names() -> Dict[str, str]:
    """Get table names from environment or defaults"""
    return {
        "template_table": os.environ.get("RULE_TEMPLATE_TABLE", "aws-guardian-rule-templates"),
        "rules_table": os.environ.get("SECURITY_RULES_TABLE", "aws-guardian-security-rules"),
        "audit_logs_table": os.environ.get("AUDIT_LOGS_TABLE", "aws-guardian-audit-logs"),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for rule validation API"""
    try:
        http_method = event.get("httpMethod", "POST")
        path = event.get("path", "")
        body = event.get("body", "{}")

        if isinstance(body, str):
            body = json.loads(body) if body else {}

        tables = get_table_names()
        template_repo = TemplateRepository(tables["template_table"])
        anomaly_detector = AnomalyDetector(tables["rules_table"], tables["audit_logs_table"])
        validator = RuleValidator(template_repo, anomaly_detector)

        # Route handlers
        if http_method == "POST" and path == "/validate":
            return validate_rule(validator, body)

        elif http_method == "POST" and path == "/test-run":
            return test_rule(validator, body)

        else:
            return error_response(400, "Invalid request")

    except Exception as e:
        print(f"Error in validation handler: {e}")
        return error_response(500, str(e))


def validate_rule(validator: RuleValidator, body: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a rule configuration"""
    try:
        if "rule" not in body:
            return error_response(400, "Missing required field: rule")

        rule = body["rule"]
        result = validator.validate(rule)

        return success_response({
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "execution_time_ms": result.execution_time_ms,
        })

    except Exception as e:
        print(f"Error validating rule: {e}")
        return error_response(500, str(e))


def test_rule(validator: RuleValidator, body: Dict[str, Any]) -> Dict[str, Any]:
    """Test a rule with sample logs"""
    try:
        required_fields = ["rule", "test_logs"]
        for field in required_fields:
            if field not in body:
                return error_response(400, f"Missing required field: {field}")

        rule = body["rule"]
        test_logs = body["test_logs"]
        account_id = body.get("account_id")

        result = validator.test_rule(rule, test_logs, account_id)

        return success_response({
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "dry_run_threats": result.dry_run_threats,
            "execution_time_ms": result.execution_time_ms,
        })

    except Exception as e:
        print(f"Error testing rule: {e}")
        return error_response(500, str(e))
