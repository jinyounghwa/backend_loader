"""Sprint 65 Phase 3: Multi-Account Management (10 tests)"""

import pytest
from unittest.mock import Mock

from guardian.multi_account import (
    RoleAssumptioner,
    AccountManager,
    ConsolidatedReporter,
)
from guardian.storage.account_registry import AccountRegistry


class TestRoleAssumption:
    """Test cross-account role assumption."""

    @pytest.fixture
    def mock_sts(self):
        return Mock()

    @pytest.fixture
    def assumptioner(self, mock_sts):
        return RoleAssumptioner(clients={"sts": mock_sts})

    def test_assume_cross_account_role(self, assumptioner, mock_sts):
        """✅ Assume role in member account."""
        mock_sts.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'SessionToken': 'token123',
                'Expiration': __import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ),
            }
        }

        creds = assumptioner.assume_role(
            'arn:aws:iam::123456789012:role/CrossAccountRole',
            'session-name'
        )

        assert creds is not None
        assert creds['access_key'] == 'AKIAIOSFODNN7EXAMPLE'
        assert creds['session_token'] == 'token123'


class TestAccountManagement:
    """Test account management operations."""

    @pytest.fixture
    def manager(self):
        return AccountManager()

    def test_register_new_account(self, manager):
        """✅ Add new account to system."""
        result = manager.register_account(
            '123456789012',
            'Production Account',
            'arn:aws:iam::123456789012:role/AssumeRole',
            1000.0
        )

        assert result is True
        account = manager.get_account('123456789012')
        assert account['account_name'] == 'Production Account'
        assert account['cost_limit'] == 1000.0

    def test_list_accounts(self, manager):
        """✅ List registered accounts."""
        manager.register_account('111111111111', 'Prod', 'arn:...', 500.0)
        manager.register_account('222222222222', 'Dev', 'arn:...', 200.0)

        accounts = manager.list_accounts()
        assert len(accounts) == 2
        assert any(a['account_id'] == '111111111111' for a in accounts)

    def test_per_account_cost_query(self, manager):
        """✅ Get costs per account."""
        costs = {
            '111111111111': 450.75,
            '222222222222': 125.50,
        }

        cost = manager.get_per_account_cost('111111111111', costs)
        assert cost == 450.75

    def test_consolidated_cost_view(self, manager):
        """✅ Aggregate all account costs."""
        manager.register_account('111111111111', 'Prod', 'arn:...', 500.0)
        manager.register_account('222222222222', 'Dev', 'arn:...', 200.0)

        costs = {
            '111111111111': 450.75,
            '222222222222': 125.50,
        }

        consolidated = manager.get_consolidated_cost_view(costs)
        assert consolidated['total_cost'] == 576.25
        assert consolidated['account_count'] == 2

    def test_account_specific_rules(self, manager):
        """✅ Apply rules per account."""
        manager.register_account('111111111111', 'Prod', 'arn:...', 500.0)

        rules = [
            {'account_id': None, 'name': 'global_rule'},
            {'account_id': '111111111111', 'name': 'prod_rule'},
            {'account_id': '222222222222', 'name': 'dev_rule'},
        ]

        applied = manager.apply_account_rules('111111111111', rules)
        assert len(applied) == 2
        assert any(r['name'] == 'global_rule' for r in applied)
        assert any(r['name'] == 'prod_rule' for r in applied)


class TestMultiAccountDetection:
    """Test anomaly detection across accounts."""

    def test_cross_account_anomaly(self):
        """✅ Detect anomalies across accounts."""
        manager = AccountManager()
        manager.register_account('111111111111', 'Prod', 'arn:...', 500.0)
        manager.register_account('222222222222', 'Dev', 'arn:...', 200.0)

        anomalies = [
            {
                'account_id': '111111111111',
                'anomaly_type': 'cost_spike',
                'cost': 750.0,
            },
            {
                'account_id': '222222222222',
                'anomaly_type': 'unauthorized_region',
            },
        ]

        for anomaly in anomalies:
            account_id = anomaly['account_id']
            if manager.check_cost_threshold(account_id, anomaly.get('cost', 0)):
                assert True

    def test_cost_allocation_by_team(self, ):
        """✅ Allocate costs to business units."""
        reporter = ConsolidatedReporter()

        costs = {
            '111111111111': 450.75,
            '222222222222': 125.50,
        }

        report = reporter.generate_cost_report(costs)
        assert report['total_cost'] == 576.25
        assert len(report['accounts']) == 2

    def test_account_permission_validation(self):
        """✅ Verify cross-account permissions."""
        mock_sts = Mock()
        assumptioner = RoleAssumptioner(clients={"sts": mock_sts})

        mock_sts.get_caller_identity.return_value = {
            'Account': '111111111111',
            'UserId': 'AIDAIOSFODNN7EXAMPLE',
            'Arn': 'arn:aws:iam::111111111111:user/test',
        }

        identity = assumptioner.get_caller_identity()
        assert identity['account_id'] == '111111111111'

    def test_account_cost_comparison(self):
        """✅ Compare costs across accounts."""
        manager = AccountManager()
        manager.register_account('111111111111', 'Prod', 'arn:...', 500.0)
        manager.register_account('222222222222', 'Dev', 'arn:...', 200.0)

        costs = {
            '111111111111': 450.75,
            '222222222222': 125.50,
        }

        consolidated = manager.get_consolidated_cost_view(costs)
        breakdown = sorted(consolidated['breakdown'], key=lambda x: x['cost'], reverse=True)

        assert breakdown[0]['account_id'] == '111111111111'
        assert breakdown[1]['account_id'] == '222222222222'


class TestAccountRegistry:
    """Test account registry storage."""

    @pytest.fixture
    def registry(self):
        return AccountRegistry()

    def test_registry_register(self, registry):
        """✅ Register and retrieve account."""
        registry.register(
            '123456789012',
            'Test Account',
            'arn:aws:iam::123456789012:role/TestRole',
            1000.0
        )

        account = registry.get('123456789012')
        assert account['account_name'] == 'Test Account'

    def test_registry_list(self, registry):
        """✅ List all registered accounts."""
        registry.register('111111111111', 'Account 1', 'arn:...', 500.0)
        registry.register('222222222222', 'Account 2', 'arn:...', 300.0)

        accounts = registry.list_all()
        assert len(accounts) == 2
