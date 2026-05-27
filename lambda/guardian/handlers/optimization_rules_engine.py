"""Optimization rules engine for custom automation."""

import logging
import uuid
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RulesEngine:
    """Manages custom optimization rules and executions."""

    def __init__(self):
        """Initialize rules engine."""
        self.rules = {}
        self.executions = []

    def create_rule(self, account_id: str, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create custom optimization rule.

        Args:
            account_id: AWS account ID
            rule_config: Rule configuration

        Returns:
            Dict with rule_id and confirmation
        """
        try:
            rule_id = str(uuid.uuid4())
            rule = {
                "rule_id": rule_id,
                "account_id": account_id,
                **rule_config,
                "created_at": "2026-05-27",
                "enabled": True,
            }
            self.rules[rule_id] = rule

            return {
                "success": True,
                "rule_id": rule_id,
                "rule_name": rule_config.get("name"),
                "account_id": account_id,
            }

        except Exception as e:
            logger.error(f"Error creating rule: {e}")
            return {"success": False, "error": str(e)}

    def evaluate_rule_conditions(
        self, rule: Dict[str, Any], metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate if rule conditions are met.

        Args:
            rule: Rule definition
            metrics: Current resource metrics

        Returns:
            Dict with rule_triggered and matching conditions
        """
        try:
            condition_type = rule.get("condition_type", "utilization")
            metric_name = rule.get("metric")
            threshold = rule.get("threshold", 0)
            duration_days = rule.get("duration_days", 1)

            metric_value = metrics.get(metric_name, 0)
            days_monitored = metrics.get("days_monitored", 0)

            # Check metric threshold
            metric_met = metric_value < threshold

            # Check duration requirement
            duration_met = days_monitored >= duration_days

            rule_triggered = metric_met and duration_met
            matching_metrics = []
            if metric_met:
                matching_metrics.append(metric_name)
            if duration_met:
                matching_metrics.append("duration")

            return {
                "success": True,
                "rule_triggered": rule_triggered,
                "metric_name": metric_name,
                "metric_value": round(metric_value, 2),
                "threshold": threshold,
                "days_monitored": days_monitored,
                "duration_required": duration_days,
                "matching_metrics": matching_metrics,
            }

        except Exception as e:
            logger.error(f"Error evaluating rule conditions: {e}")
            return {"success": False, "error": str(e)}

    def execute_rule_action(
        self, rule: Dict[str, Any], account_id: str, resource_id: str
    ) -> Dict[str, Any]:
        """
        Execute rule action.

        Args:
            rule: Rule definition
            account_id: AWS account ID
            resource_id: Target resource ID

        Returns:
            Dict with execution result and status
        """
        try:
            execution_id = str(uuid.uuid4())
            approval_required = rule.get("approval_required", False)

            status = "pending_approval" if approval_required else "executed"

            execution = {
                "execution_id": execution_id,
                "rule_id": rule.get("rule_id"),
                "account_id": account_id,
                "resource_id": resource_id,
                "action": rule.get("action"),
                "status": status,
                "created_at": "2026-05-27",
            }

            self.executions.append(execution)

            return {
                "success": True,
                "execution_id": execution_id,
                "rule_id": rule.get("rule_id"),
                "action": rule.get("action"),
                "resource_id": resource_id,
                "status": status,
            }

        except Exception as e:
            logger.error(f"Error executing rule action: {e}")
            return {"success": False, "error": str(e)}

    def detect_rule_conflicts(
        self, account_id: str, rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect conflicting rules.

        Args:
            account_id: AWS account ID
            rules: List of rules to check

        Returns:
            Dict with conflict detection results
        """
        try:
            conflicts = []

            # Check for conflicting actions on same target service
            for i, rule1 in enumerate(rules):
                for rule2 in rules[i + 1 :]:
                    if (
                        rule1.get("target_service") == rule2.get("target_service")
                        and rule1.get("action") != rule2.get("action")
                    ):
                        # Different actions on same service = potential conflict
                        # But only flag if both have resource_type AND they match
                        rt1 = rule1.get("resource_type")
                        rt2 = rule2.get("resource_type")
                        if rt1 and rt2 and rt1 == rt2:
                            conflicts.append(
                                {
                                    "rule1_id": rule1.get("rule_id"),
                                    "rule2_id": rule2.get("rule_id"),
                                    "conflict_type": "different_actions_same_service",
                                }
                            )

            return {
                "success": True,
                "account_id": account_id,
                "conflicts_found": len(conflicts) > 0,
                "conflict_count": len(conflicts),
                "conflicts": conflicts,
            }

        except Exception as e:
            logger.error(f"Error detecting rule conflicts: {e}")
            return {"success": False, "error": str(e)}

    def list_rules(self, account_id: str) -> Dict[str, Any]:
        """
        List enabled rules for account.

        Args:
            account_id: AWS account ID

        Returns:
            Dict with rules and potential savings
        """
        try:
            account_rules = [r for r in self.rules.values() if r.get("account_id") == account_id]
            enabled_rules = [r for r in account_rules if r.get("enabled", True)]

            total_savings = sum(r.get("estimate_savings", 0) for r in enabled_rules)

            return {
                "success": True,
                "account_id": account_id,
                "rules": enabled_rules,
                "enabled_count": len(enabled_rules),
                "total_potential_savings": round(total_savings, 2),
            }

        except Exception as e:
            logger.error(f"Error listing rules: {e}")
            return {"success": False, "error": str(e)}
