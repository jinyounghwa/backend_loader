"""Rule Management Lambda Handler for Sprint 33 Phase 1

Provides HTTP API endpoints for creating, reading, updating, and deleting security rules.
Integrates with API Gateway and DynamoDB SecurityRulesTable.
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

from guardian.storage.security_rules import SecurityRuleRepository, SecurityRule


def get_rules_table_name() -> str:
    """Get the SecurityRulesTable name from environment"""
    return os.environ.get("SECURITY_RULES_TABLE", "aws-guardian-security-rules")


def format_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Format Lambda response for API Gateway"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def get_rule_id_from_path(path: str) -> str:
    """Extract rule_id from path (e.g., /rules/rule-123 -> rule-123)"""
    parts = path.split("/")
    if len(parts) >= 3:
        return parts[2]
    return ""


def handle_get_rules(event: Dict[str, Any]) -> Dict[str, Any]:
    """GET /rules - List all rules"""
    try:
        repo = SecurityRuleRepository(get_rules_table_name())

        # Check query parameters
        query_params = event.get("queryStringParameters") or {}
        rule_type = query_params.get("rule_type")
        account_id = query_params.get("account_id")
        enabled_only = query_params.get("enabled_only", "false").lower() == "true"

        if rule_type:
            rules = repo.list_rules_by_type(rule_type, enabled_only=enabled_only)
        elif account_id:
            rules = repo.list_rules_by_account(account_id, enabled_only=enabled_only)
        else:
            rules = repo.list_all_rules(enabled_only=enabled_only)

        rules_data = [
            {
                "rule_id": rule.rule_id,
                "rule_type": rule.rule_type,
                "condition": rule.condition,
                "action": rule.action,
                "priority": rule.priority,
                "account_id": rule.account_id,
                "enabled": rule.enabled,
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat(),
            }
            for rule in rules
        ]

        return format_response(200, {"rules": rules_data, "count": len(rules_data)})
    except Exception as e:
        return format_response(500, {"error": f"Failed to list rules: {str(e)}"})


def handle_get_rule(event: Dict[str, Any]) -> Dict[str, Any]:
    """GET /rules/{rule_id} - Get a specific rule"""
    try:
        rule_id = get_rule_id_from_path(event["path"])
        if not rule_id:
            return format_response(400, {"error": "Missing rule_id"})

        repo = SecurityRuleRepository(get_rules_table_name())
        rule = repo.get_rule(rule_id)

        if not rule:
            return format_response(404, {"error": f"Rule {rule_id} not found"})

        rule_data = {
            "rule_id": rule.rule_id,
            "rule_type": rule.rule_type,
            "condition": rule.condition,
            "action": rule.action,
            "priority": rule.priority,
            "account_id": rule.account_id,
            "enabled": rule.enabled,
            "created_at": rule.created_at.isoformat(),
            "updated_at": rule.updated_at.isoformat(),
        }

        return format_response(200, {"rule": rule_data})
    except Exception as e:
        return format_response(500, {"error": f"Failed to get rule: {str(e)}"})


def handle_create_rule(event: Dict[str, Any]) -> Dict[str, Any]:
    """POST /rules - Create a new rule"""
    try:
        body = json.loads(event.get("body", "{}"))

        # Validate required fields
        required_fields = ["rule_type", "condition", "action", "priority"]
        for field in required_fields:
            if field not in body:
                return format_response(400, {"error": f"Missing required field: {field}"})

        rule = SecurityRule(
            rule_id="",  # Will be generated
            rule_type=body["rule_type"],
            condition=body["condition"],
            action=body["action"],
            priority=body["priority"],
            account_id=body.get("account_id"),
            enabled=body.get("enabled", True),
        )

        repo = SecurityRuleRepository(get_rules_table_name())
        created_rule = repo.create_rule(rule)

        rule_data = {
            "rule_id": created_rule.rule_id,
            "rule_type": created_rule.rule_type,
            "condition": created_rule.condition,
            "action": created_rule.action,
            "priority": created_rule.priority,
            "account_id": created_rule.account_id,
            "enabled": created_rule.enabled,
            "created_at": created_rule.created_at.isoformat(),
            "updated_at": created_rule.updated_at.isoformat(),
        }

        return format_response(201, {"rule": rule_data})
    except json.JSONDecodeError:
        return format_response(400, {"error": "Invalid JSON body"})
    except Exception as e:
        return format_response(500, {"error": f"Failed to create rule: {str(e)}"})


def handle_update_rule(event: Dict[str, Any]) -> Dict[str, Any]:
    """PUT /rules/{rule_id} - Update an existing rule"""
    try:
        rule_id = get_rule_id_from_path(event["path"])
        if not rule_id:
            return format_response(400, {"error": "Missing rule_id"})

        body = json.loads(event.get("body", "{}"))

        repo = SecurityRuleRepository(get_rules_table_name())
        updated_rule = repo.update_rule(rule_id, body)

        rule_data = {
            "rule_id": updated_rule.rule_id,
            "rule_type": updated_rule.rule_type,
            "condition": updated_rule.condition,
            "action": updated_rule.action,
            "priority": updated_rule.priority,
            "account_id": updated_rule.account_id,
            "enabled": updated_rule.enabled,
            "created_at": updated_rule.created_at.isoformat(),
            "updated_at": updated_rule.updated_at.isoformat(),
        }

        return format_response(200, {"rule": rule_data})
    except json.JSONDecodeError:
        return format_response(400, {"error": "Invalid JSON body"})
    except ValueError as e:
        return format_response(404, {"error": str(e)})
    except Exception as e:
        return format_response(500, {"error": f"Failed to update rule: {str(e)}"})


def handle_delete_rule(event: Dict[str, Any]) -> Dict[str, Any]:
    """DELETE /rules/{rule_id} - Delete a rule"""
    try:
        rule_id = get_rule_id_from_path(event["path"])
        if not rule_id:
            return format_response(400, {"error": "Missing rule_id"})

        repo = SecurityRuleRepository(get_rules_table_name())
        success = repo.delete_rule(rule_id)

        if not success:
            return format_response(404, {"error": f"Rule {rule_id} not found"})

        return format_response(204, {})
    except Exception as e:
        return format_response(500, {"error": f"Failed to delete rule: {str(e)}"})


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for rule management API"""
    http_method = event.get("requestContext", {}).get("http", {}).get("method")
    path = event.get("path", "")

    # Route to appropriate handler
    if http_method == "GET":
        if path.endswith("/rules") or "/rules" == path:
            # Check if path has rule_id (single rule vs list)
            parts = path.split("/")
            if len(parts) >= 3 and parts[2]:
                return handle_get_rule(event)
            return handle_get_rules(event)
        return handle_get_rule(event)
    elif http_method == "POST" and path.endswith("/rules"):
        return handle_create_rule(event)
    elif http_method == "PUT":
        return handle_update_rule(event)
    elif http_method == "DELETE":
        return handle_delete_rule(event)
    else:
        return format_response(405, {"error": f"Method {http_method} not allowed"})
