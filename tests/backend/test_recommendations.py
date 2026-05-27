"""Tests for Sprint 64 Phase 2 - ML-Based Recommendations Engine."""

import pytest


# ==========================================
# RecommendationEngine Tests
# ==========================================


class TestRecommendationEngine:
    """Test RecommendationEngine functionality."""

    @pytest.fixture
    def recommendation_engine(self):
        """Create a RecommendationEngine instance."""
        from guardian.analytics.recommendation_engine import RecommendationEngine

        return RecommendationEngine()

    def test_analyze_cost_patterns(self, recommendation_engine):
        """Test cost pattern analysis (peaks, troughs, volatility)."""
        # Generate seasonal cost data
        values = []
        for month in range(24):
            # Pattern: high in Q4, low in Q2
            if month % 12 in [9, 10, 11]:  # Q4
                base = 1500.0
            else:
                base = 1000.0
            noise = month * 5.0  # Slight upward trend
            values.append(base + noise)

        analysis = recommendation_engine.analyze_cost_patterns(values, period=12)

        assert analysis is not None
        assert "peak_periods" in analysis
        assert "off_peak_periods" in analysis
        assert "volatility_score" in analysis
        assert "average_cost" in analysis
        assert "min_cost" in analysis
        assert "max_cost" in analysis
        assert len(analysis["peak_periods"]) > 0
        assert len(analysis["off_peak_periods"]) > 0
        assert analysis["volatility_score"] >= 0
        assert analysis["max_cost"] >= analysis["min_cost"]

    def test_identify_opportunities(self, recommendation_engine):
        """Test identifying cost optimization opportunities."""
        # Multiple services with different cost patterns
        services_costs = {
            "ec2": [1000.0 + i * 50 for i in range(24)],  # High volatility (rising trend)
            "rds": [500.0] * 24,  # Stable
            "s3": [100.0 + (i % 12) * 30 for i in range(24)],  # Seasonal
        }

        # Seasonality info from Phase 1
        seasonality = {"is_seasonal": True, "strength": 0.6, "seasonal_period": 12}

        opportunities = recommendation_engine.identify_opportunities(services_costs, seasonality)

        assert opportunities is not None
        assert len(opportunities) > 0
        for opp in opportunities:
            assert "service" in opp
            assert "opportunity_type" in opp
            assert "savings_estimate" in opp
            assert "confidence" in opp
            assert 0 <= opp["confidence"] <= 1.0

    def test_generate_recommendations(self, recommendation_engine):
        """Test generating actionable recommendations."""
        analysis = {
            "average_cost": 1200.0,
            "volatility": 0.35,
        }

        opportunities = [
            {
                "service": "ec2",
                "opportunity_type": "reserved_instances",
                "savings_estimate": 300.0,
                "confidence": 0.85,
            },
            {
                "service": "s3",
                "opportunity_type": "scheduled_scaling",
                "savings_estimate": 50.0,
                "confidence": 0.70,
            },
        ]

        recommendations = recommendation_engine.generate_recommendations(analysis, opportunities)

        assert recommendations is not None
        assert len(recommendations) == 2
        for rec in recommendations:
            assert "recommendation_id" in rec
            assert "service" in rec
            assert "action" in rec
            assert "monthly_savings" in rec
            assert "annual_savings" in rec
            assert "implementation_effort" in rec
            assert "confidence" in rec
            assert "status" in rec
            # Verify annual_savings = monthly_savings * 12
            assert (
                abs(rec["annual_savings"] - rec["monthly_savings"] * 12) < 0.1
            )

    def test_calculate_roi(self, recommendation_engine):
        """Test ROI calculation for recommendations."""
        recommendation = {
            "monthly_savings": 500.0,
            "annual_savings": 6000.0,
        }

        # Test with upfront cost
        roi = recommendation_engine.calculate_roi(recommendation, upfront_cost=2000.0)

        assert roi is not None
        assert "payback_months" in roi
        assert "annual_savings" in roi
        assert "roi_percent" in roi
        # ROI = 6000 / 2000 * 100 = 300%
        assert roi["payback_months"] == 4.0  # 2000 / 500
        assert roi["roi_percent"] == 300.0

        # Test without upfront cost
        roi_no_upfront = recommendation_engine.calculate_roi(recommendation, upfront_cost=0)
        assert roi_no_upfront["payback_months"] == 0
        assert roi_no_upfront["roi_percent"] == 0.0

    def test_prioritize_recommendations(self, recommendation_engine):
        """Test recommendation prioritization by impact and feasibility."""
        recommendations = [
            {
                "recommendation_id": "rec1",
                "service": "ec2",
                "annual_savings": 6000.0,
                "confidence": 0.90,
                "implementation_effort": "low",
                "priority_score": 0.0,  # Will be calculated
            },
            {
                "recommendation_id": "rec2",
                "service": "rds",
                "annual_savings": 2400.0,
                "confidence": 0.85,
                "implementation_effort": "medium",
                "priority_score": 0.0,
            },
            {
                "recommendation_id": "rec3",
                "service": "s3",
                "annual_savings": 1200.0,
                "confidence": 0.70,
                "implementation_effort": "high",
                "priority_score": 0.0,
            },
        ]

        prioritized = recommendation_engine.prioritize_recommendations(recommendations)

        assert prioritized is not None
        assert len(prioritized) == 3
        # Verify priority scores are calculated
        for rec in prioritized:
            assert "priority_score" in rec
            assert rec["priority_score"] > 0
        # Verify sorted by priority (highest first)
        for i in range(len(prioritized) - 1):
            assert (
                prioritized[i]["priority_score"]
                >= prioritized[i + 1]["priority_score"]
            )


