"""Sprint 48 Phase 1: Threat Correlation Integration Tests (7 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.engines.threat_correlation import ThreatCorrelationEngine


class TestThreatCorrelationIntegration:
    """End-to-end threat correlation scenarios."""

    def test_end_to_end_threat_correlation_flow(self):
        """✅ Complete flow: detect → correlate → assess → recommend remediation."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Step 1: Detect threats
        detected_threats = [
            {
                'threat_id': 'THREAT-E2E-001',
                'threat_signature': 'apt-group-lazarus-tools',
                'threat_type': 'Initial Access',
                'severity': 8,
                'instance_id': 'i-web-server',
                'timestamp': '2026-05-25T10:00:00'
            },
            {
                'threat_id': 'THREAT-E2E-002',
                'threat_signature': 'apt-group-lazarus-tools',
                'threat_type': 'Lateral Movement',
                'severity': 9,
                'instance_id': 'i-database',
                'principal': 'compromised-user',
                'timestamp': '2026-05-25T10:15:00'
            },
            {
                'threat_id': 'THREAT-E2E-003',
                'threat_signature': 'apt-group-lazarus-tools',
                'threat_type': 'Data Exfiltration',
                'severity': 10,
                'bucket_id': 'sensitive-data-bucket',
                'principal': 'compromised-user',
                'timestamp': '2026-05-25T10:30:00'
            }
        ]

        # Step 2: Correlate by signature
        sig_correlation = engine.correlate_by_signature(detected_threats)
        assert sig_correlation['total_signatures'] == 1
        assert sig_correlation['top_signatures'][0]['count'] == 3

        # Step 3: Correlate across resources
        resource_chains = engine.correlate_across_resources(detected_threats)
        assert resource_chains['multi_resource_threats'] >= 2

        # Step 4: Assess blast radius
        main_threat = detected_threats[2]  # Exfiltration
        # Find the chain with the most resources
        main_chain = max(resource_chains['resource_chains'], key=lambda c: c['blast_radius'])
        blast = engine.assess_blast_radius(main_threat, {'resources': main_chain['resources']})

        assert blast['affected_resources'] >= 2
        assert blast['risk_level'] in ['high', 'critical']
        assert len(blast['recommendations']) > 0

    def test_attack_pattern_detection_apt(self):
        """✅ Detect advanced persistent threat patterns and attack progression."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        base_time = datetime.now()
        threats = [
            # Reconnaissance phase
            {
                'threat_id': 'THREAT-APT-RECON-001',
                'threat_signature': 'network-scan-nmap',
                'threat_type': 'Reconnaissance',
                'severity': 3,
                'timestamp': (base_time).isoformat()
            },
            {
                'threat_id': 'THREAT-APT-RECON-002',
                'threat_signature': 'network-scan-nmap',
                'threat_type': 'Reconnaissance',
                'severity': 3,
                'timestamp': (base_time + timedelta(minutes=5)).isoformat()
            },
            # Exploitation phase
            {
                'threat_id': 'THREAT-APT-EXPLOIT-001',
                'threat_signature': 'exploit-cve-2021-44228',
                'threat_type': 'Exploitation',
                'severity': 8,
                'instance_id': 'i-vulnerable',
                'timestamp': (base_time + timedelta(minutes=30)).isoformat()
            },
            # Privilege escalation
            {
                'threat_id': 'THREAT-APT-PRIV-001',
                'threat_signature': 'privesc-kernel-exploit',
                'threat_type': 'Privilege Escalation',
                'severity': 9,
                'principal': 'system',
                'timestamp': (base_time + timedelta(minutes=40)).isoformat()
            },
            # Persistence
            {
                'threat_id': 'THREAT-APT-PERSIST-001',
                'threat_signature': 'apt-persistence-backdoor',
                'threat_type': 'Persistence',
                'severity': 9,
                'bucket_id': 'config-backup',
                'timestamp': (base_time + timedelta(minutes=50)).isoformat()
            }
        ]

        # Timeline analysis detects progression
        timeline = engine.analyze_timeline(threats, time_window_minutes=60)

        # Should detect multiple sequences in the attack progression
        assert len(timeline['event_sequences']) > 0

        # Signature correlation shows toolkit
        sig_correlation = engine.correlate_by_signature(threats)
        assert sig_correlation['total_signatures'] >= 3

    def test_multi_account_threat_correlation(self):
        """✅ Correlate threats across multiple AWS accounts."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Threats from multiple accounts showing same attacker
        threats = []
        for account_id in ['111111111111', '222222222222', '333333333333']:
            for i in range(3):
                threats.append({
                    'threat_id': f'THREAT-ACCOUNT-{account_id}-{i}',
                    'threat_signature': 'supply-chain-compromise-vector',
                    'threat_type': f'Suspicious Activity {i}',
                    'severity': 8 + i,
                    'account_id': account_id,
                    'timestamp': (datetime.now() + timedelta(minutes=i*10)).isoformat()
                })

        # Correlate across accounts
        sig_correlation = engine.correlate_by_signature(threats)

        # Single signature across all accounts
        assert sig_correlation['total_signatures'] == 1
        assert sig_correlation['top_signatures'][0]['count'] == 9

        # Timeline shows coordinated attack
        timeline = engine.analyze_timeline(threats, time_window_minutes=30)
        assert timeline['total_sequences'] > 0

    def test_escalation_pattern_detection(self):
        """✅ Detect escalation patterns (low-severity events leading to critical)."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        base_time = datetime.now()
        escalation_threats = [
            {
                'threat_id': 'THREAT-ESC-001',
                'threat_type': 'Failed Login',
                'severity': 1,
                'timestamp': base_time.isoformat()
            },
            {
                'threat_id': 'THREAT-ESC-002',
                'threat_type': 'Failed Login',
                'severity': 1,
                'timestamp': (base_time + timedelta(seconds=10)).isoformat()
            },
            {
                'threat_id': 'THREAT-ESC-003',
                'threat_type': 'Successful Login - Unusual Location',
                'severity': 4,
                'timestamp': (base_time + timedelta(minutes=1)).isoformat()
            },
            {
                'threat_id': 'THREAT-ESC-004',
                'threat_type': 'Privilege Escalation Attempt',
                'severity': 7,
                'timestamp': (base_time + timedelta(minutes=2)).isoformat()
            },
            {
                'threat_id': 'THREAT-ESC-005',
                'threat_type': 'Admin User Created',
                'severity': 9,
                'principal': 'attacker',
                'timestamp': (base_time + timedelta(minutes=3)).isoformat()
            }
        ]

        # Analyze timeline for escalation
        timeline = engine.analyze_timeline(escalation_threats, time_window_minutes=10)

        # Single sequence showing progression
        assert len(timeline['event_sequences']) == 1
        sequence = timeline['event_sequences'][0]
        assert len(sequence['events']) == 5
        # Severity should increase through the sequence
        severities = [e['severity'] for e in sequence['events']]
        assert severities[-1] > severities[0]

    def test_false_positive_correlation_analysis(self):
        """✅ Identify unrelated events (avoid false positive correlations)."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Mix of related and unrelated threats
        base_time = datetime.now()
        threats = [
            # Real attack chain
            {
                'threat_id': 'THREAT-REAL-001',
                'threat_signature': 'exploit-splunk-app',
                'threat_type': 'Exploitation',
                'severity': 9,
                'instance_id': 'i-splunk-server',
                'timestamp': base_time.isoformat()
            },
            {
                'threat_id': 'THREAT-REAL-002',
                'threat_signature': 'exploit-splunk-app',
                'threat_type': 'Lateral Movement',
                'severity': 8,
                'instance_id': 'i-monitoring-hub',
                'timestamp': (base_time + timedelta(minutes=5)).isoformat()
            },
            # Unrelated events (noise)
            {
                'threat_id': 'THREAT-FALSE-001',
                'threat_signature': 'failed-backup-job',
                'threat_type': 'Configuration Error',
                'severity': 2,
                'timestamp': (base_time + timedelta(hours=1)).isoformat()
            },
            {
                'threat_id': 'THREAT-FALSE-002',
                'threat_signature': 'ssl-cert-expiring',
                'threat_type': 'Certificate Warning',
                'severity': 1,
                'timestamp': (base_time + timedelta(hours=2)).isoformat()
            }
        ]

        # Correlate by signature
        sig_correlation = engine.correlate_by_signature(threats)

        # Should have 3 distinct signatures
        assert sig_correlation['total_signatures'] == 3

        # Real attack should rank higher
        top_sig = sig_correlation['top_signatures'][0]
        assert top_sig['signature'] == 'exploit-splunk-app'
        assert top_sig['count'] == 2

    def test_resource_chain_severity_escalation(self):
        """✅ Resource chain analysis escalates severity when affecting critical systems."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Low severity threat affecting critical database
        threat = {
            'threat_id': 'THREAT-CRIT-001',
            'threat_type': 'Unauthorized Access',
            'severity': 3  # Low severity in isolation
        }

        critical_chain = {
            'resources': [
                {'type': 'ec2', 'id': 'i-database-primary'},
                {'type': 's3', 'id': 'backup-bucket-prod'},
                {'type': 'iam', 'id': 'database-admin'}
            ]
        }

        blast = engine.assess_blast_radius(threat, critical_chain)

        # Should escalate severity based on blast radius
        assert blast['risk_level'] in ['medium', 'high']
        assert blast['affected_resources'] == 3

    def test_correlation_with_temporal_gaps(self):
        """✅ Temporal analysis handles event gaps and distinguishes separate incidents."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        base_time = datetime.now()
        threats = [
            # Incident 1 (5 events in 10 minutes)
            {
                'threat_id': f'THREAT-INC1-{i}',
                'threat_type': 'Type1',
                'severity': 5,
                'timestamp': (base_time + timedelta(minutes=i)).isoformat()
            }
            for i in range(5)
        ] + [
            # Large gap (2 hours)
            # Incident 2 (3 events in 5 minutes)
            {
                'threat_id': f'THREAT-INC2-{i}',
                'threat_type': 'Type2',
                'severity': 6,
                'timestamp': (base_time + timedelta(hours=2, minutes=i)).isoformat()
            }
            for i in range(3)
        ]

        # Analyze timeline with 30-minute window
        timeline = engine.analyze_timeline(threats, time_window_minutes=30)

        # Should detect 2 distinct sequences (separated by gap)
        assert len(timeline['event_sequences']) >= 2

        # Verify sequence separation
        sequences = timeline['event_sequences']
        if len(sequences) >= 2:
            first_seq_end = sequences[0]['events'][-1]['timestamp']
            second_seq_start = sequences[1]['events'][0]['timestamp']
            # Gap should be significant
            assert len(sequences[0]['events']) == 5 or len(sequences[1]['events']) == 3
