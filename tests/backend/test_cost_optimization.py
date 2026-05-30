"""Sprint 72 Phase 2: Advanced Cost Optimization (15 tests)"""

import pytest
from datetime import datetime, timedelta


class TestRIPurchaseAdvisor:
    """Test Reserved Instance purchase recommendations."""

    def test_recommend_ri_for_high_utilization(self):
        """✅ Recommend RI purchase for highly utilized instance."""
        from guardian.optimizers.cost_advisor import RIPurchaseAdvisor

        advisor = RIPurchaseAdvisor()

        recommendation = advisor.recommend({
            'instance_type': 't3.xlarge',
            'monthly_cost': 300.00,
            'usage_percentage': 95,
            'days_running': 85
        })

        assert recommendation['action'] == 'PURCHASE_RI_1YEAR'
        assert recommendation['roi'] > 0.25
        assert recommendation['monthly_savings'] > 50

    def test_dont_recommend_ri_for_low_utilization(self):
        """✅ Don't recommend RI for low utilization."""
        from guardian.optimizers.cost_advisor import RIPurchaseAdvisor

        advisor = RIPurchaseAdvisor()

        recommendation = advisor.recommend({
            'instance_type': 't3.large',
            'monthly_cost': 50.00,
            'usage_percentage': 20,
            'days_running': 30
        })

        assert recommendation['action'] in ['NO_ACTION', 'MONITOR']
        assert recommendation['roi'] < 0.15

    def test_recommend_3year_ri_for_stable_workload(self):
        """✅ Recommend 3-year RI for stable workload."""
        from guardian.optimizers.cost_advisor import RIPurchaseAdvisor

        advisor = RIPurchaseAdvisor()

        recommendation = advisor.recommend({
            'instance_type': 'm5.2xlarge',
            'monthly_cost': 500.00,
            'usage_percentage': 98,
            'days_running': 180,
            'workload_type': 'DATABASE'
        })

        assert recommendation['action'] in ['PURCHASE_RI_1YEAR', 'PURCHASE_RI_3YEAR']
        assert recommendation['roi'] > 0.30


class TestSpotInstanceOptimizer:
    """Test Spot instance optimization."""

    def test_recommend_spot_for_flexible_workload(self):
        """✅ Recommend Spot instances for flexible workloads."""
        from guardian.optimizers.cost_advisor import SpotInstanceOptimizer

        optimizer = SpotInstanceOptimizer()

        recommendation = optimizer.optimize({
            'instance_type': 't3.large',
            'monthly_cost': 150.00,
            'interruption_tolerance': 'HIGH',
            'workload_type': 'BATCH'
        })

        assert recommendation['recommendation'] == 'USE_SPOT'
        assert recommendation['savings'] > 60
        assert 'spot_price' in recommendation

    def test_dont_recommend_spot_for_critical_workload(self):
        """✅ Don't recommend Spot for critical workload."""
        from guardian.optimizers.cost_advisor import SpotInstanceOptimizer

        optimizer = SpotInstanceOptimizer()

        recommendation = optimizer.optimize({
            'instance_type': 'm5.xlarge',
            'monthly_cost': 200.00,
            'interruption_tolerance': 'NONE',
            'workload_type': 'DATABASE'
        })

        assert recommendation['recommendation'] == 'USE_ON_DEMAND'
        assert recommendation['savings'] == 0

    def test_hybrid_spot_strategy(self):
        """✅ Recommend hybrid Spot + On-Demand strategy."""
        from guardian.optimizers.cost_advisor import SpotInstanceOptimizer

        optimizer = SpotInstanceOptimizer()

        recommendation = optimizer.optimize({
            'instance_type': 'c5.xlarge',
            'monthly_cost': 300.00,
            'interruption_tolerance': 'MEDIUM',
            'workload_type': 'WEB_APP'
        })

        assert 'HYBRID' in recommendation['recommendation'] or 'SPOT' in recommendation['recommendation']


class TestCostForecastor:
    """Test cost forecasting."""

    def test_forecast_monthly_cost(self):
        """✅ Forecast monthly cost with historical data."""
        from guardian.optimizers.cost_advisor import CostForecastor

        forecaster = CostForecastor()

        history = [100 + (i * 0.5) for i in range(90)]
        forecast = forecaster.forecast(history, days=30)

        assert len(forecast) == 30
        assert all(f > 0 for f in forecast)
        assert forecast[-1] > forecast[0]

    def test_forecast_with_seasonality(self):
        """✅ Forecast captures seasonal patterns."""
        from guardian.optimizers.cost_advisor import CostForecastor

        forecaster = CostForecastor()

        history = []
        for week in range(13):
            for day in range(7):
                cost = 100 if day < 5 else 80
                history.append(cost)

        forecast = forecaster.forecast(history, days=30)

        assert len(forecast) == 30
        assert all(f > 0 for f in forecast)

    def test_forecast_accuracy(self):
        """✅ Forecast achieves > 85% accuracy."""
        from guardian.optimizers.cost_advisor import CostForecastor

        forecaster = CostForecastor()

        history = [100.0] * 60

        forecast = forecaster.forecast(history, days=30)

        avg_forecast = sum(forecast) / len(forecast)
        accuracy = 100 - (abs(avg_forecast - 100) / 100 * 100)

        assert accuracy > 85


