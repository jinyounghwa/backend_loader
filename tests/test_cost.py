"""Tests for cost checker"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.checkers.cost import CostChecker


class TestCostChecker(unittest.TestCase):
    def setUp(self):
        self.cost_checker = CostChecker(cost_threshold=10.0)

    @patch('guardian.checkers.cost.boto3.client')
    def test_get_daily_cost(self, mock_boto3):
        """Test getting daily cost"""
        mock_ce_client = MagicMock()
        mock_boto3.return_value = mock_ce_client

        # Mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'Total': {
                        'UnblendedCost': {
                            'Amount': '25.50'
                        }
                    }
                }
            ]
        }

        cost = self.cost_checker.get_daily_cost('2024-01-01')
        self.assertEqual(cost, 25.50)

    @patch('guardian.checkers.cost.boto3.client')
    def test_check_cost_anomaly_exceeds_threshold(self, mock_boto3):
        """Test cost anomaly detection when threshold is exceeded"""
        mock_ce_client = MagicMock()
        mock_boto3.return_value = mock_ce_client

        # Mock responses
        mock_ce_client.get_cost_and_usage.side_effect = [
            # Today
            {'ResultsByTime': [{'Total': {'UnblendedCost': {'Amount': '15.00'}}}]},
            # Yesterday
            {'ResultsByTime': [{'Total': {'UnblendedCost': {'Amount': '5.00'}}}]},
            # Monthly
            {'ResultsByTime': [{'Total': {'UnblendedCost': {'Amount': '100.00'}}}]}
        ]

        is_anomaly, data = self.cost_checker.check_cost_anomaly()

        self.assertTrue(is_anomaly)
        self.assertEqual(data['today_cost'], 15.00)
        self.assertEqual(data['yesterday_cost'], 5.00)

    @patch('guardian.checkers.cost.boto3.client')
    def test_check_cost_anomaly_within_threshold(self, mock_boto3):
        """Test cost anomaly detection when threshold is not exceeded"""
        mock_ce_client = MagicMock()
        mock_boto3.return_value = mock_ce_client

        # Mock responses
        mock_ce_client.get_cost_and_usage.side_effect = [
            # Today
            {'ResultsByTime': [{'Total': {'UnblendedCost': {'Amount': '5.00'}}}]},
            # Yesterday
            {'ResultsByTime': [{'Total': {'UnblendedCost': {'Amount': '4.00'}}}]},
            # Monthly
            {'ResultsByTime': [{'Total': {'UnblendedCost': {'Amount': '50.00'}}}]}
        ]

        is_anomaly, data = self.cost_checker.check_cost_anomaly()

        self.assertFalse(is_anomaly)
        self.assertEqual(data['today_cost'], 5.00)


if __name__ == '__main__':
    unittest.main()
