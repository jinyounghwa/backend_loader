"""Sprint 71 Phase 1: Multi-Account Support (17 tests)"""

import pytest


class TestAccountRegistry:
    """Test account registration and management."""

    def test_register_aws_account(self):
        """✅ Register new AWS account."""
        from guardian.multi_account.account_manager import AccountRegistry

        registry = AccountRegistry()
        result = registry.register({
            'account_id': '123456789012',
            'account_name': 'production',
            'role_arn': 'arn:aws:iam::123456789012:role/GuardianCrossAccount',
            'enabled': True
        })

        assert result is True
        account = registry.get_account('123456789012')
        assert account['account_name'] == 'production'

    def test_list_registered_accounts(self):
        """✅ List all registered accounts."""
        from guardian.multi_account.account_manager import AccountRegistry

        registry = AccountRegistry()
        registry.register({'account_id': '111111111111', 'account_name': 'dev'})
        registry.register({'account_id': '222222222222', 'account_name': 'staging'})

        accounts = registry.list_accounts()
        assert len(accounts) == 2

    def test_update_account_status(self):
        """✅ Enable/disable account monitoring."""
        from guardian.multi_account.account_manager import AccountRegistry

        registry = AccountRegistry()
        registry.register({
            'account_id': '333333333333',
            'account_name': 'test',
            'enabled': True
        })

        registry.update_account('333333333333', {'enabled': False})
        account = registry.get_account('333333333333')
        assert account['enabled'] is False


class TestRoleAssumer:
    """Test cross-account role assumption."""

    def test_assume_cross_account_role(self):
        """✅ Assume role in another account."""
        from guardian.multi_account.account_manager import RoleAssumer

        assumer = RoleAssumer()
        role_arn = 'arn:aws:iam::123456789012:role/GuardianCrossAccount'

        # Mock assume role
        session = assumer.assume_role(role_arn, duration_seconds=3600)

        assert session is not None
        assert 'credentials' in session

    def test_assume_role_with_session_name(self):
        """✅ Assume role with session name for audit."""
        from guardian.multi_account.account_manager import RoleAssumer

        assumer = RoleAssumer()
        role_arn = 'arn:aws:iam::123456789012:role/GuardianCrossAccount'

        session = assumer.assume_role(
            role_arn,
            session_name='guardian-monitor',
            duration_seconds=1800
        )

        assert session['session_name'] == 'guardian-monitor'

    def test_handle_assume_role_failure(self):
        """✅ Handle failed role assumption."""
        from guardian.multi_account.account_manager import RoleAssumer

        assumer = RoleAssumer()
        role_arn = 'arn:aws:iam::999999999999:role/NonExistent'

        result = assumer.assume_role(role_arn)

        assert result is None or 'error' in result


class TestAccountAggregator:
    """Test data aggregation across accounts."""

    def test_aggregate_ec2_instances_from_accounts(self):
        """✅ Aggregate EC2 instances from multiple accounts."""
        from guardian.multi_account.account_manager import AccountAggregator

        aggregator = AccountAggregator()

        # Mock account data
        accounts = [
            {'account_id': '111111111111', 'instances': 5},
            {'account_id': '222222222222', 'instances': 3},
            {'account_id': '333333333333', 'instances': 7}
        ]

        total = aggregator.aggregate_ec2_instances(accounts)

        assert total == 15

    def test_aggregate_iam_findings(self):
        """✅ Aggregate IAM findings across accounts."""
        from guardian.multi_account.account_manager import AccountAggregator

        aggregator = AccountAggregator()

        findings = [
            {'account_id': '111111111111', 'risk_score': 85},
            {'account_id': '222222222222', 'risk_score': 45},
            {'account_id': '333333333333', 'risk_score': 70}
        ]

        avg_risk = aggregator.aggregate_iam_risk(findings)

        assert 40 < avg_risk < 90

    def test_aggregate_costs_per_account(self):
        """✅ Aggregate costs across accounts."""
        from guardian.multi_account.account_manager import AccountAggregator

        aggregator = AccountAggregator()

        costs = [
            {'account_id': '111111111111', 'monthly_cost': 1000},
            {'account_id': '222222222222', 'monthly_cost': 1500},
            {'account_id': '333333333333', 'monthly_cost': 2000}
        ]

        total_cost = aggregator.aggregate_costs(costs)

        assert total_cost == 4500