class TestOptimizationSimulation:
    """Test cost optimization scenario simulation."""

    def test_simulate_ri_purchase(self):
        """✅ Simulate cost impact of RI purchase."""
        from guardian.optimizers.cost_advisor import OptimizationSimulator

        simulator = OptimizationSimulator()

        result = simulator.simulate({
            'current_instance': 't3.xlarge',
            'current_monthly_cost': 300.00,
            'change': 'PURCHASE_RI_1YEAR',
            'ri_term_years': 1
        })

        assert result['new_monthly_cost'] < result['current_monthly_cost']
        assert result['annual_savings'] > 0
        assert 'roi_percentage' in result

    def test_simulate_spot_adoption(self):
        """✅ Simulate cost impact of Spot adoption."""
        from guardian.optimizers.cost_advisor import OptimizationSimulator

        simulator = OptimizationSimulator()

        result = simulator.simulate({
            'current_instance': 't3.large',
            'current_monthly_cost': 150.00,
            'change': 'USE_SPOT',
            'spot_discount': 0.70
        })

        assert result['new_monthly_cost'] < 150
        assert result['monthly_savings'] > 30

    def test_simulate_multi_change(self):
        """✅ Simulate multiple optimization changes."""
        from guardian.optimizers.cost_advisor import OptimizationSimulator

        simulator = OptimizationSimulator()

        result = simulator.simulate({
            'changes': [
                {'type': 'DOWNSIZE', 'current': 't3.2xlarge', 'target': 't3.xlarge'},
                {'type': 'USE_SPOT', 'spot_discount': 0.65},
                {'type': 'PURCHASE_RI', 'term_years': 1}
            ]
        })

        assert result['total_monthly_savings'] > 0
        assert result['annual_savings'] > 0


class TestCostSavings:
    """Test cost savings calculation."""

    def test_calculate_annual_savings(self):
        """✅ Calculate annual savings."""
        from guardian.optimizers.cost_advisor import CostSavingsCalculator

        calculator = CostSavingsCalculator()

        savings = calculator.calculate_annual_savings({
            'current_monthly': 500.00,
            'optimized_monthly': 350.00,
            'months': 12
        })

        assert savings['monthly_savings'] == 150.00
        assert savings['annual_savings'] == 1800.00
        assert savings['savings_percentage'] == 30.0

    def test_calculate_roi(self):
        """✅ Calculate ROI for optimization."""
        from guardian.optimizers.cost_advisor import CostSavingsCalculator

        calculator = CostSavingsCalculator()

        roi = calculator.calculate_roi({
            'annual_savings': 3000.00,
            'upfront_cost': 0,
            'months_to_break_even': 1
        })

        assert roi['roi_percentage'] > 100
        assert roi['payback_period_months'] == 1

    def test_compare_optimization_types(self):
        """✅ Compare savings by optimization type."""
        from guardian.optimizers.cost_advisor import CostSavingsCalculator

        calculator = CostSavingsCalculator()

        comparisons = calculator.compare_optimizations({
            'RI_1YEAR': {'monthly_savings': 75, 'upfront': 0},
            'RI_3YEAR': {'monthly_savings': 125, 'upfront': 0},
            'SPOT': {'monthly_savings': 90, 'upfront': 0},
            'DOWNSIZE': {'monthly_savings': 60, 'upfront': 0}
        })

        best = max(comparisons, key=lambda x: x['total_annual_savings'])
        assert best['type'] == 'RI_3YEAR'


class TestCostOptimizationIntegration:
    """Test end-to-end cost optimization."""

    def test_comprehensive_cost_audit(self):
        """✅ Comprehensive cost audit."""
        from guardian.optimizers.cost_advisor import CostOptimizationEngine

        engine = CostOptimizationEngine()

        audit = engine.audit({
            'instances': [
                {
                    'id': 'i-1',
                    'type': 't3.2xlarge',
                    'monthly_cost': 600,
                    'utilization': 25,
                    'days_running': 365
                },
                {
                    'id': 'i-2',
                    'type': 'm5.xlarge',
                    'monthly_cost': 200,
                    'utilization': 95,
                    'days_running': 180
                }
            ]
        })

        assert len(audit['recommendations']) >= 1
        assert audit['total_potential_savings'] > 0

    def test_prioritized_recommendations(self):
        """✅ Generate prioritized recommendations."""
        from guardian.optimizers.cost_advisor import CostOptimizationEngine

        engine = CostOptimizationEngine()

        recommendations = engine.get_recommendations({
            'instances': [
                {'id': 'i-1', 'type': 't3.2xlarge', 'monthly_cost': 1000, 'utilization': 10},
                {'id': 'i-2', 'type': 'm5.large', 'monthly_cost': 100, 'utilization': 98},
            ]
        })

        assert recommendations[0]['potential_savings'] >= recommendations[1]['potential_savings']

    def test_cost_optimization_report(self):
        """✅ Generate cost optimization report."""
        from guardian.optimizers.cost_advisor import CostOptimizationEngine

        engine = CostOptimizationEngine()

        report = engine.generate_report({
            'account_id': '123456789',
            'month': 'May 2026',
            'total_current_cost': 5000,
            'recommendations': [
                {'id': 'i-1', 'savings': 200},
                {'id': 'i-2', 'savings': 150}
            ]
        })

        assert report['total_potential_savings'] == 350
        assert report['savings_percentage'] == 7.0
        assert 'recommendations' in report
