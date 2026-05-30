"""Sprint 72 Phase 3: Custom Rule Builder (15 tests)"""

import pytest
from datetime import datetime


class TestRuleBuilder:
    """Test custom rule creation."""

    def test_create_simple_rule(self):
        """✅ Create simple IF-THEN rule."""
        from guardian.rules.rule_builder import RuleBuilder

        builder = RuleBuilder()

        rule = builder.create({
            'name': 'Stop Critical Threats',
            'condition': "threat.severity == 'CRITICAL'",
            'actions': ['STOP_INSTANCE', 'NOTIFY_SLACK']
        })

        assert rule['rule_id']
        assert rule['status'] == 'active'
        assert rule['name'] == 'Stop Critical Threats'

    def test_create_rule_with_multiple_conditions(self):
        """✅ Create rule with AND/OR conditions."""
        from guardian.rules.rule_builder import RuleBuilder

        builder = RuleBuilder()

        rule = builder.create({
            'name': 'Alert on High Cost OR Critical Threat',
            'condition': "(cost.daily > 100) OR (threat.severity == 'CRITICAL')",
            'actions': ['NOTIFY_SLACK', 'ESCALATE']
        })

        assert rule['rule_id']
        assert 'OR' in rule['condition']

    def test_create_rule_with_variables(self):
        """✅ Create rule with variable references."""
        from guardian.rules.rule_builder import RuleBuilder

        builder = RuleBuilder()

        rule = builder.create({
            'name': 'Dynamic Budget Alert',
            'condition': f"cost.daily > 100",
            'actions': ['NOTIFY_SLACK']
        })

        assert rule['rule_id']
        assert '100' in rule['condition']


class TestRuleValidator:
    """Test rule validation."""

    def test_validate_correct_syntax(self):
        """✅ Validate syntactically correct rule."""
        from guardian.rules.rule_builder import RuleValidator

        validator = RuleValidator()

        result = validator.validate({
            'condition': "threat.severity == 'CRITICAL'",
            'actions': ['STOP_INSTANCE']
        })

        assert result['valid'] is True
        assert 'errors' not in result or len(result.get('errors', [])) == 0

    def test_reject_invalid_syntax(self):
        """✅ Reject invalid rule syntax."""
        from guardian.rules.rule_builder import RuleValidator

        validator = RuleValidator()

        result = validator.validate({
            'condition': "threat.severity == 'CRITICAL'",
            'actions': []  # Empty actions
        })

        assert result['valid'] is False
        assert 'errors' in result

    def test_validate_action_names(self):
        """✅ Validate action names are recognized."""
        from guardian.rules.rule_builder import RuleValidator

        validator = RuleValidator()

        # Valid actions
        result = validator.validate({
            'condition': "threat.severity == 'HIGH'",
            'actions': ['STOP_INSTANCE', 'NOTIFY_SLACK']
        })
        assert result['valid'] is True

        # Invalid action
        result = validator.validate({
            'condition': "threat.severity == 'HIGH'",
            'actions': ['INVALID_ACTION']
        })
        assert result['valid'] is False


class TestRuleExecution:
    """Test rule evaluation and execution."""

    def test_execute_rule_matching(self):
        """✅ Execute rule and return matching result."""
        from guardian.rules.rule_builder import RuleExecutor

        executor = RuleExecutor()

        rule = {
            'rule_id': 'rule_1',
            'condition': "threat.severity == 'CRITICAL'",
            'actions': ['ISOLATE', 'NOTIFY']
        }

        threat = {'severity': 'CRITICAL', 'type': 'MALWARE'}

        actions = executor.execute(rule, threat)

        assert 'ISOLATE' in actions
        assert 'NOTIFY' in actions

    def test_execute_rule_not_matching(self):
        """✅ Return empty actions when rule doesn't match."""
        from guardian.rules.rule_builder import RuleExecutor

        executor = RuleExecutor()

        rule = {
            'condition': "threat.severity == 'CRITICAL'",
            'actions': ['ISOLATE']
        }

        threat = {'severity': 'LOW'}

        actions = executor.execute(rule, threat)

        assert len(actions) == 0

    def test_execute_rule_with_complex_condition(self):
        """✅ Execute rule with AND/OR logic."""
        from guardian.rules.rule_builder import RuleExecutor

        executor = RuleExecutor()

        rule = {
            'condition': "(threat.severity == 'CRITICAL') OR (cost.daily > 100)",
            'actions': ['ALERT']
        }

        # Threat severity match
        event1 = {'threat': {'severity': 'CRITICAL'}, 'cost': {'daily': 50}}
        actions1 = executor.execute(rule, event1)
        assert 'ALERT' in actions1

        # Cost match
        event2 = {'threat': {'severity': 'LOW'}, 'cost': {'daily': 150}}
        actions2 = executor.execute(rule, event2)
        assert 'ALERT' in actions2

        # No match
        event3 = {'threat': {'severity': 'MEDIUM'}, 'cost': {'daily': 50}}
        actions3 = executor.execute(rule, event3)
        assert len(actions3) == 0


