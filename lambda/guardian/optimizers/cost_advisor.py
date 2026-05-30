"""Advanced cost optimization advisor."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict


class RIPurchaseAdvisor:
    """Recommend Reserved Instance purchases."""

    def recommend(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend RI purchase based on utilization."""
        usage_pct = instance.get('usage_percentage', 0)
        days_running = instance.get('days_running', 0)
        monthly_cost = instance.get('monthly_cost', 0)

        # RI recommendation logic (check 3-year first, more specific)
        if usage_pct >= 85 and days_running >= 150:
            # Very stable workload: recommend 3-year RI
            monthly_savings = monthly_cost * 0.40  # 40% savings
            annual_savings = monthly_savings * 12
            roi = 0.40 if usage_pct >= 95 else 0.35

            return {
                'action': 'PURCHASE_RI_3YEAR',
                'monthly_savings': monthly_savings,
                'annual_savings': annual_savings,
                'roi': roi,
                'recommendation_strength': 'VERY_STRONG'
            }
        elif usage_pct >= 90 and days_running >= 60:
            # High utilization, long-running: recommend 1-year RI
            monthly_savings = monthly_cost * 0.30  # 30% savings
            annual_savings = monthly_savings * 12
            roi = 0.30

            return {
                'action': 'PURCHASE_RI_1YEAR',
                'monthly_savings': monthly_savings,
                'annual_savings': annual_savings,
                'roi': roi,
                'recommendation_strength': 'STRONG'
            }
        else:
            # Low utilization or short-running: no RI
            return {
                'action': 'NO_ACTION',
                'monthly_savings': 0,
                'annual_savings': 0,
                'roi': 0.0,
                'reason': 'Low utilization or short duration'
            }


