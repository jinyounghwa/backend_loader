"""Sprint 70 Phase 3: GuardDuty Integration & Threat Correlation (17 tests)"""

import pytest
from datetime import datetime


class TestGuardDutyEventCollector:
    """Test GuardDuty finding collection."""

    def test_collect_ec2_reconnaissance_finding(self):
        """✅ Collect EC2 reconnaissance finding."""
        from guardian.integrations.guardduty_connector import GuardDutyEventCollector

        finding = {
            'Id': 'finding-123',
            'Type': 'Recon.EC2/Portscan',
            'Severity': 4.5,
            'UpdatedAt': '2026-05-30T10:00:00Z',
            'Resource': {
                'InstanceDetails': {
                    'InstanceId': 'i-12345678'
                }
            }
        }

        collector = GuardDutyEventCollector()
        result = collector.collect(finding)

        assert result['finding_id'] == 'finding-123'
        assert result['threat_type'] == 'RECON'
        assert result['resource_id'] == 'i-12345678'

    def test_collect_credential_access_finding(self):
        """✅ Collect credential access finding."""
        from guardian.integrations.guardduty_connector import GuardDutyEventCollector

        finding = {
            'Id': 'finding-456',
            'Type': 'CryptoCurrency.EC2/BitcoinTool.B!DNS',
            'Severity': 7.0,
            'UpdatedAt': '2026-05-30T11:00:00Z',
            'Resource': {
                'InstanceDetails': {
                    'InstanceId': 'i-87654321'
                }
            }
        }

        collector = GuardDutyEventCollector()
        result = collector.collect(finding)

        assert result['finding_id'] == 'finding-456'
        assert result['threat_type'] == 'MALWARE'
        assert result['severity_score'] >= 7.0

    def test_collect_unauthorized_api_finding(self):
        """✅ Collect unauthorized API call finding."""
        from guardian.integrations.guardduty_connector import GuardDutyEventCollector

        finding = {
            'Id': 'finding-789',
            'Type': 'UnauthorizedAccess.IAMUser/MaliciousIPCaller.Custom',
            'Severity': 6.0,
            'UpdatedAt': '2026-05-30T12:00:00Z',
            'Principal': {
                'AWSAccountId': '123456789012'
            }
        }

        collector = GuardDutyEventCollector()
        result = collector.collect(finding)

        assert result['finding_id'] == 'finding-789'
        assert result['threat_type'] == 'UNAUTHORIZED_ACCESS'


class TestThreatSeverityClassifier:
    """Test threat severity classification."""

    def test_classify_critical_severity(self):
        """✅ Classify severity >= 7.0 as CRITICAL."""
        from guardian.integrations.guardduty_connector import ThreatSeverityClassifier

        finding = {
            'Type': 'Trojan.EC2/BlackholeTraffic!DNS',
            'Severity': 8.5,
            'Resource': {'InstanceDetails': {'InstanceId': 'i-123'}}
        }

        classifier = ThreatSeverityClassifier()
        result = classifier.classify(finding)

        assert result['severity_level'] == 'CRITICAL'
        assert result['risk_score'] > 80

    def test_classify_high_severity(self):
        """✅ Classify severity 5.0-6.9 as HIGH."""
        from guardian.integrations.guardduty_connector import ThreatSeverityClassifier

        finding = {
            'Type': 'UnauthorizedAccess.EC2/SSHBruteForce',
            'Severity': 6.0,
            'Resource': {'InstanceDetails': {'InstanceId': 'i-456'}}
        }

        classifier = ThreatSeverityClassifier()
        result = classifier.classify(finding)

        assert result['severity_level'] == 'HIGH'
        assert result['risk_score'] >= 60

    def test_classify_medium_severity(self):
        """✅ Classify severity 3.0-4.9 as MEDIUM."""
        from guardian.integrations.guardduty_connector import ThreatSeverityClassifier

        finding = {
            'Type': 'CryptoCurrency.EC2/BitcoinTool.B!DNS',
            'Severity': 4.0,
            'Resource': {'InstanceDetails': {'InstanceId': 'i-789'}}
        }

        classifier = ThreatSeverityClassifier()
        result = classifier.classify(finding)

        assert result['severity_level'] == 'MEDIUM'
        assert 40 <= result['risk_score'] < 60

    def test_classify_low_severity(self):
        """✅ Classify severity < 3.0 as LOW."""
        from guardian.integrations.guardduty_connector import ThreatSeverityClassifier

        finding = {
            'Type': 'Recon.EC2/NetworkPortUnusual',
            'Severity': 2.0,
            'Resource': {'InstanceDetails': {'InstanceId': 'i-999'}}
        }

        classifier = ThreatSeverityClassifier()
        result = classifier.classify(finding)

        assert result['severity_level'] == 'LOW'
        assert result['risk_score'] < 40


