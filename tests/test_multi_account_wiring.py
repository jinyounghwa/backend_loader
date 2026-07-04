"""Tests for multi-account wiring: GUARDIAN_ACCOUNTS, account routing,
cross-account checker construction, and ExternalId support."""

import json
from logging import getLogger
from unittest.mock import Mock, patch

import pytest

from guardian.checkers.ec2 import EC2Checker
from guardian.config import Config
from guardian.orchestrator import GuardianOrchestrator


@pytest.fixture(autouse=True)
def _reset_config():
    Config.reset_cache()
    yield
    Config.reset_cache()


def _make_orchestrator(**overrides):
    kwargs = dict(
        logger=getLogger("test"),
        cost_checker=Mock(),
        ec2_checker=Mock(),
        s3_checker=Mock(),
        storage=Mock(),
    )
    kwargs.update(overrides)
    return GuardianOrchestrator(**kwargs)


class TestStaticAccountsConfig:
    def test_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv("GUARDIAN_ACCOUNTS", raising=False)
        assert Config.get_static_accounts() == []

    def test_parses_valid_json(self, monkeypatch):
        accounts = [
            {"account_id": "current", "account_name": "Hub"},
            {"account_id": "222233334444", "account_name": "Prod"},
        ]
        monkeypatch.setenv("GUARDIAN_ACCOUNTS", json.dumps(accounts))
        parsed = Config.get_static_accounts()
        assert len(parsed) == 2
        assert parsed[0]["account_id"] == "current"
        assert parsed[1] == {"account_id": "222233334444", "account_name": "Prod"}

    def test_account_name_defaults_to_id(self, monkeypatch):
        monkeypatch.setenv("GUARDIAN_ACCOUNTS", '[{"account_id": "222233334444"}]')
        assert Config.get_static_accounts()[0]["account_name"] == "222233334444"

    def test_invalid_json_returns_empty(self, monkeypatch):
        monkeypatch.setenv("GUARDIAN_ACCOUNTS", "not-json")
        assert Config.get_static_accounts() == []

    def test_non_array_returns_empty(self, monkeypatch):
        monkeypatch.setenv("GUARDIAN_ACCOUNTS", '{"account_id": "222233334444"}')
        assert Config.get_static_accounts() == []

    def test_invalid_account_id_skipped_others_kept(self, monkeypatch):
        accounts = [
            {"account_id": "12345", "account_name": "bad"},
            {"account_id": "222233334444", "account_name": "good"},
        ]
        monkeypatch.setenv("GUARDIAN_ACCOUNTS", json.dumps(accounts))
        parsed = Config.get_static_accounts()
        assert [a["account_name"] for a in parsed] == ["good"]

    def test_multi_account_enabled_by_static_list(self, monkeypatch):
        monkeypatch.delenv("ORGANIZATIONS_ENABLED", raising=False)
        monkeypatch.setenv("GUARDIAN_ACCOUNTS", '[{"account_id": "222233334444"}]')
        assert Config.is_multi_account_enabled() is True

    def test_multi_account_enabled_by_organizations(self, monkeypatch):
        monkeypatch.delenv("GUARDIAN_ACCOUNTS", raising=False)
        monkeypatch.setenv("ORGANIZATIONS_ENABLED", "true")
        assert Config.is_multi_account_enabled() is True

    def test_multi_account_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("GUARDIAN_ACCOUNTS", raising=False)
        monkeypatch.delenv("ORGANIZATIONS_ENABLED", raising=False)
        assert Config.is_multi_account_enabled() is False


class TestGetAccounts:
    def test_static_accounts_take_priority(self, monkeypatch):
        monkeypatch.setenv(
            "GUARDIAN_ACCOUNTS",
            '[{"account_id": "current"}, {"account_id": "222233334444", "account_name": "Prod"}]',
        )
        monkeypatch.setenv("ORGANIZATIONS_ENABLED", "true")
        orch = _make_orchestrator()
        accounts = orch._get_accounts()
        assert [a["account_id"] for a in accounts] == ["current", "222233334444"]

    def test_defaults_to_current_account(self, monkeypatch):
        monkeypatch.delenv("GUARDIAN_ACCOUNTS", raising=False)
        monkeypatch.delenv("ORGANIZATIONS_ENABLED", raising=False)
        orch = _make_orchestrator()
        assert orch._get_accounts() == [
            {"account_id": "current", "account_name": "Current Account"}
        ]


class TestCrossAccountCheckers:
    CREDS = {
        "aws_access_key_id": "AKIATEST",
        "aws_secret_access_key": "secret",
        "aws_session_token": "token",
    }

    def test_core_checkers_are_replaced_for_member_account(self):
        orch = _make_orchestrator()
        with patch(
            "guardian.orchestrator.AWSClientProvider.get_client_for_account",
            return_value=Mock(),
        ) as cross, patch(
            "guardian.orchestrator.AWSClientProvider.get_client", return_value=Mock()
        ):
            checkers = orch._create_account_checkers("222233334444", self.CREDS)

        # cost/ec2/s3 must not be the hub checkers anymore
        for name in ("cost", "ec2", "s3"):
            assert checkers[name] is not orch.checkers[name], name
            assert checkers[name].account_id == "222233334444"

        cross_services = {c.args[0] for c in cross.call_args_list}
        assert {"ce", "ec2", "s3"} <= cross_services

    def test_ec2_regional_client_uses_member_credentials(self):
        checker = EC2Checker(
            {"ec2": Mock()}, {}, account_id="222233334444", credentials=self.CREDS
        )
        with patch(
            "guardian.checkers.ec2.AWSClientProvider.get_client_for_account",
            return_value=Mock(),
        ) as cross:
            checker._get_regional_client("ap-northeast-2")
        cross.assert_called_once_with(
            "ec2", "222233334444", self.CREDS, region="ap-northeast-2"
        )

    def test_ec2_regional_client_uses_hub_without_credentials(self):
        checker = EC2Checker({"ec2": Mock()}, {})
        with patch(
            "guardian.checkers.ec2.AWSClientProvider.get_client", return_value=Mock()
        ) as hub:
            checker._get_regional_client("us-east-1")
        hub.assert_called_once_with("ec2", region="us-east-1")


class TestExternalId:
    def test_external_id_sent_when_configured(self, monkeypatch):
        monkeypatch.setenv("CROSS_ACCOUNT_EXTERNAL_ID", "guardian-xyz")
        orch = _make_orchestrator()
        sts = Mock()
        sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "AKIA",
                "SecretAccessKey": "s",
                "SessionToken": "t",
            }
        }
        with patch("guardian.orchestrator.AWSClientProvider.get_client", return_value=sts):
            result = orch._assume_role_for_account("222233334444")
        assert result is not None
        assert sts.assume_role.call_args.kwargs["ExternalId"] == "guardian-xyz"

    def test_external_id_omitted_by_default(self, monkeypatch):
        monkeypatch.delenv("CROSS_ACCOUNT_EXTERNAL_ID", raising=False)
        orch = _make_orchestrator()
        sts = Mock()
        sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "AKIA",
                "SecretAccessKey": "s",
                "SessionToken": "t",
            }
        }
        with patch("guardian.orchestrator.AWSClientProvider.get_client", return_value=sts):
            orch._assume_role_for_account("222233334444")
        assert "ExternalId" not in sts.assume_role.call_args.kwargs
