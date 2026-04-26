"""Tests for EC2 checker"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.checkers.ec2 import EC2Checker


class TestEC2Checker(unittest.TestCase):
    def setUp(self):
        self.ec2_checker = EC2Checker(authorized_regions=['us-east-1', 'us-west-2'])

    @patch('guardian.checkers.ec2.boto3.client')
    def test_get_all_instances(self, mock_boto3):
        """Test getting all instances"""
        mock_ec2_client = MagicMock()
        mock_boto3.return_value = mock_ec2_client

        # Mock regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'us-west-2'}
            ]
        }

        # Mock instances
        mock_ec2_client.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-12345678',
                            'InstanceType': 't3.micro',
                            'State': {'Name': 'running'}
                        }
                    ]
                }
            ]
        }

        instances = self.ec2_checker.get_all_instances()
        self.assertIsInstance(instances, dict)

    @patch('guardian.checkers.ec2.boto3.client')
    def test_get_unauthorized_regions_instances(self, mock_boto3):
        """Test detecting instances in unauthorized regions"""
        mock_ec2_client = MagicMock()
        mock_boto3.return_value = mock_ec2_client

        # Mock regions including unauthorized
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'eu-west-1'}  # Unauthorized
            ]
        }

        # Mock instances
        def describe_instances_side_effect(**kwargs):
            return {
                'Reservations': [
                    {
                        'Instances': [
                            {
                                'InstanceId': 'i-12345678',
                                'InstanceType': 't3.micro'
                            }
                        ]
                    }
                ]
            }

        mock_ec2_client.describe_instances.side_effect = describe_instances_side_effect

        unauthorized = self.ec2_checker.get_unauthorized_regions_instances()
        self.assertIn('eu-west-1', unauthorized)

    @patch('guardian.checkers.ec2.boto3.client')
    def test_check_ec2_anomalies_no_anomalies(self, mock_boto3):
        """Test EC2 anomaly check when everything is fine"""
        mock_ec2_client = MagicMock()
        mock_boto3.return_value = mock_ec2_client

        # Mock regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'}
            ]
        }

        # Mock no instances
        mock_ec2_client.describe_instances.return_value = {
            'Reservations': []
        }

        is_anomaly, data = self.ec2_checker.check_ec2_anomalies()

        self.assertFalse(is_anomaly)
        self.assertEqual(len(data['anomalies']), 0)


if __name__ == '__main__':
    unittest.main()