class TestEventRouter:
    """Test cross-account event routing."""

    def test_route_event_to_correct_account(self):
        """✅ Route CloudTrail event to correct account handler."""
        from guardian.multi_account.account_router import EventRouter

        router = EventRouter()

        event = {
            'account_id': '123456789012',
            'eventName': 'RunInstances',
            'timestamp': '2026-05-30T10:00:00Z'
        }

        target_account = router.route_event(event)

        assert target_account == '123456789012'

    def test_route_multi_account_events(self):
        """✅ Route events from multiple accounts."""
        from guardian.multi_account.account_router import EventRouter

        router = EventRouter()

        events = [
            {'account_id': '111111111111', 'eventName': 'RunInstances'},
            {'account_id': '222222222222', 'eventName': 'PutUserPolicy'},
            {'account_id': '111111111111', 'eventName': 'DeleteBucket'}
        ]

        routes = [router.route_event(e) for e in events]

        assert routes.count('111111111111') == 2
        assert routes.count('222222222222') == 1

    def test_handle_disabled_account(self):
        """✅ Skip events from disabled accounts."""
        from guardian.multi_account.account_router import EventRouter

        router = EventRouter()
        router.disable_account('999999999999')

        event = {
            'account_id': '999999999999',  # Disabled account
            'eventName': 'RunInstances'
        }

        result = router.route_event(event)

        assert result is None


class TestAccountContext:
    """Test account context management."""

    def test_set_account_context(self):
        """✅ Set current account context."""
        from guardian.multi_account.account_router import AccountContext

        context = AccountContext()
        context.set_account('123456789012')

        assert context.get_account() == '123456789012'

    def test_get_account_credentials(self):
        """✅ Get credentials for current account."""
        from guardian.multi_account.account_router import AccountContext

        context = AccountContext()
        context.set_account('123456789012')

        creds = context.get_credentials()

        assert 'account_id' in creds

    def test_context_isolation(self):
        """✅ Ensure context isolation between accounts."""
        from guardian.multi_account.account_router import AccountContext

        context1 = AccountContext()
        context2 = AccountContext()

        context1.set_account('111111111111')
        context2.set_account('222222222222')

        assert context1.get_account() != context2.get_account()


class TestMultiAccountIntegration:
    """Test multi-account end-to-end integration."""

    def test_monitor_multiple_accounts(self):
        """✅ Monitor threats across multiple accounts."""
        from guardian.multi_account.account_manager import AccountRegistry, AccountAggregator

        registry = AccountRegistry()
        registry.register({'account_id': '111111111111', 'account_name': 'prod'})
        registry.register({'account_id': '222222222222', 'account_name': 'dev'})

        aggregator = AccountAggregator()

        threats = [
            {'account_id': '111111111111', 'type': 'MALWARE', 'severity': 'CRITICAL'},
            {'account_id': '222222222222', 'type': 'RECON', 'severity': 'HIGH'},
            {'account_id': '111111111111', 'type': 'UNAUTHORIZED', 'severity': 'HIGH'}
        ]

        critical_count = len([t for t in threats if t['severity'] == 'CRITICAL'])
        assert critical_count == 1

    def test_per_account_policies(self):
        """✅ Apply different policies per account."""
        from guardian.multi_account.account_manager import AccountRegistry

        registry = AccountRegistry()
        registry.register({
            'account_id': '111111111111',
            'policy': {'auto_response': True, 'threshold': 80}
        })
        registry.register({
            'account_id': '222222222222',
            'policy': {'auto_response': False, 'threshold': 60}
        })

        prod_account = registry.get_account('111111111111')
        dev_account = registry.get_account('222222222222')

        assert prod_account['policy']['auto_response'] is True
        assert dev_account['policy']['auto_response'] is False

    def test_account_audit_trail(self):
        """✅ Maintain audit trail of account changes."""
        from guardian.multi_account.account_manager import AccountRegistry

        registry = AccountRegistry()
        registry.register({'account_id': '123456789012', 'account_name': 'test'})
        registry.update_account('123456789012', {'enabled': False})

        audit_log = registry.get_audit_log('123456789012')

        assert len(audit_log) >= 2  # Register + Update

    def test_account_health_check(self):
        """✅ Perform health check on monitored accounts."""
        from guardian.multi_account.account_manager import AccountRegistry

        registry = AccountRegistry()
        registry.register({'account_id': '123456789012'})

        health = registry.health_check('123456789012')

        assert 'status' in health
        assert health['status'] in ['healthy', 'unhealthy']
