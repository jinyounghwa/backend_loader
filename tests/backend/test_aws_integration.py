"""Sprint 65 Phase 1: Real AWS API Integration (12 tests)"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from guardian.integrations import (
    CostExplorerClient,
    EC2Manager,
    S3Manager,
    RDSManager,
    LambdaManager,
    DynamoDBManager,
)


class TestCostExplorerClient:
    """Test Cost Explorer real API integration."""

    @pytest.fixture
    def mock_ce_client(self):
        return Mock()

    @pytest.fixture
    def cost_explorer(self, mock_ce_client):
        return CostExplorerClient(clients={"ce": mock_ce_client})

    def test_cost_explorer_daily_cost(self, cost_explorer, mock_ce_client):
        """✅ Fetch actual daily costs from Cost Explorer API."""
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-05-29', 'End': '2025-05-30'},
                    'Total': {'UnblendedCost': {'Amount': '15.50'}},
                }
            ]
        }

        cost = cost_explorer.get_daily_cost('2025-05-29')
        assert cost == 15.50
        mock_ce_client.get_cost_and_usage.assert_called_once()

    def test_cost_explorer_monthly_trend(self, cost_explorer, mock_ce_client):
        """✅ Get monthly cost trends from Cost Explorer API."""
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-05-01', 'End': '2025-06-01'},
                    'Total': {'UnblendedCost': {'Amount': '450.75'}},
                }
            ]
        }

        cost = cost_explorer.get_monthly_cost(2025, 5)
        assert cost == 450.75
        mock_ce_client.get_cost_and_usage.assert_called_once()


class TestEC2Manager:
    """Test EC2 real API integration."""

    @pytest.fixture
    def mock_ec2_client(self):
        return Mock()

    @pytest.fixture
    def ec2_manager(self, mock_ec2_client):
        return EC2Manager(clients={"ec2": mock_ec2_client})

    def test_ec2_list_instances(self, ec2_manager, mock_ec2_client):
        """✅ List instances with real filters."""
        mock_ec2_client.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-123456',
                            'State': {'Name': 'running'},
                            'InstanceType': 't3.micro',
                            'LaunchTime': datetime.now(timezone.utc),
                            'PrivateIpAddress': '10.0.0.1',
                            'Tags': [{'Key': 'Name', 'Value': 'test-instance'}],
                        }
                    ]
                }
            ]
        }

        instances = ec2_manager.list_instances()
        assert len(instances) == 1
        assert instances[0]['instance_id'] == 'i-123456'
        assert instances[0]['state'] == 'running'

    def test_ec2_stop_instance(self, ec2_manager, mock_ec2_client):
        """✅ Actually stop EC2 instance."""
        result = ec2_manager.stop_instance('i-123456')
        assert result is True
        mock_ec2_client.stop_instances.assert_called_once_with(
            InstanceIds=['i-123456']
        )


class TestS3Manager:
    """Test S3 real API integration."""

    @pytest.fixture
    def mock_s3_client(self):
        return Mock()

    @pytest.fixture
    def s3_manager(self, mock_s3_client):
        return S3Manager(clients={"s3": mock_s3_client})

    def test_s3_list_buckets(self, s3_manager, mock_s3_client):
        """✅ List S3 buckets with policies."""
        mock_s3_client.list_buckets.return_value = {
            'Buckets': [
                {
                    'Name': 'my-bucket',
                    'CreationDate': datetime.now(timezone.utc),
                }
            ]
        }

        buckets = s3_manager.list_buckets()
        assert len(buckets) == 1
        assert buckets[0]['name'] == 'my-bucket'

    def test_s3_block_public_access(self, s3_manager, mock_s3_client):
        """✅ Apply block public access settings."""
        result = s3_manager.block_public_access('my-bucket')
        assert result is True
        mock_s3_client.put_public_access_block.assert_called_once()

        call_args = mock_s3_client.put_public_access_block.call_args
        assert call_args[1]['Bucket'] == 'my-bucket'
        config = call_args[1]['PublicAccessBlockConfiguration']
        assert config['BlockPublicAcls'] is True
        assert config['IgnorePublicAcls'] is True


class TestRDSManager:
    """Test RDS real API integration."""

    @pytest.fixture
    def mock_rds_client(self):
        return Mock()

    @pytest.fixture
    def rds_manager(self, mock_rds_client):
        return RDSManager(clients={"rds": mock_rds_client})

    def test_rds_modify_instance(self, rds_manager, mock_rds_client):
        """✅ Modify RDS instance class."""
        result = rds_manager.modify_instance_class('my-db', 'db.t3.small')
        assert result is True
        mock_rds_client.modify_db_instance.assert_called_once()

        call_args = mock_rds_client.modify_db_instance.call_args
        assert call_args[1]['DBInstanceIdentifier'] == 'my-db'
        assert call_args[1]['DBInstanceClass'] == 'db.t3.small'


class TestLambdaManager:
    """Test Lambda real API integration."""

    @pytest.fixture
    def mock_lambda_client(self):
        return Mock()

    @pytest.fixture
    def lambda_manager(self, mock_lambda_client):
        return LambdaManager(clients={"lambda": mock_lambda_client})

    def test_lambda_get_metrics(self, lambda_manager, mock_lambda_client):
        """✅ Fetch Lambda CloudWatch metrics."""
        mock_lambda_client.list_functions.return_value = {
            'Functions': [
                {
                    'FunctionName': 'my-function',
                    'Runtime': 'python3.12',
                    'MemorySize': 512,
                    'Timeout': 60,
                    'LastModified': '2025-05-29T10:00:00.000+0000',
                }
            ]
        }

        functions = lambda_manager.list_functions()
        assert len(functions) == 1
        assert functions[0]['name'] == 'my-function'

    def test_lambda_update_memory(self, lambda_manager, mock_lambda_client):
        """✅ Update function memory config."""
        result = lambda_manager.update_memory('my-function', 1024)
        assert result is True
        mock_lambda_client.update_function_configuration.assert_called_once()


class TestDynamoDBManager:
    """Test DynamoDB real API integration."""

    @pytest.fixture
    def mock_dynamodb_client(self):
        return Mock()

    @pytest.fixture
    def dynamodb_manager(self, mock_dynamodb_client):
        return DynamoDBManager(clients={"dynamodb": mock_dynamodb_client})

    def test_dynamodb_get_table_metrics(self, dynamodb_manager, mock_dynamodb_client):
        """✅ Get DynamoDB metrics."""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {
                'TableName': 'my-table',
                'TableStatus': 'ACTIVE',
                'ItemCount': 1000,
                'TableSizeBytes': 5242880,
                'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
                'BillingModeSummary': {'BillingMode': 'PAY_PER_REQUEST'},
            }
        }

        details = dynamodb_manager.get_table_description('my-table')
        assert details['name'] == 'my-table'
        assert details['status'] == 'ACTIVE'
        assert details['item_count'] == 1000

    def test_dynamodb_update_ttl(self, dynamodb_manager, mock_dynamodb_client):
        """✅ Enable/disable TTL."""
        result = dynamodb_manager.enable_ttl('my-table', 'expiry')
        assert result is True
        mock_dynamodb_client.update_time_to_live.assert_called_once()

        call_args = mock_dynamodb_client.update_time_to_live.call_args
        assert call_args[1]['TableName'] == 'my-table'
        assert call_args[1]['TimeToLiveSpecification']['AttributeName'] == 'expiry'
        assert call_args[1]['TimeToLiveSpecification']['Enabled'] is True


class TestBatchOperations:
    """Test multi-service batch operations."""

    def test_batch_operations(self):
        """✅ Execute multi-service batch operations."""
        mock_ce = Mock()
        mock_ec2 = Mock()
        mock_s3 = Mock()

        cost_explorer = CostExplorerClient(clients={"ce": mock_ce})
        ec2_manager = EC2Manager(clients={"ec2": mock_ec2})
        s3_manager = S3Manager(clients={"s3": mock_s3})

        mock_ce.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-05-29', 'End': '2025-05-30'},
                    'Total': {'UnblendedCost': {'Amount': '10.00'}},
                }
            ]
        }
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{'Instances': []}]
        }
        mock_s3.list_buckets.return_value = {'Buckets': []}

        cost = cost_explorer.get_daily_cost('2025-05-29')
        instances = ec2_manager.list_instances()
        buckets = s3_manager.list_buckets()

        assert cost == 10.00
        assert instances == []
        assert buckets == []
        assert mock_ce.get_cost_and_usage.called
        assert mock_ec2.describe_instances.called
        assert mock_s3.list_buckets.called
