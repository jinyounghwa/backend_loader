"""Orchestrator for cost automation with Guardian system integration."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CostAutomationOrchestrator:
    """Orchestrates cost automation while integrating with Guardian security system."""

    def __init__(self):
        """Initialize orchestrator."""
        self.audit_trail = []
        self.approvals = {}

    def sync_with_security_rules(
        self,
        cost_recommendations: List[Dict[str, Any]],
        security_rules: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Synchronize cost recommendations with security rules.

        Args:
            cost_recommendations: List of cost optimization recommendations
            security_rules: List of security rules that must be respected

        Returns:
            Dict with compatible recommendations and conflicts
        """
        try:
            compatible_recommendations = []
            conflicts = []

            for rec in cost_recommendations:
                service = rec.get("service")
                action = rec.get("action")

                # Check against security rules
                has_conflict = False
                for sec_rule in security_rules:
                    rule_service = sec_rule.get("applies_to_service")
                    rule_constraint = sec_rule.get("rule")

                    # Check for conflicts
                    if rule_service == service or rule_service == "all":
                        if action == "stop_instance" and "must_run" in rule_constraint:
                            has_conflict = True
                            conflicts.append(
                                {
                                    "recommendation": rec.get("action"),
                                    "conflicting_rule": rule_constraint,
                                    "reason": "Security rule requires service to run 24/7",
                                }
                            )

                if not has_conflict:
                    compatible_recommendations.append(rec)

            return {
                "success": True,
                "compatible_recommendations": compatible_recommendations,
                "conflicts": conflicts,
                "compatible_count": len(compatible_recommendations),
                "conflict_count": len(conflicts),
            }

        except Exception as e:
            logger.error(f"Error syncing with security rules: {e}")
            return {"success": False, "error": str(e)}

    def execute_with_approval_workflow(
        self,
        action: Dict[str, Any],
        account_id: str,
        approval_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute automation action with approval workflow.

        Args:
            action: Action to execute
            account_id: AWS account ID
            approval_config: Approval configuration (level, timeout, etc.)

        Returns:
            Dict with approval status and ID
        """
        try:
            import uuid
            approval_id = str(uuid.uuid4())

            approval_level = approval_config.get("approval_level", "auto")
            cost_impact = action.get("cost_impact", 0)

            # Risk scoring: high impact = higher approval level needed
            risk_score = min(cost_impact / 100, 1.0)  # Normalized to 0-1

            status = "pending_approval"
            if approval_level == "auto" or risk_score < 0.1:
                status = "auto_approved"

            approval_record = {
                "approval_id": approval_id,
                "action_id": action.get("action_id"),
                "account_id": account_id,
                "approval_level": approval_level,
                "risk_score": round(risk_score, 2),
                "status": status,
                "cost_impact": cost_impact,
                "timeout_hours": approval_config.get("timeout_hours", 24),
            }

            self.approvals[approval_id] = approval_record

            return {
                "success": True,
                "approval_id": approval_id,
                "action_id": action.get("action_id"),
                "status": status,
                "risk_score": round(risk_score, 2),
                "cost_impact": cost_impact,
            }

        except Exception as e:
            logger.error(f"Error executing approval workflow: {e}")
            return {"success": False, "error": str(e)}

    def maintain_action_audit_trail(
        self, account_id: str, action_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Maintain comprehensive audit trail of actions.

        Args:
            account_id: AWS account ID
            action_result: Result of executed action

        Returns:
            Dict with audit log ID
        """
        try:
            import uuid
            audit_log_id = str(uuid.uuid4())

            audit_record = {
                "audit_log_id": audit_log_id,
                "account_id": account_id,
                "action_id": action_result.get("action_id"),
                "action_type": action_result.get("action_type"),
                "result": action_result.get("result"),
                "cost_impact": action_result.get("cost_impact", 0),
                "timestamp": "2026-05-27T12:00:00Z",
                "user_id": "system",
                "details": action_result,
            }

            self.audit_trail.append(audit_record)

            return {
                "success": True,
                "audit_log_id": audit_log_id,
                "action_id": action_result.get("action_id"),
            }

        except Exception as e:
            logger.error(f"Error maintaining audit trail: {e}")
            return {"success": False, "error": str(e)}

    def calculate_realized_savings(
        self,
        account_id: str,
        action_id: str,
        cost_before: float,
        cost_after: float,
        time_period_days: int,
    ) -> Dict[str, Any]:
        """
        Calculate actual cost savings realized from action.

        Args:
            account_id: AWS account ID
            action_id: Action ID
            cost_before: Cost before action
            cost_after: Cost after action
            time_period_days: Time period measured

        Returns:
            Dict with realized and annualized savings
        """
        try:
            realized_savings = cost_before - cost_after
            annualized_savings = (realized_savings / time_period_days) * 365

            # Calculate confidence based on measurement period
            if time_period_days >= 30:
                confidence = 0.95
            elif time_period_days >= 14:
                confidence = 0.80
            else:
                confidence = 0.60

            return {
                "success": True,
                "action_id": action_id,
                "account_id": account_id,
                "realized_savings": round(realized_savings, 2),
                "cost_before": round(cost_before, 2),
                "cost_after": round(cost_after, 2),
                "measurement_period_days": time_period_days,
                "annualized_savings": round(annualized_savings, 2),
                "confidence": round(confidence, 2),
            }

        except Exception as e:
            logger.error(f"Error calculating realized savings: {e}")
            return {"success": False, "error": str(e)}

    def get_audit_trail(
        self, account_id: str = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail records.

        Args:
            account_id: Optional account filter
            limit: Maximum records to return

        Returns:
            List of audit records
        """
        try:
            trail = self.audit_trail
            if account_id:
                trail = [r for r in trail if r.get("account_id") == account_id]

            return trail[-limit:][::-1]  # Newest first

        except Exception as e:
            logger.error(f"Error getting audit trail: {e}")
            return []
