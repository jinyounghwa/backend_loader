"""Sprint 69 Phase 3: Predictive Cost Management (15 tests)"""

import pytest
import numpy as np


class TestInstanceSizing:
    """Test EC2 instance right-sizing."""

    def test_right_size_overprovisioned_instance(self):
        """✅ Recommend downsizing overprovisioned instance."""
        from guardian.optimizers.cost_optimizer import InstanceSizer

        sizer = InstanceSizer()
        current = {
            'type': 't3.xlarge',
            'monthly_cost': 131,
            'avg_cpu_usage': 15,
            'avg_memory_usage': 20
        }

        recommendation = sizer.recommend(current)

        assert recommendation['recommended_type'] != 't3.xlarge'
        assert recommendation['monthly_savings'] > 0

    def test_instance_sizing_with_different_families(self):
        """✅ Recommend across instance families."""
        from guardian.optimizers.cost_optimizer import InstanceSizer

        sizer = InstanceSizer()
        current = {
            'type': 'm5.xlarge',
            'monthly_cost': 192,
            'avg_cpu_usage': 20,
            'avg_memory_usage': 25
        }

        recommendation = sizer.recommend(current)

        assert 'recommended_type' in recommendation
        assert 'monthly_savings' in recommendation

    def test_no_downsize_needed(self):
        """✅ Keep current size if well-sized."""
        from guardian.optimizers.cost_optimizer import InstanceSizer

        sizer = InstanceSizer()
        current = {
            'type': 't3.medium',
            'monthly_cost': 32,
            'avg_cpu_usage': 70,
            'avg_memory_usage': 75
        }

        recommendation = sizer.recommend(current)

        assert recommendation['action'] == 'no_change'
        assert recommendation['monthly_savings'] == 0


class TestRIPurchase:
    """Test Reserved Instance recommendations."""

    def test_recommend_ri_for_high_uptime(self):
        """✅ Recommend RI for high uptime instances."""
        from guardian.optimizers.cost_optimizer import RIPurchaseAdvisor

        advisor = RIPurchaseAdvisor()
        instances = [{
            'type': 't3.medium',
            'monthly_cost': 32,
            'uptime_percentage': 95
        }]

        recommendations = advisor.recommend_ri_purchases(instances)

        assert len(recommendations) > 0
        assert recommendations[0]['one_year_savings'] > 0

    def test_no_ri_for_low_uptime(self):
        """✅ Don't recommend RI for low uptime instances."""
        from guardian.optimizers.cost_optimizer import RIPurchaseAdvisor

        advisor = RIPurchaseAdvisor()
        instances = [{
            'type': 't3.medium',
            'monthly_cost': 32,
            'uptime_percentage': 50
        }]

        recommendations = advisor.recommend_ri_purchases(instances)

        assert len(recommendations) == 0

    def test_three_year_better_than_one_year(self):
        """✅ Three-year RI provides greater savings."""
        from guardian.optimizers.cost_optimizer import RIPurchaseAdvisor

        advisor = RIPurchaseAdvisor()
        instances = [{
            'type': 't3.medium',
            'monthly_cost': 32,
            'uptime_percentage': 90
        }]

        recommendations = advisor.recommend_ri_purchases(instances)

        assert recommendations[0]['three_year_savings'] > recommendations[0]['one_year_savings']


