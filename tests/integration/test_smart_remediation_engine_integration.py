"""Sprint 50 Phase 1: Smart Remediation Engine Integration Tests (7 tests)"""

import sys
from pathlib import Path
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.engines.smart_remediation_engine import SmartRemediationEngine
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator


class TestSmartRemediationEngineIntegration:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    @pytest.fixture
    def engine(self, orchestrator):
        return SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

    def test_end_to_end_threat_to_remediation(self, engine):
        """✅ Complete flow: threat detection → strategy → execution."""
        threat = {
            'threat_id': 'threat-e2e',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'critical': False},
            {'resource_id': 'sg-001', 'resource_type': 'network', 'account_id': 'acc-123'},
        ]

        result = engine.execute_with_strategy(threat, resources)

        assert result['strategy_used'] == 'REMEDIATE'
        assert result['execution_result'] in ['success', 'partial']

    def test_low_severity_threat_monitoring_only(self, engine):
        """✅ Low severity threats trigger monitoring, not remediation."""
        threat = {
            'threat_id': 'threat-low',
            'threat_type': 'Unusual Activity',
            'severity': 2,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2'},
        ]

        result = engine.select_remediation_strategy(threat, resources)

        assert result['selected_strategy'] == 'MONITOR'
        assert len(result['recommended_actions']) == 0

    def test_medium_severity_isolation_strategy(self, engine):
        """✅ Medium threats use isolation without termination."""
        threat = {
            'threat_id': 'threat-med',
            'threat_type': 'Unauthorized Access',
            'severity': 5,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
            {'resource_id': 'sg-001', 'resource_type': 'network'},
        ]

        result = engine.select_remediation_strategy(threat, resources)

        assert result['selected_strategy'] == 'ISOLATE'
        assert 'ec2_terminate' not in result['recommended_actions']
        assert 'network_isolation' in result['recommended_actions'] or len(result['recommended_actions']) > 0

    def test_high_severity_full_remediation(self, engine):
        """✅ High severity triggers full remediation."""
        threat = {
            'threat_id': 'threat-high',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2'},
            {'resource_id': 'sg-001', 'resource_type': 'network'},
            {'resource_id': 'bucket-001', 'resource_type': 's3'},
        ]

        result = engine.select_remediation_strategy(threat, resources)

        assert result['selected_strategy'] == 'REMEDIATE'
        assert 'network_isolation' in result['recommended_actions']

    def test_critical_threat_aggressive_response(self, engine):
        """✅ Critical threats allow aggressive action."""
        threat = {
            'threat_id': 'threat-crit',
            'threat_type': 'Unauthorized EC2',
            'severity': 10,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
        ]

        result = engine.select_remediation_strategy(threat, resources)

        assert result['selected_strategy'] == 'TERMINATE'
        assert 'ec2_terminate' in result['recommended_actions']

    def test_risk_vs_impact_decision_making(self, engine):
        """✅ Strategy respects risk-vs-impact tradeoffs."""
        threat_high_risk = {
            'threat_id': 'threat-high-risk',
            'threat_type': 'Network Breach',
            'severity': 9,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'sg-001', 'resource_type': 'network'},
        ]

        analysis = engine.evaluate_risk_vs_impact(threat_high_risk, resources)

        assert analysis['risk_score'] > 0
        assert analysis['impact_score'] >= 0
        assert 'recommendation' in analysis

    def test_strategy_recommendations_without_execution(self, engine):
        """✅ Provide recommendations without executing."""
        threat = {
            'threat_id': 'threat-rec',
            'threat_type': 'Unauthorized EC2',
            'severity': 8,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2'},
        ]

        recommendations = engine.get_strategy_recommendations(threat, resources)

        assert 'strategy' in recommendations
        assert 'actions' in recommendations
        assert 'warnings' in recommendations
        assert 'approval_required' in recommendations
        assert isinstance(recommendations['actions'], list)
