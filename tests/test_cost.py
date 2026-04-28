"""Tests for cost checker - LocalStack integration tests"""
import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.checkers.cost import CostChecker


class TestCostChecker(unittest.TestCase):

    def setUp(self):
        self._orig_daily = os.environ.get('MOCK_DAILY_COST')
        self._orig_monthly = os.environ.get('MOCK_MONTHLY_COST')

    def tearDown(self):
        if self._orig_daily is not None:
            os.environ['MOCK_DAILY_COST'] = self._orig_daily
        elif 'MOCK_DAILY_COST' in os.environ:
            del os.environ['MOCK_DAILY_COST']
        if self._orig_monthly is not None:
            os.environ['MOCK_MONTHLY_COST'] = self._orig_monthly
        elif 'MOCK_MONTHLY_COST' in os.environ:
            del os.environ['MOCK_MONTHLY_COST']

    def test_get_daily_cost_default(self):
        checker = CostChecker(cost_threshold=10.0)
        cost = checker.get_daily_cost('2024-01-01')
        self.assertEqual(cost, 5.50)

    def test_get_daily_cost_custom_env(self):
        os.environ['MOCK_DAILY_COST'] = '25.50'
        checker = CostChecker(cost_threshold=10.0)
        cost = checker.get_daily_cost('2024-01-01')
        self.assertEqual(cost, 25.50)

    def test_get_monthly_cost_default(self):
        checker = CostChecker(cost_threshold=10.0)
        cost = checker.get_monthly_cost(2024, 1)
        self.assertEqual(cost, 150.50)

    def test_get_monthly_cost_custom_env(self):
        os.environ['MOCK_MONTHLY_COST'] = '300.00'
        checker = CostChecker(cost_threshold=10.0)
        cost = checker.get_monthly_cost(2024, 1)
        self.assertEqual(cost, 300.00)

    def test_check_cost_anomaly_exceeds_threshold(self):
        os.environ['MOCK_DAILY_COST'] = '15.00'
        checker = CostChecker(cost_threshold=10.0)
        is_anomaly, data = checker.check_cost_anomaly()

        self.assertTrue(is_anomaly)
        self.assertEqual(data['today_cost'], 15.00)
        self.assertEqual(data['yesterday_cost'], 15.00)
        self.assertEqual(data['threshold'], 10.0)

    def test_check_cost_anomaly_within_threshold(self):
        os.environ['MOCK_DAILY_COST'] = '5.00'
        checker = CostChecker(cost_threshold=10.0)
        is_anomaly, data = checker.check_cost_anomaly()

        self.assertFalse(is_anomaly)
        self.assertEqual(data['today_cost'], 5.00)
        self.assertEqual(data['yesterday_cost'], 5.00)
        self.assertEqual(data['monthly_cost'], 150.50)

    def test_increase_percent_zero_when_costs_equal(self):
        os.environ['MOCK_DAILY_COST'] = '10.00'
        checker = CostChecker(cost_threshold=10.0)
        _, data = checker.check_cost_anomaly()
        self.assertEqual(data['increase_percent'], 0.0)


if __name__ == '__main__':
    unittest.main()
