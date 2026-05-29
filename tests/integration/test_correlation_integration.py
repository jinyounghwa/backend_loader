"""Sprint 54 Phase 1: Integration Tests for Threat Correlation (7 tests)"""

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


class TestCorrelationIntegration:
    """Integration tests for end-to-end threat correlation workflows."""

    def test_end_to_end_threat_grouping_and_clustering(self):
        """✅ Full workflow: ingest threats → group by type → cluster by similarity."""
        engine = ThreatCorrelationEngine()
        clustering = ThreatClusteringEngine()

        threats = [
            {
                'threat_id': 'E2E-001',
                'threat_type': 'Unauthorized Access',
                'severity': 8,
                'account_id': 'prod',
                'evidence': ['ssh_auth_failure'],
                'detected_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            },
            {
                'threat_id': 'E2E-002',
                'threat_type': 'Unauthorized Access',
                'severity': 7,
                'account_id': 'prod',
                'evidence': ['ssh_auth_failure'],
                'detected_at': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)).isoformat()
            },
            {
                'threat_id': 'E2E-003',
                'threat_type': 'Data Exfiltration',
                'severity': 9,
                'account_id': 'prod',
                'evidence': ['s3_export'],
                'detected_at': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)).isoformat()
            }
        ]

        # Step 1: Group by type
        groups = engine.correlate_threats_by_type(threats)
        assert len(groups) == 2

        # Step 2: Cluster similar threats
        clusters = clustering.cluster_by_similarity(threats, threshold=0.7)
        assert len(clusters) >= 1

        # Step 3: Verify clustering captures similarity
        auth_cluster = [c for c in clusters if c['cluster_size'] >= 2]
        assert len(auth_cluster) > 0

    def test_kill_chain_progression_detection(self):
        """✅ Detect multi-stage attack: recon → exploit → privilege esc → lateral move."""
        engine = ThreatCorrelationEngine()
        detector = AttackChainDetector()

        base_time = datetime.now(timezone.utc).replace(tzinfo=None)
        threats = [
            {
                'threat_id': 'STAGE-001',
                'threat_type': 'Reconnaissance',
                'severity': 3,
                'detected_at': base_time.isoformat()
            },
            {
                'threat_id': 'STAGE-002',
                'threat_type': 'Unauthorized Access',
                'severity': 6,
                'detected_at': (base_time + timedelta(minutes=15)).isoformat()
            },
            {
                'threat_id': 'STAGE-003',
                'threat_type': 'Privilege Escalation',
                'severity': 8,
                'detected_at': (base_time + timedelta(minutes=30)).isoformat()
            },
            {
                'threat_id': 'STAGE-004',
                'threat_type': 'Lateral Movement',
                'severity': 9,
                'detected_at': (base_time + timedelta(minutes=45)).isoformat()
            }
        ]

        # Detect kill chain
        chains = detector.detect_kill_chain(threats, time_window_minutes=60)
        assert len(chains) >= 1

        # Calculate progression
        progression = detector.calculate_kill_chain_progression(threats)
        assert progression['stage_count'] >= 3
        assert 'exploitation' in progression['stages_completed']
        assert progression['progression_percentage'] >= 50

    def test_mitre_attack_pattern_correlation(self):
        """✅ Correlate threats to MITRE ATT&CK framework patterns."""
        engine = ThreatCorrelationEngine()

        threats = [
            {
                'threat_id': 'MITRE-001',
                'threat_type': 'Lateral Movement',
                'severity': 8,
                'account_id': 'prod',
                'evidence': []
            },
            {
                'threat_id': 'MITRE-002',
                'threat_type': 'Credential Compromise',
                'severity': 9,
                'account_id': 'dev',
                'evidence': []
            },
            {
                'threat_id': 'MITRE-003',
                'threat_type': 'Public Bucket',
                'severity': 7,
                'account_id': 'prod',
                'evidence': []
            }
        ]

        patterns = engine.identify_attack_patterns(threats)

        assert len(patterns) > 0
        assert any(p.get('framework') == 'MITRE ATT&CK' for p in patterns)
        assert any('Lateral Movement' in p.get('pattern_name', '') or
                   'Data Exfiltration' in p.get('pattern_name', '')
                   for p in patterns)

    def test_multi_account_threat_correlation(self):
        """✅ Correlate threats across multiple AWS accounts."""
        engine = ThreatCorrelationEngine()
        detector = AttackChainDetector()

        threats = [
            {
                'threat_id': 'MULTI-ACCT-001',
                'threat_type': 'Lateral Movement',
                'severity': 9,
                'account_id': 'prod-acct-001',
                'detected_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            },
            {
                'threat_id': 'MULTI-ACCT-002',
                'threat_type': 'Cross-Account Access',
                'severity': 8,
                'account_id': 'dev-acct-002',
                'detected_at': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)).isoformat()
            },
            {
                'threat_id': 'MULTI-ACCT-003',
                'threat_type': 'Data Exfiltration',
                'severity': 9,
                'account_id': 'prod-acct-001',
                'detected_at': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)).isoformat()
            }
        ]

        # Group by type across accounts
        groups = engine.correlate_threats_by_type(threats)
        assert any(g['threat_type'] == 'Lateral Movement' for g in groups)

        # Detect cross-account chains
        lateral_threats = [t for t in threats if 'Lateral Movement' in t['threat_type']]
        multi_account = detector.identify_lateral_movement(lateral_threats, ['prod-acct-001', 'dev-acct-002'])
        assert len(multi_account) > 0

    def test_threat_similarity_clustering_workflow(self):
        """✅ Complete workflow: extract features → calculate distances → form clusters."""
        clustering = ThreatClusteringEngine()

        threats = [
            {
                'threat_id': 'FEAT-001',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'account_id': 'prod',
                'affected_resources': [{'resource_type': 'ec2'}],
                'evidence': ['suspicious_login'],
                'detected_at': '2026-05-25T10:00:00'
            },
            {
                'threat_id': 'FEAT-002',
                'threat_type': 'Unauthorized EC2',
                'severity': 8,
                'account_id': 'prod',
                'affected_resources': [{'resource_type': 'ec2'}],
                'evidence': ['suspicious_login'],
                'detected_at': '2026-05-25T10:05:00'
            }
        ]

        # Extract features
        features = [clustering.extract_threat_features(t) for t in threats]
        assert len(features) == 2
        assert 'threat_type' in features[0]
        assert 'severity_level' in features[0]

        # Calculate distance
        distance = clustering.calculate_feature_distance(features[0], features[1])
        assert 0.0 <= distance <= 1.0
        assert distance < 0.3  # Same type/severity should be very close

        # Cluster
        clusters = clustering.cluster_by_similarity(threats, threshold=0.7)
        assert len(clusters) >= 1
        assert clusters[0]['cluster_size'] >= 2

    def test_compromise_probability_escalation_path(self):
        """✅ Calculate compromise probability increases with kill chain progression."""
        detector = AttackChainDetector()

        # Early stage chain
        early_chain = {
            'stage_count': 1,
            'max_stage_index': 0,
            'total_threats_in_chain': 1
        }

        # Advanced chain
        advanced_chain = {
            'stage_count': 5,
            'max_stage_index': 4,
            'total_threats_in_chain': 10
        }

        early_prob = detector.estimate_compromise_probability(early_chain)
        advanced_prob = detector.estimate_compromise_probability(advanced_chain)

        assert early_prob < advanced_prob
        assert 0.0 <= early_prob <= 0.95
        assert 0.0 <= advanced_prob <= 0.95
        assert advanced_prob > 0.7  # Advanced stages should be high risk

    def test_cluster_statistics_and_quality_metrics(self):
        """✅ Generate cluster statistics and silhouette scores for cluster quality."""
        clustering = ThreatClusteringEngine()

        threats = [
            {
                'threat_id': f'STATS-{i:03d}',
                'threat_type': 'Unauthorized EC2',
                'severity': 7 + (i % 3),
                'account_id': 'prod',
                'affected_resources': [{'resource_type': 'ec2'}],
                'evidence': ['suspicious_login'],
                'detected_at': (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=i)).isoformat()
            }
            for i in range(5)
        ]

        clusters = clustering.cluster_by_similarity(threats, threshold=0.6)
        clustering.clusters = clusters

        stats = clustering.get_cluster_statistics()

        assert stats['total_clusters'] >= 1
        assert stats['total_threats'] == 5
        assert stats['avg_cluster_size'] > 0
        assert stats['max_cluster_size'] >= stats['min_cluster_size']
        assert len(stats['cluster_details']) >= 1
