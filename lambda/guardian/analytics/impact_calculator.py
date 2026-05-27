"""Financial Impact Analysis for Optimization Recommendations."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ImpactCalculator:
    """Calculates real savings impact and financial analysis for recommendations."""

    def __init__(self):
        """Initialize impact calculator."""
        self.calculations_cache = {}

    def estimate_savings(self, baseline_cost: float, optimization_type: str) -> Dict[str, Any]:
        """
        Estimate savings for different optimization types.

        Args:
            baseline_cost: Current monthly cost
            optimization_type: Type of optimization (e.g., 'reserved_instances', 'spot_instances')

        Returns:
            Dict with monthly_savings, annual_savings, savings_percent, confidence
        """
        try:
            if baseline_cost <= 0:
                return {
                    "monthly_savings": 0.0,
                    "annual_savings": 0.0,
                    "savings_percent": 0.0,
                    "confidence": 0.0,
                }

            # Savings estimates by optimization type (based on AWS best practices)
            savings_map = {
                "reserved_instances": {
                    "percent": 0.40,
                    "confidence": 0.90,
                    "description": "1-year Reserved Instances",
                },
                "spot_instances": {
                    "percent": 0.70,
                    "confidence": 0.75,
                    "description": "Spot Instances for fault-tolerant workloads",
                },
                "scheduled_scaling": {
                    "percent": 0.15,
                    "confidence": 0.80,
                    "description": "Time-based scaling optimization",
                },
                "seasonal_adjustments": {
                    "percent": 0.10,
                    "confidence": 0.70,
                    "description": "Seasonal demand adjustments",
                },
                "storage_class_transition": {
                    "percent": 0.60,
                    "confidence": 0.85,
                    "description": "Transition to cheaper storage classes",
                },
                "lifecycle_policies": {
                    "percent": 0.30,
                    "confidence": 0.80,
                    "description": "Automated data lifecycle management",
                },
                "compression": {
                    "percent": 0.25,
                    "confidence": 0.75,
                    "description": "Data compression and deduplication",
                },
                "memory_optimization": {
                    "percent": 0.30,
                    "confidence": 0.82,
                    "description": "Right-sizing memory allocation",
                },
                "code_optimization": {
                    "percent": 0.20,
                    "confidence": 0.70,
                    "description": "Code and query optimization",
                },
                "provisioned_concurrency": {
                    "percent": 0.25,
                    "confidence": 0.78,
                    "description": "Provisioned concurrency optimization",
                },
                "billing_mode_optimization": {
                    "percent": 0.40,
                    "confidence": 0.83,
                    "description": "Switch to on-demand or provisioned",
                },
                "ttl_optimization": {
                    "percent": 0.35,
                    "confidence": 0.81,
                    "description": "TTL and automatic cleanup",
                },
                "query_optimization": {
                    "percent": 0.20,
                    "confidence": 0.75,
                    "description": "Query and key schema optimization",
                },
                "multi_az_review": {
                    "percent": 0.50,
                    "confidence": 0.65,
                    "description": "Multi-AZ necessity review",
                },
                "rightsizing": {
                    "percent": 0.20,
                    "confidence": 0.85,
                    "description": "Instance right-sizing",
                },
            }

            # Get savings estimate or use default
            if optimization_type in savings_map:
                estimate = savings_map[optimization_type]
            else:
                # Default conservative estimate
                estimate = {
                    "percent": 0.15,
                    "confidence": 0.60,
                    "description": "General optimization",
                }

            monthly_savings = baseline_cost * estimate["percent"]
            annual_savings = monthly_savings * 12

            return {
                "optimization_type": optimization_type,
                "baseline_monthly_cost": round(baseline_cost, 2),
                "monthly_savings": round(monthly_savings, 2),
                "annual_savings": round(annual_savings, 2),
                "savings_percent": round(estimate["percent"] * 100, 1),
                "confidence": estimate["confidence"],
                "description": estimate.get("description", ""),
            }

        except Exception as e:
            logger.error(f"Error estimating savings: {e}")
            return {}

    def calculate_breakeven(
        self,
        upfront_cost: float,
        monthly_savings: float,
        discount_rate: float = 0.05,
        analysis_period_months: int = 36,
    ) -> Dict[str, Any]:
        """
        Calculate financial metrics including breakeven, NPV, and IRR.

        Args:
            upfront_cost: One-time implementation cost
            monthly_savings: Monthly cost savings
            discount_rate: Annual discount rate for NPV (default 5%)
            analysis_period_months: Period for analysis (default 36 months)

        Returns:
            Dict with payback_months, npv, irr_percent, three_year_savings
        """
        try:
            if monthly_savings <= 0:
                return {
                    "payback_months": float("inf"),
                    "npv": -upfront_cost,
                    "irr_percent": 0.0,
                    "three_year_savings": 0.0,
                    "is_profitable": False,
                }

            # Calculate payback period
            if upfront_cost > 0:
                payback_months = upfront_cost / monthly_savings
            else:
                payback_months = 0.0

            # Calculate NPV (Net Present Value)
            # NPV = sum of (monthly_savings / (1 + discount_rate/12)^month) - upfront_cost
            monthly_discount_rate = discount_rate / 12
            npv = -upfront_cost

            for month in range(1, analysis_period_months + 1):
                pv_savings = monthly_savings / ((1 + monthly_discount_rate) ** month)
                npv += pv_savings

            # Calculate simple IRR (approximation)
            # For simple case: IRR is roughly (annual_savings / upfront_cost) * 100
            annual_savings = monthly_savings * 12
            if upfront_cost > 0:
                irr_percent = (annual_savings / upfront_cost) * 100
            else:
                irr_percent = 0.0

            # Calculate 3-year savings
            total_savings_3years = monthly_savings * analysis_period_months
            net_savings_3years = total_savings_3years - upfront_cost

            # Determine if profitable
            is_profitable = npv > 0

            return {
                "upfront_cost": round(upfront_cost, 2),
                "monthly_savings": round(monthly_savings, 2),
                "annual_savings": round(annual_savings, 2),
                "payback_months": round(payback_months, 1),
                "payback_days": round(payback_months * 30.44, 0),
                "npv": round(npv, 2),
                "irr_percent": round(irr_percent, 1),
                "discount_rate_percent": discount_rate * 100,
                "analysis_period_months": analysis_period_months,
                "total_savings": round(total_savings_3years, 2),
                "net_savings_after_cost": round(net_savings_3years, 2),
                "roi_percent": round((annual_savings / upfront_cost) * 100, 1) if upfront_cost > 0 else 0.0,
                "is_profitable": is_profitable,
                "profitability_summary": (
                    f"Breaks even in {payback_months:.1f} months. "
                    f"3-year net savings: ${net_savings_3years:.0f}"
                ),
            }

        except Exception as e:
            logger.error(f"Error calculating breakeven: {e}")
            return {}

    def validate_feasibility(
        self, recommendation: Dict[str, Any], constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate financial feasibility of a recommendation.

        Args:
            recommendation: Optimization recommendation with financial metrics
            constraints: Financial constraints (max_upfront_cost, min_roi_percent, etc.)

        Returns:
            Feasibility assessment with score and warnings
        """
        if constraints is None:
            constraints = {}

        try:
            feasibility = {
                "recommendation_id": recommendation.get("recommendation_id", "unknown"),
                "financial_feasibility_score": 1.0,
                "is_financially_feasible": True,
                "warnings": [],
                "blockers": [],
            }

            annual_savings = recommendation.get("annual_savings", 0)
            upfront_cost = recommendation.get("upfront_cost", 0)
            confidence = recommendation.get("confidence", 0.5)

            # Check upfront cost budget
            max_upfront = constraints.get("max_upfront_cost", float("inf"))
            if upfront_cost > max_upfront:
                feasibility["blockers"].append(
                    f"Upfront cost (${upfront_cost:.2f}) exceeds budget (${max_upfront:.2f})"
                )
                feasibility["is_financially_feasible"] = False

            # Check minimum ROI requirement
            min_roi = constraints.get("min_roi_percent", 0)
            if upfront_cost > 0:
                roi = (annual_savings / upfront_cost) * 100
                if roi < min_roi:
                    feasibility["warnings"].append(
                        f"ROI ({roi:.1f}%) below minimum requirement ({min_roi:.1f}%)"
                    )
                    feasibility["financial_feasibility_score"] *= 0.7

            # Check minimum annual savings
            min_annual_savings = constraints.get("min_annual_savings", 0)
            if annual_savings < min_annual_savings:
                feasibility["warnings"].append(
                    f"Annual savings (${annual_savings:.2f}) below minimum (${min_annual_savings:.2f})"
                )
                feasibility["financial_feasibility_score"] *= 0.6

            # Check payback period constraint
            max_payback_months = constraints.get("max_payback_months", 24)
            if upfront_cost > 0 and annual_savings > 0:
                payback = (upfront_cost / (annual_savings / 12))
                if payback > max_payback_months:
                    feasibility["warnings"].append(
                        f"Payback period ({payback:.1f} months) exceeds limit ({max_payback_months} months)"
                    )
                    feasibility["financial_feasibility_score"] *= 0.8

            # Apply confidence as final modifier
            feasibility["financial_feasibility_score"] *= confidence

            return feasibility

        except Exception as e:
            logger.error(f"Error validating feasibility: {e}")
            return {
                "is_financially_feasible": False,
                "blockers": [str(e)],
                "financial_feasibility_score": 0.0,
            }

    def generate_financial_report(
        self, recommendations: List[Dict[str, Any]], discount_rate: float = 0.05
    ) -> Dict[str, Any]:
        """
        Generate comprehensive financial report for multiple recommendations.

        Args:
            recommendations: List of recommendations with financial metrics
            discount_rate: Annual discount rate for NPV

        Returns:
            Aggregated financial report
        """
        try:
            if not recommendations:
                return {
                    "total_recommendations": 0,
                    "total_annual_savings": 0.0,
                    "total_upfront_cost": 0.0,
                    "portfolio_roi_percent": 0.0,
                    "recommendations": [],
                }

            total_annual_savings = 0.0
            total_upfront_cost = 0.0
            total_npv = 0.0

            for rec in recommendations:
                annual_savings = rec.get("annual_savings", 0)
                upfront_cost = rec.get("upfront_cost", 0)

                total_annual_savings += annual_savings
                total_upfront_cost += upfront_cost

                # Simple NPV contribution
                if upfront_cost > 0:
                    simple_npv = (annual_savings * 3) - upfront_cost  # 3-year NPV approximation
                    total_npv += simple_npv

            # Calculate portfolio metrics
            portfolio_roi = 0.0
            if total_upfront_cost > 0:
                portfolio_roi = (total_annual_savings / total_upfront_cost) * 100

            portfolio_payback = 0.0
            if total_annual_savings > 0:
                portfolio_payback = (total_upfront_cost / (total_annual_savings / 12))

            return {
                "report_date": "current",
                "total_recommendations": len(recommendations),
                "total_annual_savings": round(total_annual_savings, 2),
                "total_upfront_cost": round(total_upfront_cost, 2),
                "portfolio_roi_percent": round(portfolio_roi, 1),
                "portfolio_payback_months": round(portfolio_payback, 1),
                "three_year_npv": round(total_npv, 2),
                "avg_confidence": (
                    round(
                        sum(r.get("confidence", 0.5) for r in recommendations) / len(recommendations),
                        2,
                    )
                    if recommendations
                    else 0.0
                ),
                "recommendations": recommendations,
            }

        except Exception as e:
            logger.error(f"Error generating financial report: {e}")
            return {}
