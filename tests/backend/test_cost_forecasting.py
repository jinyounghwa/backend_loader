"""Tests for Phase 3 Cost Analytics (Cost Forecasting, Savings Analysis, Spike Detection)."""

import pytest


# ==========================================
# CostForecaster Tests
# ==========================================


class TestCostForecaster:
    """Test CostForecaster functionality."""

    @pytest.fixture
    def cost_forecaster(self):
        """Create a CostForecaster instance."""
        from guardian.analytics.cost_forecaster import CostForecaster

        return CostForecaster()

    def test_forecast_daily_cost(self, cost_forecaster):
        """Test daily cost forecasting with trend calculation."""
        historical_costs = [
            (100.0, "2026-05-27T00:00:00Z"),
            (110.0, "2026-05-26T00:00:00Z"),
            (105.0, "2026-05-25T00:00:00Z"),
        ]

        result = cost_forecaster.forecast_daily_cost(historical_costs, days=5)

        assert result["forecast_available"] is True
        assert "mean_historical_cost" in result
        assert "trend" in result
        assert "forecasts" in result
        assert len(result["forecasts"]) == 5

        # Check forecast structure
        for forecast in result["forecasts"]:
            assert "day" in forecast
            assert "forecast" in forecast
            assert "lower_bound" in forecast
            assert "upper_bound" in forecast
            assert "confidence" in forecast
            assert forecast["lower_bound"] <= forecast["forecast"] <= forecast["upper_bound"]

    def test_forecast_monthly_cost(self, cost_forecaster):
        """Test monthly cost aggregation from daily forecasts."""
        daily_forecasts = {
            "forecasts": [
                {"forecast": 100.0, "lower_bound": 90.0, "upper_bound": 110.0},
                {"forecast": 102.0, "lower_bound": 92.0, "upper_bound": 112.0},
                {"forecast": 104.0, "lower_bound": 94.0, "upper_bound": 114.0},
            ]
        }

        result = cost_forecaster.forecast_monthly_cost(daily_forecasts)

        assert result["forecast_available"] is True
        assert "total_forecast" in result
        assert "daily_average" in result
        assert "min_daily" in result
        assert "max_daily" in result
        assert "lower_bound_total" in result
        assert "upper_bound_total" in result
        assert "days_forecasted" in result
        assert result["total_forecast"] == pytest.approx(306.0, rel=0.01)

    def test_predict_cost_after_action(self, cost_forecaster):
        """Test cost projections after optimization actions."""
        current_costs = [100.0, 110.0, 105.0, 115.0, 120.0]

        result = cost_forecaster.predict_cost_after_action(
            current_costs, action_type="stop_ec2", action_impact=0.3
        )

        assert "action_type" in result
        assert result["action_type"] == "stop_ec2"
        assert "current_daily_average" in result
        assert "projected_daily_average" in result
        assert "daily_savings" in result
        assert "current_monthly_cost" in result
        assert "projected_monthly_cost" in result
        assert "monthly_savings" in result
        assert "annual_savings" in result
        assert "impact_percentage" in result
        assert result["impact_percentage"] == 30.0

        # Verify savings calculation
        assert result["projected_daily_average"] == pytest.approx(
            result["current_daily_average"] * 0.7, rel=0.01
        )

    def test_estimate_savings_potential(self, cost_forecaster):
        """Test identification of optimization opportunities."""
        costs_by_service = {
            "ec2": 1000.0,
            "rds": 500.0,
            "s3": 200.0,
            "nat_gateway": 100.0,
            "cloudwatch": 50.0,
            "elastic_ip": 10.0,
        }

        result = cost_forecaster.estimate_savings_potential(costs_by_service)

        assert len(result) > 0
        # Verify sorted by potential savings
        assert all(
            result[i]["max_potential_savings"] >= result[i + 1]["max_potential_savings"]
            for i in range(len(result) - 1)
        )

        # Check structure
        for opportunity in result:
            assert "service" in opportunity
            assert "current_cost" in opportunity
            assert "max_potential_savings" in opportunity
            assert "savings_percentage" in opportunity
            assert "reason" in opportunity
            assert "impact" in opportunity
            assert opportunity["impact"] in ["HIGH", "MEDIUM", "LOW"]

    def test_calculate_breakeven(self, cost_forecaster):
        """Test ROI and break-even analysis for investments."""
        result = cost_forecaster.calculate_breakeven(upfront_cost=5000.0, monthly_savings=500.0)

        assert result["breakeven_available"] is True
        assert "upfront_cost" in result
        assert "monthly_savings" in result
        assert "breakeven_months" in result
        assert "annual_benefit" in result
        assert "roi_percent" in result
        assert "payback_feasible" in result
        assert result["breakeven_months"] == pytest.approx(10.0, rel=0.01)
        assert result["payback_feasible"] is True

    def test_detect_cost_spike(self, cost_forecaster):
        """Test statistical spike detection using z-scores."""
        costs = [100.0, 105.0, 102.0, 103.0, 250.0, 101.0, 104.0]

        result = cost_forecaster.detect_cost_spike(costs, threshold=1.5)

        assert isinstance(result, list)
        # Should detect the spike at 250.0
        if result:
            spike = result[0]
            assert "day" in spike
            assert "cost" in spike
            assert "z_score" in spike
            assert "increase_percent" in spike
            assert "severity" in spike
            assert spike["severity"] in ["HIGH", "MEDIUM"]

    def test_get_forecast_summary(self, cost_forecaster):
        """Test comprehensive forecast summary generation."""
        historical_costs = [
            (100.0, "2026-05-27T00:00:00Z"),
            (110.0, "2026-05-26T00:00:00Z"),
            (105.0, "2026-05-25T00:00:00Z"),
            (115.0, "2026-05-24T00:00:00Z"),
        ]

        result = cost_forecaster.get_forecast_summary(historical_costs, days=5)

        assert result["forecast_available"] is True
        assert "daily" in result
        assert "monthly" in result
        assert "summary" in result
        assert result["summary"]["days_forecasted"] == 5
        assert "average_daily_forecast" in result["summary"]
        assert "projected_monthly" in result["summary"]


