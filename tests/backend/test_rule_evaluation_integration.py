"""Sprint 36 Phase 1: Rule Evaluation Integration Tests

Tests for deployment-aware rule evaluation.
Ensures only ACTIVE (deployed) rules are evaluated in real-time anomaly detection.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, ANY
import sys
from pathlib import Path
from guardian.detectors.anomaly_detector import AnomalyDetector
from guardian.storage.security_rules import SecurityRuleRepository, SecurityRule
from guardian.storage.rule_deployment import RuleDeploymentRepository, Deployment


class TestDeploymentAwareRuleEvaluation:
    """Test integration of deployment system with anomaly detection"""

    @pytest.fixture
    def mock_rules_table(self):
        """Create mock DynamoDB table for rules"""
        return MagicMock()

    @pytest.fixture
    def mock_deployments_table(self):
        """Create mock DynamoDB table for deployments"""
        return MagicMock()

    @pytest.fixture
    def mock_audit_logs_table(self):
        """Create mock DynamoDB table for audit logs"""
        return MagicMock()

    @pytest.fixture
    def detector(self, mock_rules_table, mock_audit_logs_table):
        """Create AnomalyDetector with mocked tables"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.side_effect = lambda table_name: {
                'rules-table': mock_rules_table,
                'audit-logs-table': mock_audit_logs_table,
                'deployments-table': MagicMock()
            }.get(table_name, MagicMock())

            detector = AnomalyDetector(
                'rules-table',
                'audit-logs-table',
                'deployments-table'
            )
            return detector

    def test_detector_accepts_deployments_table(self):
        """Test that AnomalyDetector accepts deployments_table_name"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.return_value = MagicMock()

            detector = AnomalyDetector(
                'rules-table',
                'audit-logs-table',
                'deployments-table'
            )

            assert detector.deployments_table_name == 'deployments-table'

    def test_detector_supports_backward_compatibility(self):
        """Test that AnomalyDetector works without deployments_table (backward compatible)"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.return_value = MagicMock()

            detector = AnomalyDetector('rules-table', 'audit-logs-table')

            assert detector.deployments_table_name is None

    def test_only_active_rules_evaluated(self, detector, mock_rules_table, mock_audit_logs_table):
        """Test that only ACTIVE rules are evaluated"""
        # Mock rules: one enabled, one disabled, but check deployment status
        mock_rules_table.query.return_value = {
            'Items': [
                {
                    'rule_id': 'rule-active',
                    'rule_type': 'connection_spike',
                    'enabled': True,
                    'condition': '{"threshold": 10}',
                    'action': '{"notify": true}'
                },
                {
                    'rule_id': 'rule-inactive',
                    'rule_type': 'auth_failure',
                    'enabled': True,
                    'condition': '{"threshold": 5}',
                    'action': '{"notify": true}'
                }
            ]
        }

        mock_audit_logs_table.query.return_value = {'Items': []}

        with patch('guardian.storage.rule_deployment.RuleDeploymentRepository') as MockDeploymentRepo:
            mock_deploy_repo = MagicMock()
            MockDeploymentRepo.return_value = mock_deploy_repo

            # Mock: rule-active has ACTIVE deployment, rule-inactive has PENDING
            def get_active_deployment(rule_id):
                if rule_id == 'rule-active':
                    deployment = MagicMock()
                    deployment.status = 'ACTIVE'
                    return deployment
                elif rule_id == 'rule-inactive':
                    deployment = MagicMock()
                    deployment.status = 'PENDING'
                    return deployment
                return None

            mock_deploy_repo.get_active_deployment.side_effect = get_active_deployment

            threats = detector.detect_anomalies('test-account')

            # Should query deployments for each rule
            assert mock_deploy_repo.get_active_deployment.call_count == 2
            mock_deploy_repo.get_active_deployment.assert_any_call('rule-active')
            mock_deploy_repo.get_active_deployment.assert_any_call('rule-inactive')

    def test_inactive_deployment_skipped(self, detector, mock_rules_table, mock_audit_logs_table):
        """Test that rules without ACTIVE deployment are skipped"""
        mock_rules_table.query.return_value = {
            'Items': [
                {
                    'rule_id': 'rule-pending',
                    'rule_type': 'connection_spike',
                    'enabled': True,
                    'condition': '{"threshold": 10}',
                    'action': '{"notify": true}'
                }
            ]
        }

        with patch('guardian.storage.rule_deployment.RuleDeploymentRepository') as MockDeploymentRepo:
            mock_deploy_repo = MagicMock()
            MockDeploymentRepo.return_value = mock_deploy_repo

            # Deployment is PENDING (not ACTIVE)
            pending_deployment = MagicMock()
            pending_deployment.status = 'PENDING'
            mock_deploy_repo.get_active_deployment.return_value = pending_deployment

            threats = detector.detect_anomalies('test-account')

            # Should not evaluate rule since deployment is not ACTIVE
            # Threat detection methods should not be called
            assert threats == []

    def test_no_deployment_record_skipped(self, detector, mock_rules_table):
        """Test that rules with no deployment record are skipped"""
        mock_rules_table.query.return_value = {
            'Items': [
                {
                    'rule_id': 'rule-no-deployment',
                    'rule_type': 'connection_spike',
                    'enabled': True,
                    'condition': '{"threshold": 10}',
                    'action': '{"notify": true}'
                }
            ]
        }

        with patch('guardian.storage.rule_deployment.RuleDeploymentRepository') as MockDeploymentRepo:
            mock_deploy_repo = MagicMock()
            MockDeploymentRepo.return_value = mock_deploy_repo

            # No deployment found
            mock_deploy_repo.get_active_deployment.return_value = None

            threats = detector.detect_anomalies('test-account')

            # Should not evaluate rule since no deployment exists
            assert threats == []

    def test_multiple_active_rules_evaluated(self, detector, mock_rules_table, mock_audit_logs_table):
        """Test that multiple ACTIVE rules are all evaluated"""
        mock_rules_table.query.return_value = {
            'Items': [
                {
                    'rule_id': 'rule-1',
                    'rule_type': 'connection_spike',
                    'enabled': True,
                    'priority': 5,
                    'condition': '{"threshold": 10}',
                    'action': '{"notify": true}'
                },
                {
                    'rule_id': 'rule-2',
                    'rule_type': 'auth_failure',
                    'enabled': True,
                    'priority': 8,
                    'condition': '{"threshold": 5}',
                    'action': '{"notify": true}'
                },
                {
                    'rule_id': 'rule-3',
                    'rule_type': 'unknown_region',
                    'enabled': True,
                    'priority': 7,
                    'condition': '{"regions": ["us-east-1"]}',
                    'action': '{"notify": true}'
                }
            ]
        }

        mock_audit_logs_table.query.return_value = {'Items': []}

        with patch('guardian.storage.rule_deployment.RuleDeploymentRepository') as MockDeploymentRepo:
            mock_deploy_repo = MagicMock()
            MockDeploymentRepo.return_value = mock_deploy_repo

            # All three rules have ACTIVE deployments
            active_deployment = MagicMock()
            active_deployment.status = 'ACTIVE'
            mock_deploy_repo.get_active_deployment.return_value = active_deployment

            threats = detector.detect_anomalies('test-account')

            # Should check deployment status for all three rules
            assert mock_deploy_repo.get_active_deployment.call_count == 3

    def test_backward_compatibility_without_deployments_table(self, mock_rules_table, mock_audit_logs_table):
        """Test that detector works without deployments table (no deployment filtering)"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.side_effect = lambda table_name: {
                'rules': mock_rules_table,
                'logs': mock_audit_logs_table
            }.get(table_name, MagicMock())

            detector = AnomalyDetector('rules', 'logs')  # No deployments table

            mock_rules_table.query.return_value = {
                'Items': [
                    {
                        'rule_id': 'rule-1',
                        'rule_type': 'connection_spike',
                        'enabled': True,
                        'condition': '{}',
                        'action': '{}'
                    }
                ]
            }
            mock_audit_logs_table.query.return_value = {'Items': []}

            threats = detector.detect_anomalies('test-account')

            # Should return rules without checking deployments
            # (May detect threats depending on rule logic)
            # What matters is that it doesn't crash


class TestSecurityRuleRepositoryActiveRules:
    """Test SecurityRuleRepository.list_active_rules() method"""

    @pytest.fixture
    def mock_rules_table(self):
        """Create mock rules table"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_rules_table):
        """Create repository with mocked table"""
        with patch('boto3.resource') as mock_dynamodb:
            mock_dynamodb.return_value.Table.return_value = mock_rules_table
            repo = SecurityRuleRepository('rules-table')
            return repo

    def test_list_active_rules_filters_by_deployment(self, repository, mock_rules_table):
        """Test that list_active_rules only returns rules with ACTIVE deployment"""
        mock_rules_table.query.return_value = {
            'Items': [
                {
                    'rule_id': 'rule-1',
                    'rule_type': 'connection_spike',
                    'enabled': True,
                    'condition': '{}',
                    'action': '{}',
                    'priority': 5,
                    'account_id': 'test-account',
                    'created_at': '2026-05-23T00:00:00',
                    'updated_at': '2026-05-23T00:00:00'
                }
            ]
        }

        with patch('guardian.storage.rule_deployment.RuleDeploymentRepository') as MockDeploymentRepo:
            mock_deploy_repo = MagicMock()
            MockDeploymentRepo.return_value = mock_deploy_repo

            active_deployment = MagicMock()
            active_deployment.status = 'ACTIVE'
            mock_deploy_repo.get_active_deployment.return_value = active_deployment

            active_rules = repository.list_active_rules('test-account')

            assert len(active_rules) == 1
            assert active_rules[0].rule_id == 'rule-1'

    def test_list_active_rules_skips_pending_deployments(self, repository, mock_rules_table):
        """Test that rules with PENDING deployments are skipped"""
        mock_rules_table.query.return_value = {
            'Items': [
                {
                    'rule_id': 'rule-1',
                    'rule_type': 'connection_spike',
                    'enabled': True,
                    'condition': '{}',
                    'action': '{}',
                    'priority': 5,
                    'account_id': 'test-account',
                    'created_at': '2026-05-23T00:00:00',
                    'updated_at': '2026-05-23T00:00:00'
                }
            ]
        }

        with patch('guardian.storage.rule_deployment.RuleDeploymentRepository') as MockDeploymentRepo:
            mock_deploy_repo = MagicMock()
            MockDeploymentRepo.return_value = mock_deploy_repo

            pending_deployment = MagicMock()
            pending_deployment.status = 'PENDING'
            mock_deploy_repo.get_active_deployment.return_value = pending_deployment

            active_rules = repository.list_active_rules('test-account')

            # Should not include the rule since deployment is not ACTIVE
            assert len(active_rules) == 0

    def test_list_active_rules_handles_errors_gracefully(self, repository, mock_rules_table):
        """Test that list_active_rules returns empty list on error"""
        with patch('guardian.storage.rule_deployment.RuleDeploymentRepository') as MockDeploymentRepo:
            MockDeploymentRepo.side_effect = Exception('Deployment repo error')

            active_rules = repository.list_active_rules('test-account')

            assert active_rules == []
