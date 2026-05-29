"""Sprint 34 Phase 1: Rule Template Tests

Tests for template storage, repository operations, and template-based rule creation.
Covers RuleTemplate, TemplateRepository, and SecurityRule.create_from_template().
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from storage.rule_template import RuleTemplate, TemplateRepository, BUILTIN_TEMPLATES
from storage.security_rules import SecurityRule, SecurityRuleRepository


class TestRuleTemplate:
    """Test RuleTemplate data class"""

    def test_create_template(self):
        """Test creating a template"""
        template = RuleTemplate(
            template_id="template-1",
            template_name="Connection Spike",
            description="Detect connection spikes",
            rule_type="connection_spike",
            condition_schema={"threshold": int, "window_minutes": int},
            action_schema={"notify": list},
            example_condition={"threshold": 10, "window_minutes": 5},
            example_action={"notify": ["telegram"]},
            tags=["security", "network"],
            version=1,
        )

        assert template.template_id == "template-1"
        assert template.template_name == "Connection Spike"
        assert template.rule_type == "connection_spike"
        assert template.version == 1
        assert "security" in template.tags

    def test_template_to_dynamodb_item(self):
        """Test converting template to DynamoDB item"""
        template = RuleTemplate(
            template_id="template-1",
            template_name="Auth Failure",
            description="Detect auth failures",
            rule_type="auth_failure",
            condition_schema={"threshold": "integer", "time_window": "integer"},
            action_schema={"notify": "list of strings"},
            example_condition={"threshold": 5},
            example_action={"notify": ["discord"]},
            version=1,
        )

        item = template.to_dynamodb_item()

        assert item["template_id"] == "template-1"
        assert item["template_name"] == "Auth Failure"
        assert item["version"] == 1
        assert "condition_schema" in item

    def test_template_from_dynamodb_item(self):
        """Test creating template from DynamoDB item"""
        item = {
            "template_id": "template-1",
            "template_name": "Public Bucket",
            "description": "Detect public buckets",
            "rule_type": "public_bucket",
            "condition_schema": "{}",
            "action_schema": '{"notify": []}',
            "example_condition": "{}",
            "example_action": '{"notify": ["telegram"]}',
            "tags": ["s3", "compliance"],
            "version": 1,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }

        template = RuleTemplate.from_dynamodb_item(item)

        assert template.template_id == "template-1"
        assert template.template_name == "Public Bucket"
        assert template.rule_type == "public_bucket"
        assert len(template.tags) == 2


class TestBuiltinTemplates:
    """Test built-in templates"""

    def test_builtin_templates_exist(self):
        """Test that built-in templates are defined"""
        assert len(BUILTIN_TEMPLATES) == 4

        # Check template names
        names = [t.template_name for t in BUILTIN_TEMPLATES]
        assert "Connection Spike Detection" in names
        assert "Authentication Failure Detection" in names
        assert "Unknown Region Detection" in names
        assert "Public Bucket Detection" in names

    def test_builtin_template_structure(self):
        """Test built-in template has required fields"""
        template = BUILTIN_TEMPLATES[0]  # Connection Spike

        assert template.template_id
        assert template.template_name
        assert template.description
        assert template.rule_type
        assert template.condition_schema
        assert template.action_schema
        assert template.example_condition
        assert template.example_action
        assert template.tags
        assert template.version == 1


class TestTemplateRepository:
    """Test TemplateRepository operations"""

    @pytest.fixture
    def mock_table(self):
        """Mock DynamoDB table"""
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_table):
        """Create repository with mock table"""
        with patch('guardian.storage.rule_template.boto3.resource') as mock_boto3:
            mock_boto3.return_value.Table.return_value = mock_table
            repo = TemplateRepository('test-templates')
            repo.table = mock_table
            return repo

    def test_create_template(self, repo, mock_table):
        """Test creating a template"""
        template = RuleTemplate(
            template_id="",
            template_name="Test Template",
            description="Test",
            rule_type="connection_spike",
            condition_schema={"threshold": "integer", "window_minutes": "integer"},
            action_schema={"notify": "list of strings"},
            example_condition={"threshold": 10},
            example_action={"notify": ["telegram"]},
        )

        result = repo.create_template(template)

        assert result.template_id  # Should have generated ID
        mock_table.put_item.assert_called_once()

    def test_get_template(self, repo, mock_table):
        """Test getting a template"""
        mock_table.get_item.return_value = {
            "Item": {
                "template_id": "template-1",
                "template_name": "Test",
                "description": "Test template",
                "rule_type": "connection_spike",
                "condition_schema": "{}",
                "action_schema": "{}",
                "example_condition": "{}",
                "example_action": "{}",
                "tags": [],
                "version": 1,
                "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }
        }

        template = repo.get_template("template-1")

        assert template is not None
        assert template.template_id == "template-1"
        assert template.template_name == "Test"

    def test_list_templates(self, repo, mock_table):
        """Test listing templates (latest version)"""
        mock_table.scan.return_value = {
            "Items": [
                {
                    "template_id": "template-1",
                    "template_name": "Connection Spike",
                    "description": "Test",
                    "rule_type": "connection_spike",
                    "condition_schema": "{}",
                    "action_schema": "{}",
                    "example_condition": "{}",
                    "example_action": "{}",
                    "tags": [],
                    "version": 1,
                    "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                },
                {
                    "template_id": "template-2",
                    "template_name": "Auth Failure",
                    "description": "Test",
                    "rule_type": "auth_failure",
                    "condition_schema": "{}",
                    "action_schema": "{}",
                    "example_condition": "{}",
                    "example_action": "{}",
                    "tags": [],
                    "version": 1,
                    "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                },
            ]
        }

        templates = repo.list_templates()

        assert len(templates) >= 2
        assert any(t.template_name == "Connection Spike" for t in templates)
        assert any(t.template_name == "Auth Failure" for t in templates)

    def test_update_template(self, repo, mock_table):
        """Test updating a template"""
        template = RuleTemplate(
            template_id="template-1",
            template_name="Updated Template",
            description="Updated",
            rule_type="connection_spike",
            condition_schema={"threshold": "integer", "window_minutes": "integer"},
            action_schema={"notify": "list of strings"},
            example_condition={"threshold": 20},
            example_action={"notify": ["discord"]},
            version=2,
        )

        success = repo.update_template(template)

        assert success is True
        mock_table.put_item.assert_called_once()


class TestSecurityRuleFromTemplate:
    """Test creating SecurityRules from templates"""

    def test_security_rule_has_template_fields(self):
        """Test SecurityRule now has template_id and template_version"""
        rule = SecurityRule(
            rule_id="rule-1",
            rule_type="connection_spike",
            condition={"threshold": 10},
            action={"notify": ["telegram"]},
            priority=5,
            account_id="acc-1",
            template_id="template-1",
            template_version=1,
        )

        assert rule.template_id == "template-1"
        assert rule.template_version == 1

    def test_rule_to_dynamodb_with_template(self):
        """Test rule DynamoDB serialization includes template fields"""
        rule = SecurityRule(
            rule_id="rule-1",
            rule_type="connection_spike",
            condition={"threshold": 10},
            action={"notify": ["telegram"]},
            priority=5,
            template_id="template-1",
            template_version=1,
        )

        item = rule.to_dynamodb_item()

        assert "template_id" in item
        assert "template_version" in item
        assert item["template_id"] == "template-1"
        assert item["template_version"] == 1

    def test_rule_from_dynamodb_with_template(self):
        """Test rule DynamoDB deserialization includes template fields"""
        item = {
            "rule_id": "rule-1",
            "rule_type": "connection_spike",
            "condition": '{"threshold": 10}',
            "action": '{"notify": ["telegram"]}',
            "priority": 5,
            "account_id": "all",
            "enabled": True,
            "template_id": "template-1",
            "template_version": 1,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }

        rule = SecurityRule.from_dynamodb_item(item)

        assert rule.template_id == "template-1"
        assert rule.template_version == 1

    def test_rule_without_template_still_works(self):
        """Test backward compatibility: rules without template fields work"""
        item = {
            "rule_id": "rule-1",
            "rule_type": "connection_spike",
            "condition": '{"threshold": 10}',
            "action": '{"notify": ["telegram"]}',
            "priority": 5,
            "account_id": "all",
            "enabled": True,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }

        rule = SecurityRule.from_dynamodb_item(item)

        assert rule.template_id is None
        assert rule.template_version == 1  # Default value
