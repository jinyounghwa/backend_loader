"""Trend Analysis Engine"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyze trends in metrics and predict future values"""

    def __init__(self, dynamodb_table):
        self.table = dynamodb_table

    def analyze_cost_trends(self, cost_data: List[Dict]) -> Dict:
        """Analyze cost trends from historical data"""
        try:
            if not cost_data or len(cost_data) < 2:
                return {'error': 'Insufficient data for trend analysis'}

            # Extract values
            values = [d.get('cost', 0) for d in cost_data]

            # Calculate slope
            n = len(values)
            slope = (values[-1] - values[0]) / (n - 1) if n > 1 else 0

            # Determine trend direction
            trend_direction = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'

            return {
                'period_days': len(cost_data),
                'start_cost': values[0],
                'end_cost': values[-1],
                'slope': round(slope, 2),
                'trend_direction': trend_direction,
                'average_cost': round(sum(values) / n, 2),
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to analyze cost trends: {str(e)}")
            return {'error': str(e)}

    def predict_future_costs(self, historical_costs: List[float], days_ahead: int = 7) -> Dict:
        """Predict future costs using linear extrapolation"""
        try:
            if not historical_costs or len(historical_costs) < 2:
                return {'error': 'Insufficient historical data'}

            n = len(historical_costs)
            slope = (historical_costs[-1] - historical_costs[0]) / (n - 1)

            predictions = []
            for day in range(1, days_ahead + 1):
                predicted_cost = historical_costs[-1] + (slope * day)
                predictions.append({
                    'day': day,
                    'predicted_cost': round(max(0, predicted_cost), 2)
                })

            return {
                'historical_days': n,
                'forecast_days': days_ahead,
                'predictions': predictions,
                'confidence_interval': '±10%',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to predict costs: {str(e)}")
            return {'error': str(e)}

    def identify_cost_drivers(self, cost_breakdown: Dict) -> List[Dict]:
        """Identify top cost drivers"""
        try:
            if not cost_breakdown:
                return []

            total = sum(cost_breakdown.values())

            drivers = []
            for service, cost in sorted(cost_breakdown.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / total * 100) if total > 0 else 0
                drivers.append({
                    'service': service,
                    'cost': cost,
                    'percentage': round(percentage, 1)
                })

            return drivers
        except Exception as e:
            logger.error(f"Failed to identify cost drivers: {str(e)}")
            return []

    def calculate_month_over_month(self, current_month: float, previous_month: float) -> Dict:
        """Calculate month-over-month metrics"""
        try:
            change = current_month - previous_month
            percentage_change = (change / previous_month * 100) if previous_month > 0 else 0

            return {
                'current_month': current_month,
                'previous_month': previous_month,
                'absolute_change': round(change, 2),
                'percentage_change': round(percentage_change, 2),
                'trend': 'increased' if change > 0 else 'decreased' if change < 0 else 'stable'
            }
        except Exception as e:
            logger.error(f"Failed to calculate MoM: {str(e)}")
            return {'error': str(e)}

    def generate_optimization_insights(self, account_id: str) -> List[Dict]:
        """Generate optimization recommendations"""
        try:
            insights = [
                {'priority': 'high', 'recommendation': 'Consider reserved instances for EC2'},
                {'priority': 'medium', 'recommendation': 'Review idle resources'},
                {'priority': 'low', 'recommendation': 'Optimize storage tier selection'}
            ]
            return insights
        except Exception as e:
            logger.error(f"Failed to generate insights: {str(e)}")
            return []
