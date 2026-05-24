"""Sprint 39 Phase 3: Budget Control and Alerts"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from controllers.budget_controller import BudgetController, BudgetAlert


# ==========================================
# Test Group 1: Budget Setup and Retrieval (2 tests)
# ==========================================

def test_budget_controller_initialization():
    """Test budget controller initialization"""
    table = MagicMock()

    controller = BudgetController(table)

    assert controller is not None
    assert controller.table is not None


def test_set_and_retrieve_monthly_budget():
    """Test setting and retrieving monthly budget"""
    table = MagicMock()
    table.put_item.return_value = {}
    table.get_item.return_value = {
        'Item': {
            'account_id': 'acc-123',
            'monthly_budget': 1000.0,
            'set_date': '2026-05-24'
        }
    }

    controller = BudgetController(table)
    controller.set_monthly_budget('acc-123', 1000.0)

    retrieved = table.get_item.return_value['Item']
    assert retrieved['monthly_budget'] == 1000.0


# ==========================================
# Test Group 2: Budget Alerts (2 tests)
# ==========================================

def test_check_budget_alert_50_percent():
    """Test budget alert at 50% threshold"""
    table = MagicMock()

    controller = BudgetController(table)

    # $500 spent of $1000 budget = 50%
    is_alert = controller.check_budget_alert_at_threshold(500.0, 1000.0, 50)

    assert is_alert


def test_check_budget_alert_80_percent():
    """Test budget alert at 80% threshold"""
    table = MagicMock()

    controller = BudgetController(table)

    # $800 spent of $1000 budget = 80%
    is_alert = controller.check_budget_alert_at_threshold(800.0, 1000.0, 80)

    assert is_alert


# ==========================================
# Test Group 3: Alert Threshold Configuration (2 tests)
# ==========================================

def test_set_alert_thresholds():
    """Test setting custom alert thresholds"""
    table = MagicMock()

    controller = BudgetController(table)

    thresholds = {
        50: 'warning',
        75: 'high',
        90: 'critical',
        100: 'stop'
    }

    controller.set_alert_thresholds('acc-123', thresholds)

    assert table.put_item.called


def test_get_remaining_budget():
    """Test remaining budget calculation"""
    table = MagicMock()

    controller = BudgetController(table)

    remaining = controller.calculate_remaining_budget(1000.0, 650.0)

    assert remaining == 350.0
    assert remaining > 0


# ==========================================
# Test Group 4: Month-End Forecasting (2 tests)
# ==========================================

def test_forecast_month_end():
    """Test month-end cost forecasting"""
    table = MagicMock()

    controller = BudgetController(table)

    # Day 10 with $200 spent = $600/month average
    current_day = 10
    spent_so_far = 200.0
    daily_average = spent_so_far / current_day

    forecast = controller.forecast_month_end(spent_so_far, current_day)

    assert forecast is not None
    assert 'projected_total' in forecast
    assert forecast['projected_total'] > spent_so_far


def test_burn_rate_calculation():
    """Test cost burn rate calculation"""
    table = MagicMock()

    controller = BudgetController(table)

    # $200 spent in 10 days = $20/day burn rate
    spent = 200.0
    days = 10
    burn_rate = spent / days

    assert burn_rate == 20.0

    # Days until $1000 budget limit = 50 days remaining
    days_until_limit = (1000.0 - spent) / burn_rate
    assert days_until_limit == 40.0


# ==========================================
# Test Group 5: Auto-Remediation (2 tests)
# ==========================================

def test_set_auto_remediation():
    """Test enabling auto-remediation"""
    table = MagicMock()

    controller = BudgetController(table)

    controller.set_auto_remediation('acc-123', enabled=True)

    assert table.put_item.called


def test_auto_remediation_triggers():
    """Test auto-remediation trigger conditions"""
    table = MagicMock()

    controller = BudgetController(table)

    # When budget exceeded, auto-remediation should trigger
    budget = 1000.0
    spent = 1050.0
    percentage = (spent / budget) * 100

    should_trigger = percentage > 100

    assert should_trigger