class TestSpotStrategy:
    """Test Spot instance strategies."""

    def test_spot_instance_savings(self):
        """✅ Calculate Spot instance savings."""
        from guardian.optimizers.cost_optimizer import SpotInstanceStrategy

        strategy = SpotInstanceStrategy()
        instances = [{
            'type': 't3.medium',
            'monthly_cost': 32
        }]

        recommendations = strategy.recommend_spot_instances(instances)

        assert len(recommendations) > 0
        assert recommendations[0]['monthly_savings'] > 0

    def test_spot_discount_by_family(self):
        """✅ Apply correct discount rate by instance family."""
        from guardian.optimizers.cost_optimizer import SpotInstanceStrategy

        strategy = SpotInstanceStrategy()
        instances = [
            {'type': 't3.medium', 'monthly_cost': 32},
            {'type': 'c5.large', 'monthly_cost': 85}
        ]

        recommendations = strategy.recommend_spot_instances(instances)

        # c5 should have 75% discount, t3 should have 70%
        assert recommendations[0]['discount_percentage'] == 70.0
        assert recommendations[1]['discount_percentage'] == 75.0

    def test_blended_spot_strategy(self):
        """✅ Calculate blended Spot + On-Demand strategy."""
        from guardian.optimizers.cost_optimizer import SpotInstanceStrategy

        strategy = SpotInstanceStrategy()
        instances = [
            {'monthly_cost': 100},
            {'monthly_cost': 200}
        ]

        result = strategy.blended_strategy(instances)

        assert result['on_demand_percentage'] == 30
        assert result['spot_percentage'] == 70
        assert result['monthly_savings'] > 0


class TestAutoScaling:
    """Test auto-scaling recommendations."""

    def test_predict_peak_load(self):
        """✅ Predict future peak load."""
        from guardian.optimizers.scaling_advisor import LoadPredictor

        predictor = LoadPredictor()
        load_history = [50 + i for i in range(30)]

        predictor.fit(load_history)
        peak = predictor.predict_peak_load(hours_ahead=24)

        assert peak > 50

    def test_detect_seasonality(self):
        """✅ Detect seasonal patterns in load."""
        from guardian.optimizers.scaling_advisor import LoadPredictor

        predictor = LoadPredictor()
        # Create weekly pattern
        load_history = []
        for _ in range(4):
            load_history.extend([20, 30, 40, 50, 60, 70, 80])

        predictor.fit(load_history)
        seasonality = predictor.detect_seasonality()

        assert 'has_seasonality' in seasonality

    def test_recommend_scaling_policy(self):
        """✅ Recommend auto-scaling policy."""
        from guardian.optimizers.scaling_advisor import AutoScalingAdvisor

        advisor = AutoScalingAdvisor()
        load_history = [40 + i * 0.5 for i in range(50)]

        policy = advisor.recommend_policy(load_history)

        assert 'min_instances' in policy
        assert 'max_instances' in policy
        assert policy['max_instances'] >= policy['min_instances']


class TestCostSimulation:
    """Test cost impact simulation."""

    def test_simulate_instance_resize(self):
        """✅ Simulate cost of instance resize."""
        from guardian.optimizers.scaling_advisor import CostSimulator

        simulator = CostSimulator()
        changes = {
            'current_monthly_cost': 131,
            'instance_type': 't3.xlarge',
            'new_instance_type': 't3.medium',
            'purchase_model': 'on_demand'
        }

        result = simulator.simulate(changes)

        assert result['new_cost'] < result['current_cost']
        assert result['monthly_savings'] > 0

    def test_simulate_reserved_instance_purchase(self):
        """✅ Simulate RI purchase impact."""
        from guardian.optimizers.scaling_advisor import CostSimulator

        simulator = CostSimulator()
        changes = {
            'current_monthly_cost': 100,
            'instance_type': 't3.medium',
            'new_instance_type': 't3.medium',
            'purchase_model': 'reserved',
            'term': 3
        }

        result = simulator.simulate(changes)

        assert result['new_cost'] < result['current_cost']

    def test_simulate_spot_conversion(self):
        """✅ Simulate Spot instance conversion impact."""
        from guardian.optimizers.scaling_advisor import CostSimulator

        simulator = CostSimulator()
        changes = {
            'current_monthly_cost': 100,
            'instance_type': 't3.medium',
            'new_instance_type': 't3.medium',
            'purchase_model': 'spot'
        }

        result = simulator.simulate(changes)

        assert result['monthly_savings'] > 0
        assert result['monthly_savings'] > 50  # Spot is significant savings
