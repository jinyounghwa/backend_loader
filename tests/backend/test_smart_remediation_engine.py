"""Sprint 50 Phase 1: Smart Remediation Engine Tests (8 tests)"""

import sys
from pathlib import Path
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.engines.smart_remediation_engine import SmartRemediationEngine
from guardian.orchestrators.remediation_orchestrator import RemediationOrchestrator


class TestSmartRemediationEngine:

    @pytest.fixture
    def orchestrator(self):
        return RemediationOrchestrator(audit_logger=None, max_workers=3)

    @pytest.fixture
    def engine(self, orchestrator):
        return SmartRemediationEngine(orchestrator=orchestrator, audit_logger=None)

    @pytest.fixture
    def sample_threat(self):
        return {
            'threat_id': 'threat-001',
            'threat_type': 'Unauthorized EC2',
            'severity': 7,
            'account_id': 'acc-123',
        }

    @pytest.fixture
    def sample_resources(self):
        return [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'account_id': 'acc-123', 'critical': False},
            {'resource_id': 'i-002', 'resource_type': 'ec2', 'account_id': 'acc-123', 'critical': False},
            {'resource_id': 'sg-001', 'resource_type': 'network', 'account_id': 'acc-123'},
        ]

    def test_severity_to_strategy_mapping(self, engine):
        """✅ Map threat severity to remediation strategy."""
        threat_low = {'threat_id': 'threat-low', 'severity': 2, 'threat_type': 'Test'}
        threat_med = {'threat_id': 'threat-med', 'severity': 5, 'threat_type': 'Test'}
        threat_high = {'threat_id': 'threat-high', 'severity': 7, 'threat_type': 'Test'}
        threat_crit = {'threat_id': 'threat-crit', 'severity': 10, 'threat_type': 'Test'}

        result_low = engine.select_remediation_strategy(threat_low, [])
        assert result_low['selected_strategy'] == 'MONITOR'

        result_med = engine.select_remediation_strategy(threat_med, [])
        assert result_med['selected_strategy'] == 'ISOLATE'

        result_high = engine.select_remediation_strategy(threat_high, [])
        assert result_high['selected_strategy'] == 'REMEDIATE'

        result_crit = engine.select_remediation_strategy(threat_crit, [])
        assert result_crit['selected_strategy'] == 'TERMINATE'

    def test_select_remediation_strategy(self, engine):
        """✅ Select optimal strategy based on threat."""
        threat = {
            'threat_id': 'threat-med',
            'threat_type': 'Unauthorized EC2',
            'severity': 5,
            'account_id': 'acc-123',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
        ]

        result = engine.select_remediation_strategy(threat, resources)

        assert result['threat_id'] == 'threat-med'
        assert result['selected_strategy'] == 'ISOLATE'
        assert result['risk_level'] in ['low', 'medium', 'high', 'critical']
        assert 'estimated_impact' in result
        assert result['safe_to_execute'] is True

    def test_evaluate_risk_vs_impact(self, engine, sample_threat):
        """✅ Analyze risk if no action vs impact if remediate."""
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2'},
        ]

        analysis = engine.evaluate_risk_vs_impact(sample_threat, resources)

        assert 'risk_if_no_action' in analysis
        assert 'impact_if_remediate' in analysis
        assert 'risk_score' in analysis
        assert 'impact_score' in analysis
        assert 'recommendation' in analysis
        assert analysis['risk_score'] >= 0
        assert analysis['impact_score'] >= 0

    def test_predict_success_probability(self, engine, sample_threat, sample_resources):
        """✅ Predict remediation success rate."""
        prediction = engine.predict_success_probability(sample_threat, sample_resources)

        assert prediction['success_probability'] >= 0.5
        assert prediction['success_probability'] <= 1.0
        assert prediction['confidence'] > 0
        assert isinstance(prediction['risk_factors'], list)
        assert isinstance(prediction['mitigating_factors'], list)

    def test_strategy_with_low_risk_resources(self, engine):
        """✅ Strategy selection respects resource risk level."""
        threat = {
            'threat_id': 'threat-high',
            'severity': 8,
            'threat_type': 'Unauthorized EC2',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': False},
        ]

        result = engine.select_remediation_strategy(threat, resources)

        assert result['selected_strategy'] == 'REMEDIATE'
        assert result['safe_to_execute'] is True

    def test_strategy_with_critical_resources(self, engine):
        """✅ Strategy respects critical resource protection."""
        threat = {
            'threat_id': 'threat-crit',
            'severity': 10,
            'threat_type': 'Unauthorized EC2',
        }
        resources = [
            {'resource_id': 'i-001', 'resource_type': 'ec2', 'critical': True},
        ]

        result = engine.select_remediation_strategy(threat, resources)

        assert result['selected_strategy'] == 'TERMINATE'
        assert result['safe_to_execute'] is False

    def test_execute_with_strategy(self, engine, sample_threat):
        """✅ Execute remediation with selected strategy."""
        resources = [
            {'resource_id': 'sg-001', 'resource_type': 'network'},
        ]

        result = engine.execute_with_strategy(sample_threat, resources)

        assert 'orchestration_id' in result
        assert 'strategy_used' in result
        assert result['execution_result'] in ['success', 'partial', 'failed']
        assert 'actions_taken' in result
        assert 'outcome_summary' in result

    def test_get_strategy_summary(self, engine, sample_threat):
        """✅ Summarize strategy decisions and outcomes."""
        resources_1 = [{'resource_id': 'i-001', 'resource_type': 'ec2'}]
        resources_2 = [{'resource_id': 'sg-001', 'resource_type': 'network'}]

        engine.select_remediation_strategy(sample_threat, resources_1)
        engine.select_remediation_strategy(sample_threat, resources_2)

        summary = engine.get_strategy_summary()

        assert summary['total_decisions'] == 2
        assert 'strategies_used' in summary
        assert summary['success_rate'] >= 0
        assert summary['average_risk_score'] >= 0
        assert summary['critical_threats_handled'] >= 0