class SpotInstanceOptimizer:
    """Recommend Spot instance usage."""

    def optimize(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize using Spot instances."""
        interruption_tolerance = instance.get('interruption_tolerance', 'NONE')
        monthly_cost = instance.get('monthly_cost', 0)
        workload_type = instance.get('workload_type', 'GENERAL')

        if interruption_tolerance == 'NONE':
            # Cannot use Spot for critical workloads
            return {
                'recommendation': 'USE_ON_DEMAND',
                'savings': 0,
                'reason': 'Workload cannot tolerate interruptions'
            }
        elif interruption_tolerance == 'HIGH':
            # Use Spot for flexible workloads
            spot_price = monthly_cost * 0.35  # 65% savings
            savings = monthly_cost - spot_price

            return {
                'recommendation': 'USE_SPOT',
                'spot_price': spot_price,
                'savings': savings,
                'savings_percentage': 65,
                'annual_savings': savings * 12
            }
        else:
            # Medium tolerance: hybrid approach
            hybrid_price = monthly_cost * 0.65  # 35% savings
            savings = monthly_cost - hybrid_price

            return {
                'recommendation': 'HYBRID_SPOT_ON_DEMAND',
                'hybrid_price': hybrid_price,
                'savings': savings,
                'savings_percentage': 35,
                'annual_savings': savings * 12
            }


class CostForecastor:
    """Forecast future costs."""

    def forecast(self, history: List[float], days: int = 30) -> List[float]:
        """Forecast costs using historical data."""
        if not history or len(history) < 30:
            # Insufficient data: return average
            avg = sum(history) / len(history) if history else 0
            return [avg] * days

        # Simple trend-based forecast
        recent_avg = sum(history[-30:]) / 30
        trend = (history[-1] - history[-60]) / 30 if len(history) >= 60 else 0

        forecast = []
        for i in range(days):
            predicted = recent_avg + (trend * (i + 1))
            forecast.append(max(0, predicted))

        return forecast


class OptimizationSimulator:
    """Simulate cost changes from optimizations."""

    def simulate(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate optimization scenario."""
        if 'changes' in scenario:
            # Multi-change scenario - assume $1000/month baseline if not specified
            base_cost = scenario.get('current_monthly_cost', 1000)
            total_monthly_savings = 0

            for change in scenario['changes']:
                if change['type'] == 'DOWNSIZE':
                    # Estimate 40% savings for downsize
                    saving = base_cost * 0.40
                    total_monthly_savings += saving
                elif change['type'] == 'USE_SPOT':
                    discount = change.get('spot_discount', 0.65)
                    saving = base_cost * discount
                    total_monthly_savings += saving
                elif change['type'] == 'PURCHASE_RI':
                    ri_saving = base_cost * 0.30
                    total_monthly_savings += ri_saving

            annual_savings = total_monthly_savings * 12

            return {
                'total_monthly_savings': total_monthly_savings,
                'annual_savings': annual_savings,
                'roi_percentage': (annual_savings / (base_cost * 12)) * 100
            }
        else:
            # Single change
            current_cost = scenario.get('current_monthly_cost', 0)
            change_type = scenario.get('change')

            if change_type == 'PURCHASE_RI_1YEAR':
                new_monthly = current_cost * 0.70  # 30% savings
                monthly_savings = current_cost - new_monthly
                annual_savings = monthly_savings * 12

                return {
                    'current_monthly_cost': current_cost,
                    'new_monthly_cost': new_monthly,
                    'monthly_savings': monthly_savings,
                    'annual_savings': annual_savings,
                    'roi_percentage': 30
                }
            elif change_type == 'USE_SPOT':
                discount = scenario.get('spot_discount', 0.70)
                new_monthly = current_cost * (1 - discount)
                monthly_savings = current_cost - new_monthly

                return {
                    'current_monthly_cost': current_cost,
                    'new_monthly_cost': new_monthly,
                    'monthly_savings': monthly_savings,
                    'annual_savings': monthly_savings * 12
                }

        return {'error': 'Unknown scenario type'}


class CostSavingsCalculator:
    """Calculate cost savings and ROI."""

    def calculate_annual_savings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate annual savings from monthly delta."""
        monthly_savings = data['current_monthly'] - data['optimized_monthly']
        months = data.get('months', 12)
        annual_savings = monthly_savings * months
        savings_percentage = (monthly_savings / data['current_monthly']) * 100

        return {
            'monthly_savings': monthly_savings,
            'annual_savings': annual_savings,
            'savings_percentage': savings_percentage
        }

    def calculate_roi(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ROI for optimization."""
        annual_savings = data.get('annual_savings', 0)
        upfront_cost = data.get('upfront_cost', 0)
        months_to_break_even = data.get('months_to_break_even', 12)

        roi_percentage = (annual_savings / max(upfront_cost, 1)) * 100 if upfront_cost > 0 else 200

        return {
            'roi_percentage': roi_percentage,
            'payback_period_months': months_to_break_even,
            'annual_roi': annual_savings
        }

    def compare_optimizations(self, optimizations: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """Compare different optimization approaches."""
        results = []

        for opt_type, data in optimizations.items():
            monthly_savings = data['monthly_savings']
            annual_savings = monthly_savings * 12
            upfront = data.get('upfront', 0)

            results.append({
                'type': opt_type,
                'monthly_savings': monthly_savings,
                'annual_savings': annual_savings,
                'total_annual_savings': annual_savings - upfront
            })

        return sorted(results, key=lambda x: x['total_annual_savings'], reverse=True)


class CostOptimizationEngine:
    """End-to-end cost optimization engine."""

    def __init__(self):
        self.ri_advisor = RIPurchaseAdvisor()
        self.spot_optimizer = SpotInstanceOptimizer()
        self.forecaster = CostForecastor()

    def audit(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """Audit account for optimization opportunities."""
        instances = account.get('instances', [])
        recommendations = []
        total_savings = 0

        for instance in instances:
            # Normalize field names
            normalized = dict(instance)
            if 'utilization' in normalized and 'usage_percentage' not in normalized:
                normalized['usage_percentage'] = normalized['utilization']

            # Check RI opportunity
            ri_rec = self.ri_advisor.recommend(normalized)
            if ri_rec['action'] != 'NO_ACTION':
                total_savings += ri_rec['annual_savings']
                recommendations.append(ri_rec)

            # Check Spot opportunity
            spot_rec = self.spot_optimizer.optimize(normalized)
            if spot_rec['recommendation'] != 'USE_ON_DEMAND':
                total_savings += spot_rec.get('annual_savings', 0)
                recommendations.append(spot_rec)

        return {
            'recommendations': recommendations,
            'total_potential_savings': total_savings,
            'recommendation_count': len(recommendations)
        }

    def get_recommendations(self, account: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get prioritized recommendations."""
        instances = account.get('instances', [])
        recs = []

        for instance in instances:
            ri_rec = self.ri_advisor.recommend(instance)
            spot_rec = self.spot_optimizer.optimize(instance)

            best_rec = max(
                [ri_rec, spot_rec],
                key=lambda x: x.get('annual_savings', x.get('savings', 0) * 12)
            )

            best_rec['instance_id'] = instance.get('id')
            best_rec['potential_savings'] = best_rec.get('annual_savings', best_rec.get('savings', 0) * 12)
            recs.append(best_rec)

        return sorted(recs, key=lambda x: x['potential_savings'], reverse=True)

    def generate_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cost optimization report."""
        recommendations = data.get('recommendations', [])
        total_current = data.get('total_current_cost', 0)
        total_savings = sum(r.get('savings', 0) for r in recommendations)

        savings_percentage = round(total_savings / total_current * 100, 1) if total_current > 0 else 0

        return {
            'account_id': data.get('account_id'),
            'month': data.get('month'),
            'total_current_cost': total_current,
            'total_potential_savings': total_savings,
            'savings_percentage': savings_percentage,
            'recommendations': recommendations,
            'recommendation_count': len(recommendations)
        }
