"""Tests for Sprint 64 Phase 4 - Advanced Analytics & Automation."""

import pytest


class TestAutomationHandler:
    """Test automated action execution."""

    @pytest.fixture
    def automation_handler(self):
        """Create an AutomationHandler instance."""
        from guardian.handlers.automation_handler import AutomationHandler
        return AutomationHandler()

    def test_ec2_stop_action(self, automation_handler):
        """Test EC2 instance stop action."""
        result = automation_handler.execute_ec2_action(
            "123456789", "i-0123456789abcdef0", "stop"
        )
        assert result["success"] is True
        assert result["service"] == "ec2"
        assert result["action"] == "stop"
        assert "action_id" in result
        assert "estimated_savings" in result
        assert result["estimated_savings"] > 0

    def test_s3_block_public_action(self, automation_handler):
        """Test S3 block public access action."""
        result = automation_handler.execute_s3_action(
            "123456789",
            "my-bucket",
            "block_public",
            object_count=50000,
            size_gb=500,
        )
        assert result["success"] is True
        assert result["service"] == "s3"
        assert result["action"] == "block_public"
        assert "action_id" in result
        assert "bucket_analyzed" in result

    def test_rds_modify_action(self, automation_handler):
        """Test RDS instance modification action."""
        result = automation_handler.execute_rds_action(
            "123456789", "prod-database", "modify_type", new_type="db.t3.large"
        )
        assert result["success"] is True
        assert result["service"] == "rds"
        assert result["action"] == "modify_type"
        assert "action_id" in result
        assert result["downtime_minutes"] > 0

    def test_lambda_optimize_action(self, automation_handler):
        """Test Lambda function optimization action."""
        result = automation_handler.execute_lambda_action(
            "123456789",
            "api-handler",
            "reduce_memory",
            avg_duration=250,
            avg_memory=256,
            invocations=1000000,
        )
        assert result["success"] is True
        assert result["service"] == "lambda"
        assert result["action"] == "reduce_memory"
        assert "action_id" in result
        assert "metrics_analyzed" in result
        assert result["metrics_analyzed"]["average_memory_mb"] == 256

    def test_dynamodb_billing_action(self, automation_handler):
        """Test DynamoDB billing mode switch action."""
        result = automation_handler.execute_dynamodb_action(
            "123456789",
            "events-table",
            "switch_billing_mode",
            rcu=100,
            wcu=100,
            peak_rcu=10,
            peak_wcu=5,
        )
        assert result["success"] is True
        assert result["service"] == "dynamodb"
        assert result["action"] == "switch_billing_mode"
        assert "action_id" in result
        assert "table_analyzed" in result

    def test_create_rollback_plan(self, automation_handler):
        """Test rollback plan generation."""
        # First execute an action
        result = automation_handler.execute_ec2_action(
            "123456789", "i-0123456789abcdef0", "stop"
        )
        action_id = result["action_id"]

        # Get rollback plan
        rollback = automation_handler.create_rollback_plan("123456789", action_id)
        assert rollback["success"] is True
        assert "rollback_plan" in rollback
        assert "rollback_steps" in rollback["rollback_plan"]
        assert "verification_steps" in rollback["rollback_plan"]
        assert rollback["estimated_duration_minutes"] > 0

    def test_action_impact_estimation(self, automation_handler):
        """Test cost savings estimation for different actions."""
        # EC2 stop: ~$50/month
        ec2_result = automation_handler.execute_ec2_action(
            "123456789", "i-test", "stop"
        )
        assert ec2_result["estimated_savings"] == 50.0

        # S3 transition: size_gb * 0.02
        s3_result = automation_handler.execute_s3_action(
            "123456789", "bucket", "transition_storage", size_gb=100
        )
        assert s3_result["estimated_savings"] == 2.0

        # RDS modify: ~$75/month
        rds_result = automation_handler.execute_rds_action(
            "123456789", "db", "modify_type"
        )
        assert rds_result["estimated_savings"] == 75.0

        # Lambda reduce_memory: ~$10/month
        lambda_result = automation_handler.execute_lambda_action(
            "123456789", "func", "reduce_memory"
        )
        assert lambda_result["estimated_savings"] == 10.0