class TestRuleLibrary:
    """Test rule templates and library."""

    def test_get_default_rules(self):
        """✅ Get list of default rule templates."""
        from guardian.rules.rule_builder import RuleLibrary

        library = RuleLibrary()

        templates = library.get_templates()

        assert len(templates) > 0
        assert any('CRITICAL' in t.get('name', '') for t in templates)

    def test_create_from_template(self):
        """✅ Create rule from template."""
        from guardian.rules.rule_builder import RuleLibrary

        library = RuleLibrary()

        rule = library.create_from_template('stop_critical_threats')

        assert rule['rule_id']
        assert 'CRITICAL' in rule.get('condition', '')

    def test_list_available_templates(self):
        """✅ List all available templates."""
        from guardian.rules.rule_builder import RuleLibrary

        library = RuleLibrary()

        templates = library.list_templates()

        assert isinstance(templates, list)
        assert all('name' in t for t in templates)
        assert all('description' in t for t in templates)


class TestRuleIntegration:
    """Test end-to-end rule workflows."""

    def test_create_validate_execute_workflow(self):
        """✅ Complete workflow: create, validate, execute rule."""
        from guardian.rules.rule_builder import (
            RuleBuilder, RuleValidator, RuleExecutor
        )

        builder = RuleBuilder()
        validator = RuleValidator()
        executor = RuleExecutor()

        # Create
        rule = builder.create({
            'name': 'Auto-Stop Critical',
            'condition': "threat.severity == 'CRITICAL'",
            'actions': ['STOP_INSTANCE']
        })

        # Validate
        valid = validator.validate(rule)
        assert valid['valid'] is True

        # Execute
        threat = {'severity': 'CRITICAL'}
        actions = executor.execute(rule, threat)
        assert 'STOP_INSTANCE' in actions

    def test_rule_library_workflow(self):
        """✅ Use library templates for quick setup."""
        from guardian.rules.rule_builder import RuleLibrary, RuleExecutor

        library = RuleLibrary()
        executor = RuleExecutor()

        # Get template
        rule = library.create_from_template('high_cost_alert')

        # Execute against event
        event = {'cost': {'daily': 150}}

        actions = executor.execute(rule, event)

        assert len(actions) > 0

    def test_multiple_rules_evaluation(self):
        """✅ Evaluate multiple rules against event."""
        from guardian.rules.rule_builder import RuleExecutor

        executor = RuleExecutor()

        rules = [
            {'condition': "threat.severity == 'CRITICAL'", 'actions': ['ISOLATE']},
            {'condition': "cost.daily > 100", 'actions': ['ALERT']},
            {'condition': "threat.type == 'MALWARE'", 'actions': ['BLOCK']}
        ]

        event = {
            'threat': {'severity': 'CRITICAL', 'type': 'MALWARE'},
            'cost': {'daily': 150}
        }

        all_actions = set()
        for rule in rules:
            actions = executor.execute(rule, event)
            all_actions.update(actions)

        assert len(all_actions) >= 2  # At least 2 rules match

    def test_rule_performance_under_load(self):
        """✅ Rule execution performs < 50ms per rule."""
        from guardian.rules.rule_builder import RuleExecutor
        import time

        executor = RuleExecutor()

        rule = {
            'condition': "threat.severity == 'CRITICAL'",
            'actions': ['STOP_INSTANCE']
        }

        event = {'severity': 'CRITICAL'}

        start = time.time()
        for _ in range(100):
            executor.execute(rule, event)
        duration = (time.time() - start) * 1000 / 100  # ms per execution

        assert duration < 50
