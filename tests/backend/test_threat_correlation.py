"""Sprint 48 Phase 1: Threat Correlation Tests (8 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.engines.threat_correlation import ThreatCorrelationEngine


class TestThreatCorrelation:
    """Advanced threat correlation across resources."""

    def test_correlate_threats_by_signature(self):
        """✅ Correlate threats by signature detects same attacker/tools."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        threats = [
            {
                'threat_id': 'THREAT-SIG-001',
                'threat_signature': 'malware-trojan-v2.3',
                'severity': 9,
                'timestamp': '2026-05-25T10:00:00'
            },
            {
                'threat_id': 'THREAT-SIG-002',
                'threat_signature': 'malware-trojan-v2.3',
                'severity': 9,
                'timestamp': '2026-05-25T11:00:00'
            },
            {
                'threat_id': 'THREAT-SIG-003',
                'threat_signature': 'brute-force-ssh',
                'severity': 7,
                'timestamp': '2026-05-25T12:00:00'
            },
            {
                'threat_id': 'THREAT-SIG-004',
                'threat_signature': 'brute-force-ssh',
                'severity': 7,
                'timestamp': '2026-05-25T13:00:00'
            },
            {
                'threat_id': 'THREAT-SIG-005',
                'threat_signature': 'brute-force-ssh',
                'severity': 7,
                'timestamp': '2026-05-25T14:00:00'
            }
        ]

        # Correlate by signature
        correlation = engine.correlate_by_signature(threats)

        assert correlation['total_signatures'] == 2
        assert len(correlation['top_signatures']) == 2

        # Brute force should be #1 (3 threats - highest count)
        assert correlation['top_signatures'][0]['signature'] == 'brute-force-ssh'
        assert correlation['top_signatures'][0]['count'] == 3
        assert correlation['top_signatures'][0]['threat_count'] == 3

        # Malware trojan should be #2 (2 threats)
        assert correlation['top_signatures'][1]['signature'] == 'malware-trojan-v2.3'
        assert correlation['top_signatures'][1]['count'] == 2

        # Verify signature groups details
        trojan_group = correlation['signature_groups']['malware-trojan-v2.3']
        assert trojan_group['count'] == 2
        assert len(trojan_group['threats']) == 2
        assert trojan_group['severity_range']['min'] == 9
        assert trojan_group['severity_range']['max'] == 9

    def test_correlate_across_resources(self):
        """✅ Correlate threats across EC2 → S3 → IAM chains."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        threats = [
            {
                'threat_id': 'THREAT-CHAIN-001',
                'threat_type': 'Lateral Movement',
                'severity': 9,
                'instance_id': 'i-infected',
                'bucket_id': 's3://data-bucket',
                'principal': 'attacker-user'
            },
            {
                'threat_id': 'THREAT-CHAIN-002',
                'threat_type': 'Privilege Escalation',
                'severity': 8,
                'instance_id': 'i-infected',
                'principal': 'attacker-user'
            },
            {
                'threat_id': 'THREAT-CHAIN-003',
                'threat_type': 'Data Exfiltration',
                'severity': 8,
                'bucket_id': 's3://data-bucket',
                'principal': 'attacker-user'
            },
            {
                'threat_id': 'THREAT-CHAIN-004',
                'threat_type': 'Network Isolation Issue',
                'severity': 5,
                'instance_id': 'i-test',
                'vpc_id': 'vpc-prod'
            }
        ]

        # Correlate across resources
        chains = engine.correlate_across_resources(threats)

        assert chains['total_chains'] >= 2
        assert chains['multi_resource_threats'] >= 3  # Threats spanning multiple resources

        # Find the main attack chain (EC2 → S3 → IAM)
        main_chain = None
        for chain in chains['resource_chains']:
            if chain['blast_radius'] >= 3:
                main_chain = chain
                break

        assert main_chain is not None
        assert main_chain['threat_count'] == 1
        assert main_chain['severity'] == 9

    def test_correlate_timeline_analysis(self):
        """✅ Analyze timeline detects sequences and burst patterns."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Create threats in sequence with some bursts
        base_time = datetime.now()
        threats = []

        # Burst 1: 6 threats in 10 minutes
        for i in range(6):
            threats.append({
                'threat_id': f'THREAT-BURST-001-{i}',
                'threat_type': 'Brute Force',
                'severity': 5,
                'timestamp': (base_time + timedelta(minutes=i)).isoformat()
            })

        # Gap: 70 minutes (ensures separate hour windows for burst detection)

        # Burst 2: 7 threats in 15 minutes
        for i in range(7):
            threats.append({
                'threat_id': f'THREAT-BURST-002-{i}',
                'threat_type': 'Dictionary Attack',
                'severity': 6,
                'timestamp': (base_time + timedelta(minutes=80+i)).isoformat()
            })

        # Analyze timeline
        timeline = engine.analyze_timeline(threats, time_window_minutes=15)

        assert len(timeline['event_sequences']) > 0
        assert len(timeline['suspicious_bursts']) > 0

        # Bursts should have at least 2 detected (6 in 10 min, 7 in 15 min)
        assert timeline['total_bursts'] >= 2

        # Verify burst details
        for burst in timeline['suspicious_bursts']:
            assert burst['threat_count'] >= 5
            assert burst['intensity'] > 0

    def test_assess_blast_radius(self):
        """✅ Assess blast radius determines affected resources and risk level."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Threat with multi-resource impact
        critical_threat = {
            'threat_id': 'THREAT-RADIUS-001',
            'threat_type': 'Advanced Persistent Threat',
            'severity': 10
        }

        # Multiple affected resources
        resource_chain = {
            'resources': [
                {'type': 'ec2', 'id': 'i-compromised-1'},
                {'type': 'ec2', 'id': 'i-compromised-2'},
                {'type': 's3', 'id': 'bucket-data'},
                {'type': 'iam', 'id': 'admin-user'},
                {'type': 'network', 'id': 'vpc-prod'}
            ]
        }

        # Assess blast radius
        radius = engine.assess_blast_radius(critical_threat, resource_chain)

        assert radius['affected_resources'] == 5
        assert len(radius['affected_services']) == 4  # ec2, s3, iam, network
        assert radius['blast_radius_score'] >= 8.0
        assert radius['risk_level'] == 'critical'
        assert 'Critical' in radius['estimated_impact']
        assert len(radius['recommendations']) > 0

    def test_blast_radius_medium_impact(self):
        """✅ Blast radius correctly classifies medium-impact threats."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        medium_threat = {
            'threat_id': 'THREAT-RADIUS-002',
            'threat_type': 'Policy Violation',
            'severity': 5
        }

        resource_chain = {
            'resources': [
                {'type': 's3', 'id': 'bucket-public'}
            ]
        }

        radius = engine.assess_blast_radius(medium_threat, resource_chain)

        assert radius['affected_resources'] == 1
        assert radius['blast_radius_score'] <= 4.0
        assert radius['risk_level'] == 'low'

    def test_signature_correlation_identifies_patterns(self):
        """✅ Signature correlation identifies attacker tools and methods."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Multiple threats from same attacker using consistent tools
        threats = [
            {
                'threat_id': f'THREAT-PATTERN-{i}',
                'threat_signature': 'exploit-log4j-rce-variant-3',
                'severity': 9,
                'timestamp': (datetime.now() + timedelta(hours=i)).isoformat()
            }
            for i in range(5)
        ]

        correlation = engine.correlate_by_signature(threats)

        assert correlation['total_signatures'] == 1
        assert correlation['top_signatures'][0]['count'] == 5
        assert 'exploit-log4j-rce' in correlation['top_signatures'][0]['signature']

    def test_timeline_sequence_correlation_score(self):
        """✅ Timeline analysis calculates correlation scores for related events."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Related threats in quick succession
        base_time = datetime.now()
        threats = [
            {
                'threat_id': 'THREAT-SEQ-001',
                'threat_type': 'Reconnaissance',
                'severity': 4,
                'timestamp': base_time.isoformat()
            },
            {
                'threat_id': 'THREAT-SEQ-002',
                'threat_type': 'Exploitation',
                'severity': 8,
                'timestamp': (base_time + timedelta(seconds=30)).isoformat()
            },
            {
                'threat_id': 'THREAT-SEQ-003',
                'threat_type': 'Privilege Escalation',
                'severity': 9,
                'timestamp': (base_time + timedelta(minutes=2)).isoformat()
            }
        ]

        timeline = engine.analyze_timeline(threats, time_window_minutes=10)

        # Should detect 1 sequence (all within 10 minute window)
        assert len(timeline['event_sequences']) == 1

        # Correlation score should be > 0
        sequence = timeline['event_sequences'][0]
        assert sequence['correlation_score'] > 0
        assert len(sequence['events']) == 3
        assert sequence['time_span_seconds'] <= 600  # 10 minutes

    def test_resource_chain_isolation_recommendation(self):
        """✅ Multi-resource threat chains recommend isolation strategy."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(mock_audit)

        # Threat spanning production systems
        threat = {
            'threat_id': 'THREAT-ISO-001',
            'threat_type': 'Ransomware',
            'severity': 10
        }

        resource_chain = {
            'resources': [
                {'type': 'ec2', 'id': 'i-db-server'},
                {'type': 'ec2', 'id': 'i-app-server'},
                {'type': 's3', 'id': 'bucket-backups'},
                {'type': 'iam', 'id': 'admin-role'},
                {'type': 'network', 'id': 'vpc-prod'}
            ]
        }

        radius = engine.assess_blast_radius(threat, resource_chain)

        # Should recommend isolation
        assert any('isolate' in rec.lower() for rec in radius['recommendations'])
        assert any('iam' in rec.lower() or 's3' in rec.lower() or 'ec2' in rec.lower()
                   for rec in radius['recommendations'])