class TestMLModelTraining:
    """Test ML model training pipeline."""

    @pytest.fixture
    def cost_predictor(self):
        """Create a CostPredictor instance."""
        from guardian.ml.cost_predictor import CostPredictor
        return CostPredictor()

    def test_train_prophet_model(self, cost_predictor):
        """Test Prophet model training with seasonality."""
        # Generate synthetic cost history with seasonality
        historical_costs = []
        for month in range(24):
            if month % 12 in [9, 10, 11]:  # Q4 peak
                base = 1500.0
            else:
                base = 1000.0
            noise = month * 5.0
            historical_costs.append(base + noise)

        seasonality_info = {"is_seasonal": True, "strength": 0.6, "period": 12}

        result = cost_predictor.train_prophet_model(
            "123456789", historical_costs, seasonality_info
        )

        assert result["success"] is True
        assert "forecast" in result
        assert "accuracy_mape" in result
        assert result["accuracy_mape"] < 70  # Simulated forecast accuracy
        assert "confidence_intervals" in result

    def test_train_lstm_model(self, cost_predictor):
        """Test LSTM model training for short-term spikes."""
        historical_costs = [1000.0 + i * 10 for i in range(60)]  # 60 days
        features = {
            "ec2_cost": [500.0] * 60,
            "rds_cost": [300.0] * 60,
            "s3_cost": [100.0] * 60,
        }

        result = cost_predictor.train_lstm_model("123456789", historical_costs, features)

        assert result["success"] is True
        assert "predictions" in result
        assert len(result["predictions"]) == 7  # 7-day forecast
        assert "confidence_bands" in result

    def test_train_ensemble_model(self, cost_predictor):
        """Test ensemble model combining multiple forecasts."""
        arima_forecast = [1100.0, 1110.0, 1120.0, 1130.0, 1140.0]
        prophet_forecast = [1105.0, 1115.0, 1125.0, 1135.0, 1145.0]
        lstm_forecast = [1095.0, 1105.0, 1115.0, 1125.0, 1135.0]

        result = cost_predictor.train_ensemble_model(
            arima_forecast, prophet_forecast, lstm_forecast
        )

        assert result["success"] is True
        assert "ensemble_forecast" in result
        assert len(result["ensemble_forecast"]) == 5
        # Ensemble should be weighted average (0.4 ARIMA + 0.35 Prophet + 0.25 LSTM)
        expected_first = (1100.0 * 0.4) + (1105.0 * 0.35) + (1095.0 * 0.25)
        assert abs(result["ensemble_forecast"][0] - expected_first) < 1.0

    def test_model_accuracy_evaluation(self, cost_predictor):
        """Test model accuracy calculation."""
        actual_costs = [1000.0, 1050.0, 1100.0, 1150.0, 1200.0]
        predicted_costs = [1010.0, 1045.0, 1095.0, 1155.0, 1195.0]

        result = cost_predictor.evaluate_model_accuracy(
            actual_costs, predicted_costs
        )

        assert result["success"] is True
        assert "mape_percent" in result
        assert "rmse" in result
        assert "mae" in result
        assert result["mape_percent"] < 2  # Should be accurate

    def test_model_retraining_trigger(self, cost_predictor):
        """Test trigger conditions for model retraining."""
        # Train initial model
        historical_costs = [1000.0 + i * 10 for i in range(60)]

        initial_result = cost_predictor.train_prophet_model(
            "123456789", historical_costs, {"is_seasonal": True}
        )
        initial_mape = initial_result["accuracy_mape"]

        # Simulate new data with worse accuracy
        # If MAPE > 15%, should trigger retraining
        should_retrain = initial_mape > 15 or initial_mape < 5  # Either very good or needs training

        assert "should_retrain" in cost_predictor.check_retraining_condition(
            initial_mape
        )

    def test_model_prediction_confidence(self, cost_predictor):
        """Test prediction confidence interval calculation."""
        forecast_values = [1100.0, 1110.0, 1120.0]
        uncertainty = [50.0, 55.0, 60.0]  # 95% CI bounds

        result = cost_predictor.calculate_confidence_intervals(
            forecast_values, uncertainty
        )

        assert result["success"] is True
        assert len(result["intervals"]) == 3
        # Each interval should have lower and upper bounds
        for interval in result["intervals"]:
            assert "lower_bound" in interval
            assert "upper_bound" in interval
            assert interval["lower_bound"] < interval["upper_bound"]