# ==========================================
# Integration Tests
# ==========================================


class TestCostAnalyticsIntegration:
    """Integration tests for cost analytics."""

    def test_complete_cost_forecasting_pipeline(self):
        """Test complete cost forecasting pipeline with all operations."""
        from guardian.analytics.cost_forecaster import CostForecaster

        forecaster = CostForecaster()

        # Step 1: Historical cost data
        historical_costs = [
            (100.0 + i * 5, f"2026-05-{27-i:02d}T00:00:00Z") for i in range(10)
        ]

        # Step 2: Get daily forecast
        daily_forecast = forecaster.forecast_daily_cost(historical_costs, days=7)
        assert daily_forecast["forecast_available"] is True

        # Step 3: Get monthly forecast
        monthly_forecast = forecaster.forecast_monthly_cost(daily_forecast)
        assert monthly_forecast["forecast_available"] is True

        # Step 4: Analyze cost spike
        costs = [float(c) for c, _ in historical_costs]
        spikes = forecaster.detect_cost_spike(costs)
        assert isinstance(spikes, list)

        # Step 5: Estimate savings opportunities
        services_costs = {"ec2": 500.0, "rds": 300.0, "s3": 100.0}
        opportunities = forecaster.estimate_savings_potential(services_costs)
        assert len(opportunities) > 0

        # Step 6: Project savings from action
        action_result = forecaster.predict_cost_after_action(costs, "reduce_nat", 0.5)
        assert action_result["monthly_savings"] > 0

        # Step 7: Calculate investment ROI
        roi_result = forecaster.calculate_breakeven(
            upfront_cost=2000.0, monthly_savings=action_result["daily_savings"] * 30
        )
        assert "breakeven_months" in roi_result