class TestThreatCorrelationEngine:
    """Test multi-signal correlation for campaign detection."""

    def test_correlate_cloudtrail_and_guardduty(self):
        """✅ Correlate CloudTrail and GuardDuty signals."""
        from guardian.integrations.guardduty_connector import ThreatCorrelationEngine

        cloudtrail_signal = {
            'eventName': 'UnauthorizedOperation',
            'sourceIPAddress': '203.0.113.100',
            'timestamp': '2026-05-30T10:00:00Z'
        }

        guardduty_signal = {
            'Type': 'UnauthorizedAccess.EC2/MaliciousIPCaller',
            'SourceIP': '203.0.113.100',
            'Timestamp': '2026-05-30T10:05:00Z'
        }

        engine = ThreatCorrelationEngine()
        result = engine.correlate([cloudtrail_signal], [guardduty_signal])

        assert result['is_correlated'] is True
        assert result['correlation_score'] > 70
        assert 'campaign' in result['result_type'].lower()

    def test_correlate_multiple_instances_same_malware(self):
        """✅ Detect campaign: same malware on multiple instances."""
        from guardian.integrations.guardduty_connector import ThreatCorrelationEngine

        signals = [
            {
                'Type': 'Trojan.EC2/BitcoinTool.B!DNS',
                'Resource': {'InstanceDetails': {'InstanceId': 'i-111'}},
                'Timestamp': '2026-05-30T10:00:00Z'
            },
            {
                'Type': 'Trojan.EC2/BitcoinTool.B!DNS',
                'Resource': {'InstanceDetails': {'InstanceId': 'i-222'}},
                'Timestamp': '2026-05-30T10:10:00Z'
            },
            {
                'Type': 'Trojan.EC2/BitcoinTool.B!DNS',
                'Resource': {'InstanceDetails': {'InstanceId': 'i-333'}},
                'Timestamp': '2026-05-30T10:20:00Z'
            }
        ]

        engine = ThreatCorrelationEngine()
        result = engine.correlate_signals(signals)

        assert result['is_campaign'] is True
        assert result['affected_resources'] == 3

    def test_detect_privilege_escalation_campaign(self):
        """✅ Detect campaign: IAM escalation + unauthorized API calls."""
        from guardian.integrations.guardduty_connector import ThreatCorrelationEngine

        signals = [
            {'signal_type': 'IAM_ESCALATION', 'timestamp': '2026-05-30T10:00:00Z'},
            {'signal_type': 'UNAUTHORIZED_API', 'timestamp': '2026-05-30T10:05:00Z'},
            {'signal_type': 'DATA_EXFILTRATION', 'timestamp': '2026-05-30T10:10:00Z'},
        ]

        engine = ThreatCorrelationEngine()
        result = engine.detect_attack_pattern(signals)

        assert result['is_attack'] is True
        assert result['attack_pattern'] == 'privilege_escalation'


