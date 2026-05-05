"""Unit tests for auto-remediation functions"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from guardian.responders.auto_remediation import (
    remediate_cost_overrun,
    remediate_hacking_suspicion
)


class TestRemediateCostOverrun(unittest.TestCase):
    """Unit tests for remediate_cost_overrun"""

    @patch('guardian.responders.auto_remediation.Config.is_localstack')
    @patch('guardian.responders.auto_remediation.AWSClientProvider.get_client')
    def test_remediate_cost_overrun_localstack(self, mock_get_client, mock_is_localstack):
        """Test cost remediation in LocalStack mode"""
        mock_is_localstack.return_value = True

        mock_ssm = MagicMock()
        mock_get_client.return_value = mock_ssm

        result = remediate_cost_overrun()

        self.assertEqual(result['action'], '요금과다 원인수정')
        self.assertIn('timestamp', result)
        self.assertIsInstance(result['steps'], list)
        self.assertGreater(len(result['steps']), 0)
        self.assertIsNotNone(result['summary'])

    @patch('guardian.responders.auto_remediation.Config.is_localstack')
    @patch('guardian.responders.auto_remediation.AWSClientProvider.get_client')
    def test_remediate_cost_overrun_aws(self, mock_get_client, mock_is_localstack):
        """Test cost remediation in AWS mode"""
        mock_is_localstack.return_value = False

        # Mock AWS clients
        mock_ce_client = MagicMock()
        mock_ssm_client = MagicMock()

        def get_client_side_effect(service, **kwargs):
            if service == 'ce':
                return mock_ce_client
            elif service == 'ssm':
                return mock_ssm_client
            return MagicMock()

        mock_get_client.side_effect = get_client_side_effect

        # Mock Cost Explorer response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'Groups': [
                        {
                            'Keys': ['EC2'],
                            'Metrics': {'UnblendedCost': {'Amount': '5.00'}}
                        },
                        {
                            'Keys': ['Lambda'],
                            'Metrics': {'UnblendedCost': {'Amount': '2.00'}}
                        },
                        {
                            'Keys': ['S3'],
                            'Metrics': {'UnblendedCost': {'Amount': '1.50'}}
                        }
                    ]
                }
            ]
        }

        # Mock SSM parameter
        mock_ssm_client.get_parameter.return_value = {
            'Parameter': {'Value': '10.0'}
        }

        result = remediate_cost_overrun()

        self.assertEqual(result['action'], '요금과다 원인수정')
        self.assertGreater(len(result['steps']), 0)
        self.assertIn('EC2', result['summary'])

    @patch('guardian.responders.auto_remediation.Config.is_localstack')
    def test_remediate_cost_overrun_result_structure(self, mock_is_localstack):
        """Test result structure of cost remediation"""
        mock_is_localstack.return_value = True

        result = remediate_cost_overrun()

        # Check required fields
        self.assertIn('action', result)
        self.assertIn('timestamp', result)
        self.assertIn('steps', result)
        self.assertIn('summary', result)

        # Check timestamp format
        try:
            datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            self.fail("Timestamp is not in ISO format")


class TestRemediateHackingSuspicion(unittest.TestCase):
    """Unit tests for remediate_hacking_suspicion"""

    @patch('guardian.responders.auto_remediation.Config.is_localstack')
    @patch('guardian.responders.auto_remediation.AWSClientProvider.get_client')
    def test_remediate_hacking_suspicion_localstack(
        self, mock_get_client, mock_is_localstack
    ):
        """Test hacking suspicion remediation in LocalStack mode"""
        mock_is_localstack.return_value = True

        # Mock AWS clients
        mock_ec2_client = MagicMock()
        mock_s3_client = MagicMock()

        def get_client_side_effect(service, **kwargs):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 's3':
                return mock_s3_client
            return MagicMock()

        mock_get_client.side_effect = get_client_side_effect

        # Mock EC2 response
        mock_ec2_client.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [
                        {'InstanceId': 'i-12345678', 'State': {'Name': 'running'}},
                        {'InstanceId': 'i-87654321', 'State': {'Name': 'running'}}
                    ]
                }
            ]
        }

        # Mock S3 response
        mock_s3_client.list_buckets.return_value = {
            'Buckets': [
                {'Name': 'bucket-1'},
                {'Name': 'bucket-2'},
                {'Name': 'bucket-3'}
            ]
        }

        result = remediate_hacking_suspicion()

        self.assertEqual(result['action'], '해킹우려 수정')
        self.assertIn('timestamp', result)
        self.assertIsInstance(result['steps'], list)
        self.assertGreater(len(result['steps']), 0)
        self.assertIsNotNone(result['summary'])

    @patch('guardian.responders.auto_remediation.Config.is_localstack')
    @patch('guardian.responders.auto_remediation.AWSClientProvider.get_client')
    def test_remediate_hacking_suspicion_ec2_failure(
        self, mock_get_client, mock_is_localstack
    ):
        """Test hacking suspicion with EC2 failure"""
        mock_is_localstack.return_value = False

        mock_ec2_client = MagicMock()
        mock_s3_client = MagicMock()

        def get_client_side_effect(service, **kwargs):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 's3':
                return mock_s3_client
            return MagicMock()

        mock_get_client.side_effect = get_client_side_effect

        # Mock EC2 methods
        mock_ec2_client.describe_regions.return_value = {'Regions': [{'RegionName': 'us-east-1'}]}
        mock_ec2_client.describe_instances.side_effect = Exception('API Error')

        # Mock S3 success
        mock_s3_client.list_buckets.return_value = {'Buckets': []}

        result = remediate_hacking_suspicion()

        # Should handle error gracefully
        self.assertEqual(result['action'], '해킹우려 수정')
        self.assertGreater(len(result['steps']), 0)

    @patch('guardian.responders.auto_remediation.Config.is_localstack')
    @patch('guardian.responders.auto_remediation.AWSClientProvider.get_client')
    def test_remediate_hacking_suspicion_result_structure(self, mock_get_client, mock_is_localstack):
        """Test result structure of hacking suspicion remediation"""
        mock_is_localstack.return_value = True

        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {'Reservations': []}
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {'Buckets': []}

        def get_client_side_effect(service, **kwargs):
            if service == 'ec2':
                return mock_ec2
            elif service == 's3':
                return mock_s3
            return MagicMock()

        mock_get_client.side_effect = get_client_side_effect
        result = remediate_hacking_suspicion()

        # Check required fields
        self.assertIn('action', result)
        self.assertIn('timestamp', result)
        self.assertIn('steps', result)
        self.assertIn('summary', result)

        # Check each step has required fields
        for step in result['steps']:
            self.assertIn('name', step)
            self.assertIn('detail', step)
            self.assertIn('status', step)
            self.assertIn(step['status'], ['done', 'failed', 'analyzed', 'identified'])


class TestRemediationIntegration(unittest.TestCase):
    """Integration tests for remediation functions"""

    @patch('guardian.responders.auto_remediation.Config.is_localstack')
    @patch('guardian.responders.auto_remediation.AWSClientProvider.get_client')
    def test_both_remediations_return_valid_structure(self, mock_get_client, mock_is_localstack):
        """Test that both remediation functions return valid structures"""
        mock_is_localstack.return_value = True

        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {'Reservations': []}
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {'Buckets': []}
        mock_ssm = MagicMock()

        def get_client_side_effect(service, **kwargs):
            if service == 'ec2':
                return mock_ec2
            elif service == 's3':
                return mock_s3
            elif service == 'ssm':
                return mock_ssm
            return MagicMock()

        mock_get_client.side_effect = get_client_side_effect

        cost_result = remediate_cost_overrun()
        hack_result = remediate_hacking_suspicion()

        # Both should have the same structure
        for result in [cost_result, hack_result]:
            self.assertIsInstance(result, dict)
            self.assertIn('action', result)
            self.assertIn('timestamp', result)
            self.assertIn('steps', result)
            self.assertIn('summary', result)


if __name__ == '__main__':
    unittest.main()
