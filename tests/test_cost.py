"""Tests for cost checker - LocalStack integration tests"""

import os
import unittest

from guardian.checkers.cost import CostChecker


class TestCostChecker(unittest.TestCase):

    def test_get_daily_cost_default(self):
        checker = CostChecker(config={"cost_threshold": 10.0})
        cost = checker._get_daily_cost("2024-01-01")
        self.assertEqual(cost, 5.50)

    def test_get_daily_cost_custom_env(self):
        os.environ["MOCK_DAILY_COST"] = "25.50"
        checker = CostChecker(config={"cost_threshold": 10.0})
        cost = checker._get_daily_cost("2024-01-01")
        self.assertEqual(cost, 25.50)
        os.environ.pop("MOCK_DAILY_COST", None)

    def test_get_monthly_cost_default(self):
        checker = CostChecker(config={"cost_threshold": 10.0})
        cost = checker._get_monthly_cost(2024, 1)
        self.assertEqual(cost, 150.50)

    def test_get_monthly_cost_custom_env(self):
        os.environ["MOCK_MONTHLY_COST"] = "300.00"
        checker = CostChecker(config={"cost_threshold": 10.0})
        cost = checker._get_monthly_cost(2024, 1)
        self.assertEqual(cost, 300.00)
        os.environ.pop("MOCK_MONTHLY_COST", None)

    def test_check_cost_anomaly_exceeds_threshold(self):
        os.environ["MOCK_DAILY_COST"] = "15.00"
        checker = CostChecker(config={"cost_threshold": 10.0})
        is_anomaly, data = checker.check_cost_anomaly()
        self.assertTrue(is_anomaly)
        self.assertEqual(data["today_cost"], 15.00)
        self.assertEqual(data["threshold"], 10.0)
        os.environ.pop("MOCK_DAILY_COST", None)

    def test_check_cost_anomaly_within_threshold(self):
        os.environ["MOCK_DAILY_COST"] = "5.00"
        checker = CostChecker(config={"cost_threshold": 10.0})
        is_anomaly, data = checker.check_cost_anomaly()
        self.assertFalse(is_anomaly)
        self.assertEqual(data["today_cost"], 5.00)
        self.assertEqual(data["monthly_cost"], 150.50)
        os.environ.pop("MOCK_DAILY_COST", None)

    def test_increase_percent_zero_when_costs_equal(self):
        os.environ["MOCK_DAILY_COST"] = "10.00"
        checker = CostChecker(config={"cost_threshold": 10.0})
        _, data = checker.check_cost_anomaly()
        self.assertEqual(data["increase_percent"], 0.0)
        os.environ.pop("MOCK_DAILY_COST", None)

    def test_check_returns_check_result(self):
        os.environ["MOCK_DAILY_COST"] = "5.00"
        checker = CostChecker(config={"cost_threshold": 10.0})
        result = checker.check()
        self.assertEqual(result.severity, "INFO")
        self.assertIn("5.00", result.message)
        os.environ.pop("MOCK_DAILY_COST", None)

    def test_check_returns_high_on_anomaly(self):
        os.environ["MOCK_DAILY_COST"] = "15.00"
        checker = CostChecker(config={"cost_threshold": 10.0})
        result = checker.check()
        self.assertEqual(result.severity, "HIGH")
        self.assertTrue(result.details["is_anomaly"])
        os.environ.pop("MOCK_DAILY_COST", None)


if __name__ == "__main__":
    unittest.main()
