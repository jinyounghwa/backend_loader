"""Predictive scaling based on forecasts."""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class PredictiveScaling:
    """Scale resources based on predicted demand."""

    def __init__(self):
        """Initialize predictive scaling."""
        self.forecasts = {}

    def generate_forecast(
        self,
        resource_id: str,
        historical_data: List[float],
    ) -> Dict[str, Any]:
        """Generate demand forecast for resource.
        
        Args:
            resource_id: AWS resource ID
            historical_data: Historical usage data points
            
        Returns:
            Forecast with predicted values
        """
        if not historical_data:
            return {'error': 'No historical data'}

        # Simple forecast: average of historical data
        average = sum(historical_data) / len(historical_data)
        max_val = max(historical_data)
        min_val = min(historical_data)

        return {
            'resource_id': resource_id,
            'average_demand': average,
            'peak_demand': max_val * 1.2,  # 20% buffer
            'minimum_demand': min_val,
            'confidence': 0.85,
        }

    def calculate_required_capacity(
        self, forecast: Dict[str, Any]
    ) -> int:
        """Calculate required capacity based on forecast.
        
        Args:
            forecast: Forecast data
            
        Returns:
            Required capacity in units
        """
        peak = forecast.get('peak_demand', 0)
        # Round up to nearest 10
        return int((peak // 10 + 1) * 10)

    def suggest_scaling_action(
        self,
        current_capacity: int,
        required_capacity: int,
    ) -> Optional[Dict[str, Any]]:
        """Suggest scaling action based on requirements.
        
        Args:
            current_capacity: Current capacity
            required_capacity: Required capacity
            
        Returns:
            Scaling suggestion or None
        """
        difference_percent = (
            (required_capacity - current_capacity) / current_capacity * 100
            if current_capacity > 0
            else 0
        )

        # Only suggest if difference > 10%
        if abs(difference_percent) <= 10:
            return None

        if required_capacity > current_capacity:
            return {
                'action': 'scale_up',
                'current': current_capacity,
                'required': required_capacity,
                'percentage_increase': difference_percent,
                'reason': 'Predicted demand increase',
            }
        else:
            return {
                'action': 'scale_down',
                'current': current_capacity,
                'required': required_capacity,
                'percentage_decrease': abs(difference_percent),
                'reason': 'Predicted demand decrease',
            }

    def estimate_cost_impact(
        self,
        action: Dict[str, Any],
        cost_per_unit_hour: float,
    ) -> Dict[str, Any]:
        """Estimate cost impact of scaling action.
        
        Args:
            action: Scaling action
            cost_per_unit_hour: Cost per unit per hour
            
        Returns:
            Cost impact estimate
        """
        capacity_change = action['required'] - action['current']
        hours_per_month = 730

        monthly_impact = capacity_change * cost_per_unit_hour * hours_per_month

        return {
            'monthly_cost_change': monthly_impact,
            'is_cost_saving': monthly_impact < 0,
            'estimated_monthly_savings': abs(monthly_impact) if monthly_impact < 0 else 0,
        }
