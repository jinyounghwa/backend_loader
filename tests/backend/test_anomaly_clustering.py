import pytest
from unittest.mock import Mock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda'))
from guardian.ml.anomaly_clustering_engine import AnomalyClusteringEngine


@pytest.fixture
def anomaly_clustering_engine():
    mock_db = Mock()
    return AnomalyClusteringEngine(dynamodb_resource=mock_db)


@pytest.fixture
def sample_threats():
    return [
        {
            'threat_id': 'threat-1',
            'threat_type': 'Unknown Region',
            'severity': 8,
            'account_risk_score': 0.8,
            'event_frequency': 5,
            'resource_impact_count': 3,
            'response_time_seconds': 120,
            'remediation_success_rate': 0.7
        },
        {
            'threat_id': 'threat-2',
            'threat_type': 'Unknown Region',
            'severity': 7,
            'account_risk_score': 0.75,
            'event_frequency': 4,
            'resource_impact_count': 2,
            'response_time_seconds': 100,
            'remediation_success_rate': 0.75
        },
        {
            'threat_id': 'threat-3',
            'threat_type': 'Unauthorized SSH',
            'severity': 6,
            'account_risk_score': 0.6,
            'event_frequency': 3,
            'resource_impact_count': 1,
            'response_time_seconds': 80,
            'remediation_success_rate': 0.8
        },
        {
            'threat_id': 'threat-4',
            'threat_type': 'Unauthorized SSH',
            'severity': 5,
            'account_risk_score': 0.5,
            'event_frequency': 2,
            'resource_impact_count': 1,
            'response_time_seconds': 60,
            'remediation_success_rate': 0.85
        },
        {
            'threat_id': 'threat-5',
            'threat_type': 'Public S3',
            'severity': 9,
            'account_risk_score': 0.9,
            'event_frequency': 1,
            'resource_impact_count': 5,
            'response_time_seconds': 30,
            'remediation_success_rate': 0.6
        }
    ]


def test_cluster_threats(anomaly_clustering_engine, sample_threats):
    """K-Means clustering"""
    result = anomaly_clustering_engine.cluster_threats(sample_threats, n_clusters=2)

    assert 'clusters' in result
    assert len(result['clusters']) <= 2
    assert 'silhouette_score' in result

    # 모든 위협이 클러스터에 포함되어 있는지 확인
    threat_ids = set()
    for cluster in result['clusters']:
        threat_ids.update(cluster['threats'])

    assert len(threat_ids) == len(sample_threats)


def test_get_similar_threats(anomaly_clustering_engine, sample_threats):
    """유사 위협 검색"""
    result = anomaly_clustering_engine.get_similar_threats(
        'threat-1',
        sample_threats,
        similarity_threshold=0.7
    )

    assert result['threat_id'] == 'threat-1'
    assert 'similar_threats' in result
    assert all(t['threat_id'] != 'threat-1' for t in result['similar_threats'])
    assert all(t['similarity'] >= 0.7 for t in result['similar_threats'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
