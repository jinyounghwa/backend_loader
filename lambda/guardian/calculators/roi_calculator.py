"""ROI Calculator for Cost Optimization Prioritization"""

import logging
from typing import Dict, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ROICalculator:
    """Calculate ROI and prioritize optimizations by return on investment"""

    def __init__(self):
        """Initialize ROI calculator"""
        pass

    def calculate_implementation_cost(self, optimization: Dict) -> float:
        """
        Calculate total implementation cost for optimization

        Args:
            optimization: Optimization with effort and resource costs

        Returns:
            Total implementation cost
        """
        try:
            # Base cost from effort hours
            effort_hours = optimization.get('effort_hours', 0)
            hourly_rate = optimization.get('hourly_rate', 50)
            labor_cost = effort_hours * hourly_rate

            # Additional costs
            tool_cost = optimization.get('tool_cost', 0)
            testing_cost = optimization.get('testing_cost', 0)
            documentation_cost = optimization.get('documentation_cost', 0)

            total_cost = labor_cost + tool_cost + testing_cost + documentation_cost

            logger.debug(f"Calculated implementation cost: ${total_cost:.2f}")
            return total_cost

        except Exception as e:
            logger.error(f"Failed to calculate implementation cost: {str(e)}")
            return 0.0

    def calculate_annual_savings(self, optimization: Dict) -> Dict:
        """
        Calculate annual savings from optimization

        Args:
            optimization: Optimization with current and optimized costs

        Returns:
            Savings calculation result
        """
        try:
            current_monthly = optimization.get('current_monthly_cost', 0)
            optimized_monthly = optimization.get('optimized_monthly_cost', 0)

            monthly_savings = current_monthly - optimized_monthly
            annual_savings = monthly_savings * 12

            result = {
                'current_annual_cost': current_monthly * 12,
                'optimized_annual_cost': optimized_monthly * 12,
                'monthly_savings': monthly_savings,
                'annual_savings': annual_savings,
                'savings_percentage': (monthly_savings / current_monthly * 100) if current_monthly > 0 else 0
            }

            logger.info(f"Calculated annual savings: ${annual_savings:.2f}")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate savings: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def calculate_payback_period(self, optimization: Dict) -> float:
        """
        Calculate payback period for optimization

        Args:
            optimization: Optimization with implementation cost and monthly savings

        Returns:
            Payback period in months
        """
        try:
            implementation_cost = optimization.get('implementation_cost', 0)
            monthly_savings = optimization.get('monthly_savings', 0)

            if monthly_savings <= 0:
                payback_months = float('inf')
            else:
                payback_months = implementation_cost / monthly_savings

            logger.info(f"Calculated payback period: {payback_months:.1f} months")
            return payback_months

        except Exception as e:
            logger.error(f"Failed to calculate payback period: {str(e)}")
            return 0.0

    def prioritize_by_roi(self, optimizations: List[Dict]) -> List[Dict]:
        """
        Prioritize optimizations by ROI (highest first)

        Args:
            optimizations: List of optimizations with savings and costs

        Returns:
            Sorted list by ROI descending
        """
        try:
            scored_optimizations = []

            for optimization in optimizations:
                annual_savings = optimization.get('annual_savings', 0)
                implementation_cost = optimization.get('implementation_cost', 0)

                if implementation_cost > 0:
                    roi = (annual_savings - implementation_cost) / implementation_cost * 100
                else:
                    roi = 0 if annual_savings == 0 else float('inf')

                scored = {
                    **optimization,
                    'roi': roi,
                    'roi_percentage': round(roi, 2)
                }
                scored_optimizations.append(scored)

            # Sort by ROI descending
            prioritized = sorted(scored_optimizations, key=lambda x: x.get('roi', 0), reverse=True)

            logger.info(f"Prioritized {len(prioritized)} optimizations by ROI")
            return prioritized

        except Exception as e:
            logger.error(f"Failed to prioritize by ROI: {str(e)}")
            return optimizations

    def get_recommendation_score(self, optimization: Dict) -> Dict:
        """
        Get overall recommendation score for optimization

        Args:
            optimization: Optimization to score

        Returns:
            Recommendation score and rationale
        """
        try:
            annual_savings = optimization.get('annual_savings', 0)
            implementation_cost = optimization.get('implementation_cost', 0)
            effort_hours = optimization.get('effort_hours', 0)

            # Calculate components
            savings_score = min(100, (annual_savings / 10000) * 100)  # Higher savings = higher score
            effort_score = min(100, (10 - effort_hours) * 10)  # Lower effort = higher score
            roi = (annual_savings - implementation_cost) / implementation_cost if implementation_cost > 0 else 0
            roi_score = min(100, roi * 10)  # Higher ROI = higher score

            # Weighted average
            overall_score = (savings_score * 0.3 + effort_score * 0.3 + roi_score * 0.4)

            result = {
                'savings_score': round(savings_score, 1),
                'effort_score': round(effort_score, 1),
                'roi_score': round(roi_score, 1),
                'overall_score': round(overall_score, 1),
                'recommendation': 'high_priority' if overall_score > 70 else 'medium_priority' if overall_score > 40 else 'low_priority'
            }

            logger.debug(f"Scored optimization: {overall_score:.1f}/100")
            return result

        except Exception as e:
            logger.error(f"Failed to score optimization: {str(e)}")
            return {'error': str(e), 'status': 'failed'}
