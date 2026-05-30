"""Cost optimization AutoML tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestCostOptimizationML:
    """Test ML-based cost optimization recommendations."""

    def test_auto_recommendations(self):
        """✅ Generate auto recommendations."""
        from guardian.optimizers.automl_optimizer import CostOptimizationML

        optimizer = CostOptimizationML()

        recs = optimizer.auto_recommend({
            'account_id': '123456789',
            'lookback_days': 90,
            'confidence_threshold': 0.8
        })

        assert isinstance(recs, list)
        assert len(recs) >= 3
        assert all(r['confidence'] >= 0.8 for r in recs)

    def test_instance_rightsizing_recommendation(self):
        """✅ Recommend right-sized instances."""
        from guardian.optimizers.automl_optimizer import CostOptimizationML

        optimizer = CostOptimizationML()

        recs = optimizer.auto_recommend({
            'account_id': '123456789',
            'filters': {'recommendation_type': 'INSTANCE_RIGHTSIZING'},
            'lookback_days': 90
        })

        assert any(r['type'] == 'INSTANCE_RIGHTSIZING' for r in recs)

    def test_reserved_instance_recommendations(self):
        """✅ Recommend reserved instance purchases."""
        from guardian.optimizers.automl_optimizer import CostOptimizationML

        optimizer = CostOptimizationML()

        recs = optimizer.auto_recommend({
            'account_id': '123456789',
            'filters': {'recommendation_type': 'RESERVED_INSTANCE'},
            'lookback_days': 365
        })

        assert any(r.get('type') == 'RESERVED_INSTANCE' for r in recs)

    def test_savings_calculation(self):
        """✅ Calculate potential savings."""
        from guardian.optimizers.automl_optimizer import SaveingsCalculator

        calculator = SaveingsCalculator()

        savings = calculator.calculate({
            'current_monthly_cost': 1000.00,
            'optimization_type': 'INSTANCE_RIGHTSIZING',
            'reduction_percentage': 30
        })

        assert 'monthly_savings' in savings
        assert 'annual_savings' in savings
        assert savings['monthly_savings'] == 300.00
        assert savings['annual_savings'] == 3600.00

    def test_roi_calculation(self):
        """✅ Calculate ROI for optimization."""
        from guardian.optimizers.automl_optimizer import SaveingsCalculator

        calculator = SaveingsCalculator()

        roi = calculator.calculate_roi({
            'annual_savings': 3600.00,
            'implementation_cost': 500.00
        })

        assert 'roi_percentage' in roi
        assert roi['roi_percentage'] == 620.0

    def test_payback_period(self):
        """✅ Calculate payback period."""
        from guardian.optimizers.automl_optimizer import SaveingsCalculator

        calculator = SaveingsCalculator()

        payback = calculator.calculate_payback({
            'monthly_savings': 300.00,
            'implementation_cost': 500.00
        })

        assert 'payback_months' in payback
        assert payback['payback_months'] >= 1.5


class TestOptimizationExecutor:
    """Test optimization execution."""

    def test_execute_optimization(self):
        """✅ Execute optimization."""
        from guardian.optimizers.automl_optimizer import OptimizationExecutor

        executor = OptimizationExecutor()

        result = executor.execute({
            'recommendation_id': 'rec-123',
            'optimization_type': 'INSTANCE_RIGHTSIZING',
            'instance_id': 'i-12345',
            'new_instance_type': 't3.medium'
        })

        assert result['status'] == 'executed'
        assert 'execution_id' in result

    def test_optimization_dry_run(self):
        """✅ Perform dry-run before optimization."""
        from guardian.optimizers.automl_optimizer import OptimizationExecutor

        executor = OptimizationExecutor()

        result = executor.execute_dry_run({
            'recommendation_id': 'rec-123',
            'optimization_type': 'INSTANCE_RIGHTSIZING'
        })

        assert result['status'] == 'dry_run_complete'
        assert 'impact_summary' in result

    def test_optimization_rollback(self):
        """✅ Rollback failed optimization."""
        from guardian.optimizers.automl_optimizer import OptimizationExecutor

        executor = OptimizationExecutor()

        # Execute optimization
        result = executor.execute({
            'recommendation_id': 'rec-123',
            'optimization_type': 'TEST',
            'instance_id': 'i-12345'
        })

        # Rollback
        rollback = executor.rollback(result['execution_id'])

        assert rollback['status'] == 'rolled_back'


class TestOptimizationTracker:
    """Test optimization tracking and monitoring."""

    def test_track_optimization(self):
        """✅ Track optimization execution."""
        from guardian.optimizers.automl_optimizer import OptimizationTracker

        tracker = OptimizationTracker()

        tracked = tracker.track({
            'recommendation_id': 'rec-123',
            'optimization_type': 'INSTANCE_RIGHTSIZING',
            'expected_savings': 300.00
        })

        assert 'tracking_id' in tracked
        assert tracked['status'] == 'tracking'

    def test_measure_impact(self):
        """✅ Measure optimization impact."""
        from guardian.optimizers.automl_optimizer import OptimizationTracker

        tracker = OptimizationTracker()

        impact = tracker.measure_impact({
            'recommendation_id': 'rec-123',
            'days_since_optimization': 30,
            'actual_savings': 290.00,
            'expected_savings': 300.00
        })

        assert 'savings_variance' in impact
        assert 'roi_actual' in impact

    def test_optimization_history(self):
        """✅ Track optimization history."""
        from guardian.optimizers.automl_optimizer import OptimizationTracker

        tracker = OptimizationTracker()

        # Track multiple optimizations
        for i in range(3):
            tracker.track({
                'recommendation_id': f'rec-{i}',
                'optimization_type': 'INSTANCE_RIGHTSIZING',
                'expected_savings': 100.00 * (i + 1)
            })

        history = tracker.get_history({
            'lookback_days': 90,
            'account_id': '123456789'
        })

        assert len(history) >= 3


class TestAutoMLIntegration:
    """End-to-end AutoML optimization workflows."""

    def test_full_optimization_workflow(self):
        """✅ Complete workflow: recommend → calculate → execute → track."""
        from guardian.optimizers.automl_optimizer import (
            CostOptimizationML,
            SaveingsCalculator,
            OptimizationExecutor,
            OptimizationTracker
        )

        optimizer = CostOptimizationML()
        calculator = SaveingsCalculator()
        executor = OptimizationExecutor()
        tracker = OptimizationTracker()

        # Step 1: Get recommendations
        recs = optimizer.auto_recommend({
            'account_id': '123456789',
            'lookback_days': 90,
            'confidence_threshold': 0.8
        })

        assert len(recs) > 0
        rec = recs[0]

        # Step 2: Calculate savings
        savings = calculator.calculate({
            'current_monthly_cost': 1000.00,
            'optimization_type': rec['type'],
            'reduction_percentage': 30
        })

        assert savings['monthly_savings'] > 0

        # Step 3: Execute optimization
        result = executor.execute({
            'recommendation_id': rec['id'],
            'optimization_type': rec['type']
        })

        assert result['status'] == 'executed'

        # Step 4: Track impact
        tracked = tracker.track({
            'recommendation_id': rec['id'],
            'optimization_type': rec['type'],
            'expected_savings': savings['monthly_savings']
        })

        assert tracked['status'] == 'tracking'

    def test_batch_recommendations(self):
        """✅ Generate batch recommendations for multiple resources."""
        from guardian.optimizers.automl_optimizer import CostOptimizationML

        optimizer = CostOptimizationML()

        recs = optimizer.auto_recommend({
            'account_id': '123456789',
            'batch_mode': True,
            'max_recommendations': 10,
            'lookback_days': 90
        })

        assert len(recs) <= 10
        assert all('confidence' in r for r in recs)

    def test_recommendation_prioritization(self):
        """✅ Prioritize recommendations by impact."""
        from guardian.optimizers.automl_optimizer import CostOptimizationML

        optimizer = CostOptimizationML()

        recs = optimizer.auto_recommend({
            'account_id': '123456789',
            'sort_by': 'impact',
            'lookback_days': 90
        })

        # Verify sorted by impact (highest first)
        for i in range(len(recs) - 1):
            assert recs[i].get('potential_savings', 0) >= recs[i+1].get('potential_savings', 0)

    def test_savings_aggregation(self):
        """✅ Aggregate savings across recommendations."""
        from guardian.optimizers.automl_optimizer import CostOptimizationML

        optimizer = CostOptimizationML()

        aggregated = optimizer.aggregate_savings({
            'account_id': '123456789',
            'lookback_days': 90
        })

        assert 'total_potential_savings' in aggregated
        assert 'by_type' in aggregated
        assert aggregated['total_potential_savings'] >= 0
