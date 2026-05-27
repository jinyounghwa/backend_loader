"""ML-Based Recommendations Engine for cost optimization."""

import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Generates cost optimization recommendations based on pattern analysis."""

    def __init__(self):
        """Initialize recommendation engine."""
        self.recommendations = {}
        self.analysis_cache = {}

    def analyze_cost_patterns(self, values: List[float], period: int = 12) -> Dict[str, Any]:
        """
        Analyze cost patterns to identify peaks, troughs, and volatility.

        Args:
            values: List of cost values (typically monthly)
            period: Analysis period (default 12 for monthly)

        Returns:
            Dict with peak_periods, off_peak_periods, volatility_score
        """
        if not values or len(values) < period:
            return {
                "peak_periods": [],
                "off_peak_periods": [],
                "volatility_score": 0.0,
                "average_cost": 0.0,
                "min_cost": 0.0,
                "max_cost": 0.0,
            }

        try:
            # Calculate statistics
            avg_cost = sum(values) / len(values)
            min_cost = min(values)
            max_cost = max(values)

            # Calculate volatility (standard deviation / mean)
            variance = sum((v - avg_cost) ** 2 for v in values) / len(values)
            std_dev = variance ** 0.5
            volatility_score = (std_dev / avg_cost) if avg_cost > 0 else 0.0

            # Identify peak and off-peak periods
            sorted_indices = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
            peak_threshold = int(len(values) * 0.3)  # Top 30%
            peak_periods = sorted_indices[:peak_threshold]

            off_peak_threshold = int(len(values) * 0.3)  # Bottom 30%
            off_peak_periods = sorted_indices[-off_peak_threshold:]

            return {
                "peak_periods": peak_periods,
                "off_peak_periods": off_peak_periods,
                "volatility_score": round(volatility_score, 2),
                "average_cost": round(avg_cost, 2),
                "min_cost": round(min_cost, 2),
                "max_cost": round(max_cost, 2),
                "peak_to_off_peak_ratio": round(max_cost / min_cost, 2) if min_cost > 0 else 0.0,
            }

        except Exception as e:
            logger.error(f"Error analyzing cost patterns: {e}")
            return {}

    def identify_opportunities(
        self, services_costs: Dict[str, List[float]], seasonality: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify cost optimization opportunities based on service costs and seasonality.

        Args:
            services_costs: Dict of service -> cost history
            seasonality: Seasonality detection results

        Returns:
            List of opportunities with service, type, savings estimate, confidence
        """
        opportunities = []

        try:
            for service, costs in services_costs.items():
                if not costs or len(costs) < 6:
                    continue

                # Analyze this service's pattern
                pattern = self.analyze_cost_patterns(costs)
                volatility = pattern.get("volatility_score", 0)
                avg_cost = pattern.get("average_cost", 0)
                peak_ratio = pattern.get("peak_to_off_peak_ratio", 1.0)

                # High volatility → Reserved Instances or Spot instances
                if volatility > 0.3:
                    savings_estimate = avg_cost * 0.25  # 25% savings estimate
                    opportunities.append(
                        {
                            "service": service,
                            "opportunity_type": "reserved_instances",
                            "description": f"High volatility ({volatility:.1%}) indicates potential for Reserved/Spot instances",
                            "savings_estimate": round(savings_estimate, 2),
                            "confidence": min(0.95, 0.6 + volatility * 0.3),
                        }
                    )

                # High peak ratio → Schedule-based scaling
                if peak_ratio > 1.5:
                    savings_estimate = avg_cost * 0.15  # 15% savings estimate
                    opportunities.append(
                        {
                            "service": service,
                            "opportunity_type": "scheduled_scaling",
                            "description": f"Peak-to-off-peak ratio {peak_ratio:.1f}x suggests schedule-based optimization",
                            "savings_estimate": round(savings_estimate, 2),
                            "confidence": min(0.90, 0.5 + (peak_ratio - 1.5) * 0.1),
                        }
                    )

                # Check seasonality
                if seasonality.get("is_seasonal"):
                    strength = seasonality.get("strength", 0)
                    if strength > 0.5:
                        savings_estimate = avg_cost * 0.1  # 10% savings estimate
                        opportunities.append(
                            {
                                "service": service,
                                "opportunity_type": "seasonal_adjustments",
                                "description": f"Seasonal pattern (strength {strength:.1%}) detected",
                                "savings_estimate": round(savings_estimate, 2),
                                "confidence": min(0.85, 0.4 + strength * 0.4),
                            }
                        )

            return opportunities

        except Exception as e:
            logger.error(f"Error identifying opportunities: {e}")
            return []

    def generate_recommendations(
        self, analysis_result: Dict[str, Any], opportunities: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations from analysis.

        Args:
            analysis_result: Cost analysis result
            opportunities: Identified opportunities

        Returns:
            List of recommendations with action, service, savings, implementation_effort
        """
        if opportunities is None:
            opportunities = []

        recommendations = []

        try:
            for opp in opportunities:
                service = opp.get("service", "unknown")
                opp_type = opp.get("opportunity_type", "")
                savings = opp.get("savings_estimate", 0)
                confidence = opp.get("confidence", 0.5)

                # Map opportunity type to implementation details
                if opp_type == "reserved_instances":
                    recommendation = {
                        "recommendation_id": str(uuid.uuid4()),
                        "service": service,
                        "action": "convert_to_reserved_instances",
                        "description": f"Convert on-demand instances to 1-year Reserved Instances",
                        "monthly_savings": round(savings, 2),
                        "annual_savings": round(savings * 12, 2),
                        "implementation_effort": "medium",
                        "implementation_steps": [
                            "Analyze current instance usage patterns",
                            "Calculate break-even point",
                            "Purchase Reserved Instances",
                            "Monitor utilization",
                        ],
                        "confidence": round(confidence, 2),
                    }
                elif opp_type == "scheduled_scaling":
                    recommendation = {
                        "recommendation_id": str(uuid.uuid4()),
                        "service": service,
                        "action": "implement_scheduled_scaling",
                        "description": f"Implement time-based scaling rules for off-peak hours",
                        "monthly_savings": round(savings, 2),
                        "annual_savings": round(savings * 12, 2),
                        "implementation_effort": "low",
                        "implementation_steps": [
                            "Identify off-peak hours",
                            "Configure scaling policies",
                            "Test schedule",
                            "Monitor and adjust",
                        ],
                        "confidence": round(confidence, 2),
                    }
                elif opp_type == "seasonal_adjustments":
                    recommendation = {
                        "recommendation_id": str(uuid.uuid4()),
                        "service": service,
                        "action": "optimize_seasonal_usage",
                        "description": f"Adjust capacity for seasonal demand variations",
                        "monthly_savings": round(savings, 2),
                        "annual_savings": round(savings * 12, 2),
                        "implementation_effort": "medium",
                        "implementation_steps": [
                            "Review historical seasonal patterns",
                            "Plan capacity adjustments",
                            "Implement automation",
                            "Monitor effectiveness",
                        ],
                        "confidence": round(confidence, 2),
                    }
                else:
                    continue

                # Add common fields
                recommendation["status"] = "ready_for_implementation"
                recommendation["priority_score"] = 0.0  # Will be calculated by prioritize_recommendations

                recommendations.append(recommendation)

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    def calculate_roi(
        self, recommendation: Dict[str, Any], upfront_cost: float = 0
    ) -> Dict[str, Any]:
        """
        Calculate ROI for a recommendation.

        Args:
            recommendation: Recommendation dict with monthly_savings
            upfront_cost: One-time implementation cost

        Returns:
            Dict with payback_months, annual_savings, roi_percent
        """
        try:
            monthly_savings = recommendation.get("monthly_savings", 0)
            annual_savings = recommendation.get("annual_savings", 0)

            if monthly_savings <= 0:
                return {
                    "payback_months": float("inf"),
                    "annual_savings": round(annual_savings, 2),
                    "roi_percent": 0.0,
                }

            # Calculate payback period
            payback_months = upfront_cost / monthly_savings if upfront_cost > 0 else 0

            # Calculate ROI (annual savings / upfront cost)
            roi_percent = 0.0
            if upfront_cost > 0:
                roi_percent = (annual_savings / upfront_cost) * 100

            return {
                "payback_months": round(payback_months, 1),
                "annual_savings": round(annual_savings, 2),
                "roi_percent": round(roi_percent, 2),
            }

        except Exception as e:
            logger.error(f"Error calculating ROI: {e}")
            return {}

    def prioritize_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize recommendations by impact and feasibility.

        Args:
            recommendations: List of recommendations

        Returns:
            Sorted list by priority score
        """
        try:
            for rec in recommendations:
                # Priority score = (annual_savings * confidence) / effort_weight
                annual_savings = rec.get("annual_savings", 0)
                confidence = rec.get("confidence", 0.5)
                effort = rec.get("implementation_effort", "medium")

                # Effort weights: low=1, medium=2, high=3
                effort_weight = {"low": 1, "medium": 2, "high": 3}.get(effort, 2)

                priority_score = (annual_savings * confidence) / (effort_weight * 100)
                rec["priority_score"] = round(priority_score, 2)

            # Sort by priority score (highest first)
            sorted_recs = sorted(recommendations, key=lambda r: r.get("priority_score", 0), reverse=True)

            return sorted_recs

        except Exception as e:
            logger.error(f"Error prioritizing recommendations: {e}")
            return recommendations
