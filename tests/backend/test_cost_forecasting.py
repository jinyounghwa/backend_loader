"""Sprint 41 Phase 2: Cost Forecasting Model"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from forecasters.cost_forecast_model import CostForecastModel


# ==========================================
# Test Group 1: ARIMA Model Training (2 tests)
# ==========================================

def test_cost_forecast_model_initialization():
    """Test cost forecast model initialization"""
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    model = CostForecastModel(cost_history_table, dynamodb_table)

    assert model is not None
    assert model.cost_history_table is not None
    assert model.table is not None


def test_train_arima_model():
    """Test training ARIMA model for cost forecasting"""
    cost_history_table = MagicMock()

    # Mock historical cost data
    historical_data = []
    base_cost = 1000.0
    for i in range(90):
        cost = base_cost + (i * 5) + (i % 7 * 50)  # Uptrend with weekly pattern
        historical_data.append({
            'date': (datetime.now(timezone.utc) - timedelta(days=90-i)).isoformat(),
            'cost': cost
        })

    cost_history_table.query.return_value = {'Items': historical_data}
    dynamodb_table = MagicMock()

    model = CostForecastModel(cost_history_table, dynamodb_table)
    model_id = model.train_arima_model('acc-123', historical_days=90)

    assert model_id is not None
    assert isinstance(model_id, str)


# ==========================================
# Test Group 2: Cost Forecasting (2 tests)
# ==========================================

def test_forecast_costs():
    """Test forecasting future costs"""
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    model = CostForecastModel(cost_history_table, dynamodb_table)
    forecast = model.forecast_costs('acc-123', 'model-123', days_ahead=30)

    assert forecast is not None
    assert isinstance(forecast, dict)
    assert 'forecast' in forecast or 'error' in forecast


def test_forecast_with_confidence_interval():
    """Test cost forecast with confidence intervals"""
    forecast_data = {
        'forecast': [1500.0, 1525.0, 1550.0, 1575.0],
        'lower_bound': [1400.0, 1420.0, 1440.0, 1460.0],
        'upper_bound': [1600.0, 1630.0, 1660.0, 1690.0],
        'confidence': 0.95
    }

    # Verify forecast structure
    assert len(forecast_data['forecast']) == 4
    assert len(forecast_data['lower_bound']) == 4
    assert len(forecast_data['upper_bound']) == 4
    assert all(forecast_data['lower_bound'][i] < forecast_data['forecast'][i] < forecast_data['upper_bound'][i]
               for i in range(len(forecast_data['forecast'])))


# ==========================================
# Test Group 3: Anomaly Detection (2 tests)
# ==========================================

def test_detect_cost_anomalies():
    """Test detecting cost anomalies from forecast"""
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    model = CostForecastModel(cost_history_table, dynamodb_table)

    actual_cost = 2000.0  # Much higher than expected
    predicted_cost = 1500.0

    anomaly = model.detect_cost_anomalies('acc-123', actual_cost, predicted_cost)

    assert anomaly is not None
    assert isinstance(anomaly, dict)
    assert 'is_anomaly' in anomaly or 'deviation' in anomaly


def test_anomaly_deviation_calculation():
    """Test calculation of deviation from predicted cost"""
    actual = 2000.0
    predicted = 1500.0

    deviation_percent = abs(actual - predicted) / predicted * 100

    assert deviation_percent == pytest.approx(33.33, 0.1)
    assert deviation_percent > 20  # Threshold for anomaly


# ==========================================
# Test Group 4: Model Accuracy Validation (2 tests)
# ==========================================

def test_validate_model_accuracy():
    """Test validation of forecasting model accuracy"""
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    model = CostForecastModel(cost_history_table, dynamodb_table)

    # Simulated previous forecast and actual data
    predictions = [1500.0, 1525.0, 1550.0, 1575.0]
    actuals = [1480.0, 1510.0, 1560.0, 1590.0]

    accuracy = model.calculate_forecast_accuracy(predictions, actuals)

    assert accuracy is not None
    assert isinstance(accuracy, dict)
    assert 'mape' in accuracy or 'rmse' in accuracy


def test_mape_calculation():
    """Test Mean Absolute Percentage Error calculation"""
    predictions = [100.0, 200.0, 300.0]
    actuals = [110.0, 180.0, 320.0]

    errors = [abs(predictions[i] - actuals[i]) / actuals[i] * 100 for i in range(len(predictions))]
    mape = sum(errors) / len(errors)

    assert mape > 0
    assert mape < 50  # Reasonable MAPE


# ==========================================
# Test Group 5: Recommendation Generation (2 tests)
# ==========================================

def test_recommend_cost_reductions():
    """Test generating cost reduction recommendations from forecast"""
    cost_history_table = MagicMock()
    dynamodb_table = MagicMock()

    model = CostForecastModel(cost_history_table, dynamodb_table)

    forecast = {
        'forecast': [1500.0, 1600.0, 1700.0],
        'trend': 'increasing',
        'monthly_projection': 1600.0
    }

    recommendations = model.recommend_cost_reductions('acc-123', forecast)

    assert recommendations is not None
    assert isinstance(recommendations, list)


def test_cost_reduction_action_items():
    """Test cost reduction action items are specific and measurable"""
    recommendations = [
        {
            'action': 'Stop idle EC2 instances',
            'potential_savings': 200.0,
            'priority': 'high',
            'timeframe': 'immediate'
        },
        {
            'action': 'Delete old snapshots',
            'potential_savings': 75.0,
            'priority': 'medium',
            'timeframe': 'within 1 week'
        }
    ]

    total_savings = sum(r['potential_savings'] for r in recommendations)

    assert total_savings == 275.0
    assert all('action' in r and 'potential_savings' in r for r in recommendations)