class TestGuardDutyAutoResponder:
    """Test automatic response to GuardDuty findings."""

    def test_respond_to_critical_ec2_threat(self):
        """✅ Auto-respond to critical EC2 threat."""
        from guardian.responders.guardduty_responder import GuardDutyAutoResponder

        finding = {
            'Id': 'finding-critical',
            'Type': 'Trojan.EC2/BitcoinTool.B!DNS',
            'Severity': 8.0,
            'Resource': {
                'InstanceDetails': {
                    'InstanceId': 'i-compromised'
                }
            }
        }

        responder = GuardDutyAutoResponder()
        response = responder.respond(finding)

        assert response['action'] == 'ISOLATE'
        assert response['target'] == 'i-compromised'
        assert response['reason'] == 'critical_malware_detected'

    def test_respond_to_high_unauthorized_access(self):
        """✅ Auto-respond to high unauthorized access."""
        from guardian.responders.guardduty_responder import GuardDutyAutoResponder

        finding = {
            'Id': 'finding-unauth',
            'Type': 'UnauthorizedAccess.EC2/RDPBruteForce',
            'Severity': 6.5,
            'Resource': {
                'InstanceDetails': {
                    'InstanceId': 'i-attacked'
                }
            }
        }

        responder = GuardDutyAutoResponder()
        response = responder.respond(finding)

        assert response['action'] in ['ALERT', 'ISOLATE']
        assert response['severity'] == 'HIGH'

    def test_respond_to_medium_recon_threat(self):
        """✅ Auto-respond to medium reconnaissance."""
        from guardian.responders.guardduty_responder import GuardDutyAutoResponder

        finding = {
            'Id': 'finding-recon',
            'Type': 'Recon.EC2/Portscan',
            'Severity': 4.0,
            'Resource': {
                'InstanceDetails': {
                    'InstanceId': 'i-scanned'
                }
            }
        }

        responder = GuardDutyAutoResponder()
        response = responder.respond(finding)

        assert response['action'] == 'ALERT'
        assert response['severity'] == 'MEDIUM'


class TestResponseOrchestrator:
    """Test response orchestration."""

    def test_orchestrate_multi_action_response(self):
        """✅ Orchestrate multiple response actions."""
        from guardian.responders.guardduty_responder import ResponseOrchestrator

        threat = {
            'type': 'MALWARE',
            'severity': 8.5,
            'resource': 'i-infected',
            'threat_id': 'threat-123'
        }

        orchestrator = ResponseOrchestrator()
        plan = orchestrator.create_response_plan(threat)

        assert len(plan['actions']) > 1
        assert any('isolate' in action.lower() for action in plan['actions'])
        assert any('notify' in action.lower() for action in plan['actions'])

    def test_orchestrate_data_exfiltration_response(self):
        """✅ Orchestrate response to data exfiltration."""
        from guardian.responders.guardduty_responder import ResponseOrchestrator

        threat = {
            'type': 'DATA_EXFILTRATION',
            'severity': 9.0,
            'resource': 'iam-user-attacker',
            'threat_id': 'threat-456'
        }

        orchestrator = ResponseOrchestrator()
        plan = orchestrator.create_response_plan(threat)

        assert len(plan['actions']) >= 3
        assert plan['priority'] == 'CRITICAL'


class TestGuardDutyIntegrationPerformance:
    """Test GuardDuty integration performance."""

    def test_finding_collection_latency(self):
        """✅ Finding collection < 100ms."""
        from guardian.integrations.guardduty_connector import GuardDutyEventCollector
        import time

        finding = {
            'Id': 'finding-perf',
            'Type': 'Recon.EC2/Portscan',
            'Severity': 3.0,
            'Resource': {'InstanceDetails': {'InstanceId': 'i-perf'}}
        }

        collector = GuardDutyEventCollector()
        start = time.time()
        for _ in range(50):
            collector.collect(finding)
        elapsed = (time.time() - start) * 20  # Convert to ms per finding

        assert elapsed < 100

    def test_correlation_latency(self):
        """✅ Correlation analysis < 150ms for 10 signals."""
        from guardian.integrations.guardduty_connector import ThreatCorrelationEngine
        import time

        signals = [
            {'signal_type': 'TYPE_A', 'timestamp': f'2026-05-30T10:{i:02d}:00Z'}
            for i in range(10)
        ]

        engine = ThreatCorrelationEngine()
        start = time.time()
        engine.correlate_signals(signals)
        elapsed = (time.time() - start) * 1000

        assert elapsed < 150