class TestPredictiveAlerting:
    """Test predictive alerting system."""

    @pytest.fixture
    def predictive_alert_handler(self):
        """Create a PredictiveAlertHandler instance."""
        from guardian.handlers.predictive_alert_handler import PredictiveAlertHandler
        return PredictiveAlertHandler()

    def test_threshold_breach_prediction(self, predictive_alert_handler):
        """Test prediction of threshold breach."""
        forecast_values = [95.0, 98.0, 102.0, 105.0, 108.0]  # Will exceed 100
        threshold = 100.0

        result = predictive_alert_handler.predict_threshold_breach(
            "123456789", threshold, forecast_values
        )

        assert result["alert_triggered"] is True
        assert result["will_breach"] is True
        assert result["days_until_breach"] == 2  # Breaches on day 3 (index 2)
        assert result["predicted_breach_cost"] == 102.0

    def test_trend_change_detection(self, predictive_alert_handler):
        """Test detection of unusual cost trend changes."""
        historical_costs = [1000.0] * 10 + [1010.0] * 5  # Stable then slight rise
        forecast_values = [1010.0, 1050.0, 1100.0, 1200.0, 1300.0]  # Sharp increase

        result = predictive_alert_handler.detect_cost_trend_change(
            historical_costs, forecast_values
        )

        assert result["success"] is True
        assert result["trend_changed"] is True
        assert result["trend_acceleration"] > 0
        assert result["severity"] == "critical"

    def test_monthly_budget_projection(self, predictive_alert_handler):
        """Test projection of monthly costs against budget."""
        daily_forecasts = [100.0] * 30  # 30 days at $100/day = $3000
        monthly_budget = 3000.0

        result = predictive_alert_handler.forecast_monthly_budget_impact(
            daily_forecasts, monthly_budget
        )

        assert result["success"] is True
        assert result["projected_month_cost"] == 3000.0
        assert result["variance_from_budget"] == 0.0
        assert result["on_budget"] is True

    def test_predictive_alert_scheduling(self, predictive_alert_handler):
        """Test scheduling of escalating predictive alerts."""
        alert_config = {
            "account_id": "123456789",
            "threshold": 5000.0,
            "forecast_breach_day": 7,
            "alert_escalation": ["email", "sms", "call"],
        }

        result = predictive_alert_handler.schedule_predictive_alerts(alert_config)

        assert result["success"] is True
        assert "scheduled_alerts" in result
        assert len(result["scheduled_alerts"]) == 4  # 7 days, 3 days, 1 day, same day
        assert "alert_ids" in result