# ==========================================
# ServiceOptimizer Tests (Placeholder)
# ==========================================


class TestServiceOptimizer:
    """Test ServiceOptimizer functionality."""

    @pytest.fixture
    def service_optimizer(self):
        """Create a ServiceOptimizer instance."""
        from guardian.analytics.service_optimizer import ServiceOptimizer

        return ServiceOptimizer()

    def test_optimize_ec2(self, service_optimizer):
        """Test EC2 optimization strategies."""
        instance_data = [
            {"instance_id": "i-001", "type": "t3.medium", "region": "us-east-1"},
            {"instance_id": "i-002", "type": "m5.large", "region": "us-west-2"},
        ]
        cost_history = [500.0 + i * 10 for i in range(12)]

        recommendations = service_optimizer.optimize_ec2(instance_data, cost_history)

        assert recommendations is not None
        assert len(recommendations) >= 2
        for rec in recommendations:
            assert "service" in rec
            assert rec["service"] == "ec2"
            assert "optimization_type" in rec
            assert "monthly_savings" in rec
            assert "confidence" in rec
            assert rec["monthly_savings"] >= 0

    def test_optimize_rds(self, service_optimizer):
        """Test RDS optimization strategies."""
        database_data = [
            {"db_instance": "prod-db", "class": "db.m5.large"},
            {"db_instance": "staging-db", "class": "db.t3.medium"},
        ]
        cost_history = [300.0 + i * 5 for i in range(12)]

        recommendations = service_optimizer.optimize_rds(database_data, cost_history)

        assert recommendations is not None
        assert len(recommendations) >= 2
        for rec in recommendations:
            assert rec["service"] == "rds"
            assert "monthly_savings" in rec
            assert rec["monthly_savings"] >= 0

    def test_optimize_s3(self, service_optimizer):
        """Test S3 optimization strategies."""
        bucket_data = [
            {"bucket_name": "data-bucket", "size_gb": 500},
            {"bucket_name": "logs-bucket", "size_gb": 1000},
        ]
        cost_history = [150.0 + i * 2 for i in range(12)]

        recommendations = service_optimizer.optimize_s3(bucket_data, cost_history)

        assert recommendations is not None
        assert len(recommendations) >= 2
        for rec in recommendations:
            assert rec["service"] == "s3"
            assert "monthly_savings" in rec

    def test_optimize_lambda(self, service_optimizer):
        """Test Lambda optimization strategies."""
        invocation_data = [
            {"function_name": "api-handler", "memory_mb": 512},
            {"function_name": "scheduler", "memory_mb": 256},
        ]
        cost_history = [80.0 + i * 1 for i in range(12)]

        recommendations = service_optimizer.optimize_lambda(invocation_data, cost_history)

        assert recommendations is not None
        assert len(recommendations) >= 2
        for rec in recommendations:
            assert rec["service"] == "lambda"
            assert "monthly_savings" in rec

    def test_optimize_dynamodb(self, service_optimizer):
        """Test DynamoDB optimization strategies."""
        table_data = [
            {"table_name": "users", "billing_mode": "PROVISIONED"},
            {"table_name": "events", "billing_mode": "PAY_PER_REQUEST"},
        ]
        cost_history = [100.0 + i * 2 for i in range(12)]

        recommendations = service_optimizer.optimize_dynamodb(table_data, cost_history)

        assert recommendations is not None
        assert len(recommendations) >= 2
        for rec in recommendations:
            assert rec["service"] == "dynamodb"
            assert "monthly_savings" in rec

    def test_combined_optimization(self, service_optimizer):
        """Test multi-service optimization."""
        services_data = {
            "ec2": [{"instance_id": "i-001", "type": "t3.medium"}],
            "rds": [{"db_instance": "prod-db", "class": "db.m5.large"}],
            "s3": [{"bucket_name": "data-bucket", "size_gb": 500}],
        }
        costs_by_service = {
            "ec2": [500.0] * 12,
            "rds": [300.0] * 12,
            "s3": [150.0] * 12,
        }

        combined = service_optimizer.combined_optimization(services_data, costs_by_service)

        assert combined is not None
        assert "total_recommendations" in combined
        assert "total_monthly_savings" in combined
        assert "total_annual_savings" in combined
        assert "recommendations" in combined
        assert combined["total_annual_savings"] == combined["total_monthly_savings"] * 12
        assert combined["total_monthly_savings"] > 0

    def test_optimization_validation(self, service_optimizer):
        """Test feasibility validation."""
        recommendation = {
            "recommendation_id": "rec-001",
            "service": "ec2",
            "optimization_type": "reserved_instances",
            "confidence": 0.90,
            "implementation_effort": "medium",
            "monthly_savings": 300.0,
        }

        constraints = {
            "sla_availability": 0.99,
            "max_implementation_effort": "high",
            "max_upfront_cost": 10000.0,
        }

        validation = service_optimizer.optimization_validation(recommendation, constraints)

        assert validation is not None
        assert "feasibility_score" in validation
        assert "is_feasible" in validation
        assert "warnings" in validation
        assert "errors" in validation
        assert 0 <= validation["feasibility_score"] <= 1.0


