"""Sprint 54 Phase 1: Advanced Threat Correlation Tests (8 tests)"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.engines.threat_correlation_engine import ThreatCorrelationEngine
from guardian.detectors.attack_chain_detector import AttackChainDetector
from guardian.engines.threat_clustering_engine import ThreatClusteringEngine


class TestThreatCorrelation:
    """Sprint 54 Phase 1: Advanced threat correlation and pattern detection."""

    def test_correlate_threats_by_type(self):
        """✅ Correlate threats by type groups threats with severity ranges."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(audit_logger=mock_audit)

        threats = [
            {
                'threat_id': 'T-001',
                'threat_type': 'Lateral Movement',
                'severity': 9,
                'account_id': 'prod'
            },
            {
                'threat_id': 'T-002',
                'threat_type': 'Lateral Movement',
                'severity': 8,
                'account_id': 'prod'
            },
            {
                'threat_id': 'T-003',
                'threat_type': 'Privilege Escalation',
                'severity': 7,
                'account_id': 'dev'
            }
        ]

        groups = engine.correlate_threats_by_type(threats)

        assert len(groups) == 2
        lateral = [g for g in groups if g['threat_type'] == 'Lateral Movement'][0]
        assert lateral['count'] == 2
        assert lateral['max_severity'] == 9
        assert lateral['min_severity'] == 8

    def test_detect_attack_chains(self):
        """✅ Detect attack chains identifies sequential patterns within time window."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(audit_logger=mock_audit)

        base_time = datetime.now(timezone.utc).replace(tzinfo=None)
        threats = [
            {
                'threat_id': 'CHAIN-001',
                'threat_type': 'Reconnaissance',
                'severity': 4,
                'detected_at': base_time.isoformat()
            },
            {
                'threat_id': 'CHAIN-002',
                'threat_type': 'Exploitation',
                'severity': 8,
                'detected_at': (base_time + timedelta(minutes=10)).isoformat()
            },
            {
                'threat_id': 'CHAIN-003',
                'threat_type': 'Privilege Escalation',
                'severity': 9,
                'detected_at': (base_time + timedelta(minutes=25)).isoformat()
            }
        ]

        chains = engine.detect_attack_chains(threats, time_window_minutes=30)

        assert len(chains) >= 1
        assert chains[0]['count'] == 3
        assert chains[0]['span_minutes'] == 30

    def test_cluster_threats(self):
        """✅ Cluster threats groups similar threats by feature vectors."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(audit_logger=mock_audit)

        threats = [
            {
                'threat_id': 'CLUST-001',
                'threat_type': 'Unauthorized Access',
                'severity': 8,
                'account_id': 'acct-1',
                'evidence': ['api_key_exposed', 'failed_auth'],
                'detected_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            },
            {
                'threat_id': 'CLUST-002',
                'threat_type': 'Unauthorized Access',
                'severity': 7,
                'account_id': 'acct-1',
                'evidence': ['api_key_exposed'],
                'detected_at': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)).isoformat()
            },
            {
                'threat_id': 'CLUST-003',
                'threat_type': 'Data Exfiltration',
                'severity': 9,
                'account_id': 'acct-2',
                'evidence': ['s3_access', 'bucket_export'],
                'detected_at': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)).isoformat()
            }
        ]

        clusters = engine.cluster_threats(threats, similarity_threshold=0.7)

        assert len(clusters) >= 1
        assert clusters[0]['count'] >= 1
        assert 'avg_similarity' in clusters[0]

    def test_calculate_threat_similarity(self):
        """✅ Calculate threat similarity returns 0.0-1.0 based on multiple factors."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(audit_logger=mock_audit)

        threat1 = {
            'threat_id': 'T-A',
            'threat_type': 'Lateral Movement',
            'severity': 8,
            'account_id': 'prod',
            'evidence': ['ssh_scan', 'port_probe'],
            'detected_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        threat2 = {
            'threat_id': 'T-B',
            'threat_type': 'Lateral Movement',
            'severity': 7,
            'account_id': 'prod',
            'evidence': ['ssh_scan'],
            'detected_at': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)).isoformat()
        }

        similarity = engine.calculate_threat_similarity(threat1, threat2)

        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Same type, severity, account should be fairly similar

    def test_identify_attack_patterns(self):
        """✅ Identify attack patterns detects MITRE ATT&CK framework patterns."""
        mock_audit = Mock()
        engine = ThreatCorrelationEngine(audit_logger=mock_audit)

        threats = [
            {
                'threat_id': 'PATTERN-001',
                'threat_type': 'Lateral Movement',
                'severity': 8,
                'account_id': 'acct-1',
                'evidence': []
            },
            {
                'threat_id': 'PATTERN-002',
                'threat_type': 'Credential Compromise',
                'severity': 9,
                'account_id': 'acct-2',
                'evidence': []
            }
        ]

        patterns = engine.identify_attack_patterns(threats)

        assert len(patterns) > 0
        assert any('Lateral Movement' in p.get('pattern_name', '') for p in patterns)

    def test_detect_kill_chain(self):
        """✅ Detect kill chain identifies multi-stage attack progression."""
        mock_audit = Mock()
        detector = AttackChainDetector(audit_logger=mock_audit)

        threats = [
            {'threat_id': 'KC-001', 'threat_type': 'Reconnaissance', 'severity': 3},
            {'threat_id': 'KC-002', 'threat_type': 'Vulnerability', 'severity': 5},
            {'threat_id': 'KC-003', 'threat_type': 'Persistence', 'severity': 8},
            {'threat_id': 'KC-004', 'threat_type': 'Privilege Escalation', 'severity': 9}
        ]

        chains = detector.detect_kill_chain(threats, time_window_minutes=120)

        assert len(chains) >= 1
        assert chains[0]['stage_count'] >= 2
        assert len(chains[0]['detected_stages']) >= 2

    def test_cluster_by_similarity(self):
        """✅ Cluster by similarity implements K-means-style grouping."""
        mock_audit = Mock()
        clustering = ThreatClusteringEngine(audit_logger=mock_audit)

        threats = [
            {
                'threat_id': 'SIM-001',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'affected_resources': [{'resource_type': 'ec2'}],
                'evidence': ['suspicious_login'],
                'detected_at': '2026-05-25T10:00:00'
            },
            {
                'threat_id': 'SIM-002',
                'threat_type': 'Unauthorized EC2',
                'severity': 7,
                'affected_resources': [{'resource_type': 'ec2'}],
                'evidence': ['suspicious_login'],
                'detected_at': '2026-05-25T10:05:00'
            },
            {
                'threat_id': 'SIM-003',
                'threat_type': 'Public Bucket',
                'severity': 6,
                'affected_resources': [{'resource_type': 's3'}],
                'evidence': ['public_access'],
                'detected_at': '2026-05-25T10:10:00'
            }
        ]

        clusters = clustering.cluster_by_similarity(threats, threshold=0.7)

        assert len(clusters) >= 1
        assert clusters[0]['cluster_size'] >= 1
        assert 'centroid' in clusters[0]
        assert 'silhouette_score' in clusters[0]

    def test_estimate_compromise_probability(self):
        """✅ Estimate compromise probability returns 0.0-0.95 based on kill chain."""
        mock_audit = Mock()
        detector = AttackChainDetector(audit_logger=mock_audit)

        chain = {
            'stage_count': 4,
            'max_stage_index': 3,
            'total_threats_in_chain': 8
        }

        probability = detector.estimate_compromise_probability(chain)

        assert 0.0 <= probability <= 0.95
        assert probability > 0.5  # Multiple stages should increase probability