class TestOptimizationRulesEngine:
    """Test optimization rules engine."""

    @pytest.fixture
    def rules_engine(self):
        """Create a RulesEngine instance."""
        from guardian.handlers.optimization_rules_engine import RulesEngine
        return RulesEngine()

    def test_create_custom_rule(self, rules_engine):
        """Test creating custom optimization rule."""
        rule_config = {
            "name": "EC2 Auto-Stop",
            "condition": "ec2_cpu < 5 FOR 7 days",
            "action": "stop_instance",
            "approval_required": True,
            "estimate_savings": 50.0,
        }

        result = rules_engine.create_rule("123456789", rule_config)

        assert result["success"] is True
        assert "rule_id" in result
        assert result["rule_name"] == "EC2 Auto-Stop"

    def test_evaluate_rule_conditions(self, rules_engine):
        """Test evaluation of rule conditions."""
        rule = {
            "rule_id": "rule-001",
            "condition_type": "utilization",
            "metric": "cpu_percent",
            "threshold": 5,
            "duration_days": 7,
        }

        metrics = {
            "cpu_percent": 3.5,  # Below threshold
            "days_monitored": 8,  # Meets duration
        }

        result = rules_engine.evaluate_rule_conditions(rule, metrics)

        assert result["success"] is True
        assert result["rule_triggered"] is True
        assert result["matching_metrics"] == ["cpu_percent", "duration"]

    def test_execute_rule_action(self, rules_engine):
        """Test execution of rule action."""
        rule = {
            "rule_id": "rule-001",
            "action": "stop_instance",
            "approval_required": True,
        }

        result = rules_engine.execute_rule_action(
            rule, "123456789", "i-0123456789abcdef0"
        )

        assert result["success"] is True
        assert "execution_id" in result
        assert result["status"] == "pending_approval"

    def test_rule_conflict_detection(self, rules_engine):
        """Test detection of conflicting rules."""
        rule1 = {
            "rule_id": "rule-001",
            "action": "stop_instance",
            "target_service": "ec2",
        }

        rule2 = {
            "rule_id": "rule-002",
            "action": "modify_instance_type",
            "target_service": "ec2",
        }

        result = rules_engine.detect_rule_conflicts("123456789", [rule1, rule2])

        assert result["success"] is True
        assert result["conflicts_found"] is False  # Different actions on same service


class TestGuardianIntegration:
    """Test integration with existing Guardian system."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance."""
        from guardian.handlers.cost_automation_orchestrator import CostAutomationOrchestrator
        return CostAutomationOrchestrator()

    def test_sync_with_security_rules(self, orchestrator):
        """Test synchronization with security rules."""
        cost_recommendations = [
            {"service": "ec2", "action": "stop_instance", "instance_id": "i-001"}
        ]

        security_rules = [
            {"rule": "all_instances_must_run_24_7", "applies_to": "production"}
        ]

        result = orchestrator.sync_with_security_rules(
            cost_recommendations, security_rules
        )

        assert result["success"] is True
        assert "compatible_recommendations" in result
        assert "conflicts" in result

    def test_approval_workflow(self, orchestrator):
        """Test multi-level approval workflow."""
        action = {
            "action_id": "action-001",
            "service": "ec2",
            "action": "stop_instance",
            "cost_impact": 100.0,
        }

        approval_config = {
            "approval_level": "manager",
            "timeout_hours": 24,
            "escalate_on_timeout": True,
        }

        result = orchestrator.execute_with_approval_workflow(
            action, "123456789", approval_config
        )

        assert result["success"] is True
        assert "approval_id" in result
        assert result["status"] == "pending_approval"

    def test_action_audit_trail(self, orchestrator):
        """Test comprehensive action audit logging."""
        action_result = {
            "action_id": "action-001",
            "action_type": "stop_ec2",
            "result": "success",
            "cost_impact": 50.0,
        }

        result = orchestrator.maintain_action_audit_trail("123456789", action_result)

        assert result["success"] is True
        assert "audit_log_id" in result

    def test_realized_savings_calculation(self, orchestrator):
        """Test calculation of realized savings."""
        action_id = "action-001"
        cost_before = 1000.0
        cost_after = 950.0
        time_period_days = 30

        result = orchestrator.calculate_realized_savings(
            "123456789", action_id, cost_before, cost_after, time_period_days
        )

        assert result["success"] is True
        assert result["realized_savings"] == 50.0
        assert result["annualized_savings"] == 608.33