# ==========================================
# ImpactCalculator Tests (Placeholder)
# ==========================================


class TestImpactCalculator:
    """Test ImpactCalculator functionality."""

    @pytest.fixture
    def impact_calculator(self):
        """Create an ImpactCalculator instance."""
        from guardian.analytics.impact_calculator import ImpactCalculator

        return ImpactCalculator()

    def test_estimate_savings(self, impact_calculator):
        """Test savings estimation for different optimization types."""
        # Test Reserved Instances
        savings_ri = impact_calculator.estimate_savings(1000.0, "reserved_instances")

        assert savings_ri is not None
        assert "monthly_savings" in savings_ri
        assert "annual_savings" in savings_ri
        assert "savings_percent" in savings_ri
        assert "confidence" in savings_ri
        assert savings_ri["monthly_savings"] == 400.0  # 40% savings
        assert savings_ri["annual_savings"] == 4800.0
        assert 0 <= savings_ri["confidence"] <= 1.0

        # Test Spot Instances (higher savings, lower confidence)
        savings_spot = impact_calculator.estimate_savings(1000.0, "spot_instances")
        assert savings_spot["monthly_savings"] == 700.0  # 70% savings
        assert savings_spot["confidence"] < savings_ri["confidence"]

        # Test unknown type (default)
        savings_default = impact_calculator.estimate_savings(1000.0, "unknown_optimization")
        assert savings_default["monthly_savings"] > 0
        assert savings_default["monthly_savings"] < savings_ri["monthly_savings"]

    def test_calculate_breakeven(self, impact_calculator):
        """Test financial analysis (breakeven, NPV, IRR)."""
        # Test case: $5000 upfront cost, $500/month savings
        breakeven = impact_calculator.calculate_breakeven(
            upfront_cost=5000.0,
            monthly_savings=500.0,
            discount_rate=0.05,
            analysis_period_months=36,
        )

        assert breakeven is not None
        assert "payback_months" in breakeven
        assert "npv" in breakeven
        assert "irr_percent" in breakeven
        assert "net_savings_after_cost" in breakeven
        assert "is_profitable" in breakeven

        # Verify calculations
        assert breakeven["payback_months"] == 10.0  # 5000 / 500
        assert breakeven["annual_savings"] == 6000.0
        assert breakeven["npv"] > 0  # Should be positive after 36 months
        assert breakeven["irr_percent"] == 120.0  # (6000 / 5000) * 100
        assert breakeven["is_profitable"] is True

        # Test case: no upfront cost
        breakeven_free = impact_calculator.calculate_breakeven(
            upfront_cost=0.0, monthly_savings=500.0
        )
        assert breakeven_free["payback_months"] == 0.0
        assert breakeven_free["irr_percent"] == 0.0
