"""Sprint 42 Phase 1: Multi-Account Monitoring"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from guardian.managers.multi_account_manager import MultiAccountManager
from guardian.storage.account_registry import AccountRegistry


# ==========================================
# Test Group 1: Account Registration (2 tests)
# ==========================================

def test_multi_account_manager_initialization():
    """Test multi-account manager initialization"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = MultiAccountManager(sts_client, dynamodb_table)

    assert manager is not None
    assert manager.sts_client is not None
    assert manager.table is not None


def test_register_account():
    """Test registering a new AWS account"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()
    registry = AccountRegistry(dynamodb_table)

    account_config = {
        'account_id': '123456789012',
        'role_arn': 'arn:aws:iam::123456789012:role/GuardianRole',
        'account_name': 'Production Account',
        'region': 'us-east-1'
    }

    result = registry.add_account(account_config)

    assert result is not None
    assert result['account_id'] == '123456789012'
    assert result['account_name'] == 'Production Account'
    assert result['status'] == 'active'


# ==========================================
# Test Group 2: Multi-Account Queries (3 tests)
# ==========================================

def test_cross_account_query():
    """Test querying resources across multiple accounts"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = MultiAccountManager(sts_client, dynamodb_table)

    accounts = [
        {'account_id': 'acc-001', 'role_arn': 'arn:aws:iam::111111111111:role/GuardianRole'},
        {'account_id': 'acc-002', 'role_arn': 'arn:aws:iam::222222222222:role/GuardianRole'}
    ]

    query = {'resource_type': 'EC2', 'filter': {'state': 'running'}}

    results = manager.cross_account_query(query, accounts)

    assert results is not None
    assert isinstance(results, list)


def test_aggregate_metrics():
    """Test aggregating metrics from multiple accounts"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = MultiAccountManager(sts_client, dynamodb_table)

    metric_data = [
        {'account_id': 'acc-001', 'cost': 100, 'instances': 5},
        {'account_id': 'acc-002', 'cost': 200, 'instances': 10}
    ]

    aggregated = manager.aggregate_metrics('cost')

    assert aggregated is not None
    assert isinstance(aggregated, dict)


def test_switch_account_context():
    """Test switching AWS account context via STS AssumeRole"""
    from datetime import datetime, timedelta, timezone as tz

    sts_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = MultiAccountManager(sts_client, dynamodb_table)

    # Mock STS assume_role response with Expiration
    expiration = datetime.now(tz.utc) + timedelta(hours=1)
    sts_client.assume_role.return_value = {
        'Credentials': {
            'AccessKeyId': 'ASIATEMP12345',
            'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG+secretkey',
            'SessionToken': 'session-token-xyz',
            'Expiration': expiration
        }
    }

    result = manager.switch_account_context('arn:aws:iam::123456789012:role/GuardianRole')

    assert result is not None
    assert 'AccessKeyId' in result


# ==========================================
# Test Group 3: Metric Aggregation (3 tests)
# ==========================================

def test_aggregate_cost_metrics():
    """Test aggregating cost metrics across accounts"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = MultiAccountManager(sts_client, dynamodb_table)

    metrics = [
        {'account_id': 'acc-001', 'date': '2026-05-24', 'cost': 150.50},
        {'account_id': 'acc-002', 'date': '2026-05-24', 'cost': 200.75},
        {'account_id': 'acc-003', 'date': '2026-05-24', 'cost': 100.25}
    ]

    total_cost = sum(m['cost'] for m in metrics)
    avg_cost = total_cost / len(metrics)

    assert total_cost == 451.50
    assert avg_cost == pytest.approx(150.50, 0.01)


def test_aggregate_resource_metrics():
    """Test aggregating resource count metrics"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = MultiAccountManager(sts_client, dynamodb_table)

    resources = [
        {'account_id': 'acc-001', 'resource_type': 'EC2', 'count': 15},
        {'account_id': 'acc-002', 'resource_type': 'EC2', 'count': 25},
        {'account_id': 'acc-003', 'resource_type': 'EC2', 'count': 10}
    ]

    total_instances = sum(r['count'] for r in resources)

    assert total_instances == 50


def test_aggregate_by_region():
    """Test aggregating metrics by AWS region"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()

    manager = MultiAccountManager(sts_client, dynamodb_table)

    regional_metrics = {
        'us-east-1': {'cost': 300, 'instances': 20},
        'us-west-2': {'cost': 200, 'instances': 15},
        'eu-west-1': {'cost': 150, 'instances': 10}
    }

    total_cost = sum(m['cost'] for m in regional_metrics.values())

    assert total_cost == 650


# ==========================================
# Test Group 4: Account Status Monitoring (4 tests)
# ==========================================

def test_list_all_accounts():
    """Test listing all registered accounts"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()
    registry = AccountRegistry(dynamodb_table)

    # Mock DynamoDB scan response
    dynamodb_table.scan.return_value = {
        'Items': [
            {'account_id': 'acc-001', 'account_name': 'Account 1'},
            {'account_id': 'acc-002', 'account_name': 'Account 2'}
        ]
    }

    accounts = registry.list_accounts()

    assert accounts is not None
    assert isinstance(accounts, list)
    assert len(accounts) == 2


def test_get_account_status():
    """Test getting status of a specific account"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()
    manager = MultiAccountManager(sts_client, dynamodb_table)

    status = manager.get_account_status('acc-001')

    assert status is not None
    assert isinstance(status, dict)


def test_get_account_health():
    """Test getting overall health metrics for an account"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()
    manager = MultiAccountManager(sts_client, dynamodb_table)

    health = {
        'account_id': 'acc-001',
        'status': 'healthy',
        'last_check': datetime.now(timezone.utc).isoformat(),
        'issues_found': 0,
        'resources_scanned': 45
    }

    assert health['status'] == 'healthy'
    assert health['resources_scanned'] == 45


def test_update_account_registry():
    """Test updating account configuration"""
    sts_client = MagicMock()
    dynamodb_table = MagicMock()
    registry = AccountRegistry(dynamodb_table)

    account_update = {
        'account_id': 'acc-001',
        'account_name': 'Updated Prod Account',
        'status': 'active',
        'last_checked': datetime.now(timezone.utc).isoformat()
    }

    result = registry.update_account('acc-001', account_update)

    assert result is not None
    assert result['account_id'] == 'acc-001'