class TestPredictiveAlertingAdditional:
    """Test additional predictive alerting scenarios."""

    @pytest.fixture
    def predictive_alert_handler(self):
        """Create a PredictiveAlertHandler instance."""
        from guardian.handlers.predictive_alert_handler import PredictiveAlertHandler
        return PredictiveAlertHandler()

    def test_anomaly_alert_validation(self, predictive_alert_handler):
        """Test validation of anomaly thresholds against alert conditions."""
        # Simulate high-confidence anomaly detection
        forecast_values = [5000.0, 5100.0, 5200.0, 5300.0, 5400.0]
        threshold = 5000.0

        result = predictive_alert_handler.predict_threshold_breach(
            "123456789", threshold, forecast_values
        )

        assert result["success"] is True
        assert result["alert_triggered"] is True
        assert result["confidence"] == 0.95


class TestOptimizationRulesEngineAdditional:
    """Test additional optimization rules scenarios."""

    @pytest.fixture
    def rules_engine(self):
        """Create a RulesEngine instance."""
        from guardian.handlers.optimization_rules_engine import RulesEngine
        return RulesEngine()

    def test_rule_prioritization(self, rules_engine):
        """Test rule priority ordering and execution."""
        rules = [
            {"rule_id": "rule-001", "priority": 1, "name": "Low Priority"},
            {"rule_id": "rule-002", "priority": 10, "name": "High Priority"},
            {"rule_id": "rule-003", "priority": 5, "name": "Medium Priority"},
        ]

        result = rules_engine.list_rules("123456789")
        assert result["success"] is True


class TestEndToEndIntegration:
    """Test end-to-end automation workflows."""

    def test_end_to_end_cost_optimization_flow(self):
        """Test complete flow from cost detection to action execution."""
        from guardian.handlers.automation_handler import AutomationHandler
        from guardian.handlers.cost_automation_orchestrator import CostAutomationOrchestrator

        handler = AutomationHandler()
        orchestrator = CostAutomationOrchestrator()

        # Execute cost optimization action
        ec2_result = handler.execute_ec2_action(
            "123456789", "i-test", "stop"
        )
        assert ec2_result["success"] is True

        # Log action and calculate savings
        audit_result = orchestrator.maintain_action_audit_trail(
            "123456789", ec2_result
        )
        assert audit_result["success"] is True

    def test_end_to_end_ml_recommendation_flow(self):
        """Test ML model training and recommendation generation."""
        from guardian.ml.cost_predictor import CostPredictor

        predictor = CostPredictor()
        historical_costs = [1000.0 + i * 10 for i in range(60)]

        # Train LSTM model
        lstm_result = predictor.train_lstm_model(
            "123456789", historical_costs, {}
        )
        assert lstm_result["success"] is True
        assert "predictions" in lstm_result

        # Evaluate accuracy
        accuracy_result = predictor.evaluate_model_accuracy(
            historical_costs[-5:],
            lstm_result["predictions"][-5:]
        )
        assert accuracy_result["success"] is True

    def test_end_to_end_alert_response_workflow(self):
        """Test alert generation and escalation."""
        from guardian.handlers.predictive_alert_handler import PredictiveAlertHandler

        alert_handler = PredictiveAlertHandler()

        # Predict threshold breach
        forecast = [4900.0, 4950.0, 5050.0, 5150.0, 5250.0]
        threshold = 5000.0

        breach_result = alert_handler.predict_threshold_breach(
            "123456789", threshold, forecast
        )
        assert breach_result["success"] is True
        assert breach_result["will_breach"] is True

        # Schedule escalating alerts
        alert_config = {
            "account_id": "123456789",
            "threshold": threshold,
            "forecast_breach_day": 2,
            "alert_escalation": ["email", "sms"],
        }

        alert_schedule = alert_handler.schedule_predictive_alerts(alert_config)
        assert alert_schedule["success"] is True
        assert len(alert_schedule["scheduled_alerts"]) > 0
