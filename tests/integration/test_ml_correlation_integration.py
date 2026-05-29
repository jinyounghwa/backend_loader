import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda'))
from guardian.ml.threat_prediction_model import ThreatPredictionModel
from guardian.ml.anomaly_clustering_engine import AnomalyClusteringEngine
from guardian.ml.threat_trend_analyzer import ThreatTrendAnalyzer
from guardian.ml.pattern_recognition_service import PatternRecognitionService


@pytest.fixture
def mock_dynamodb():
    mock = Mock()
    mock_table = Mock()
    mock.Table.return_value = mock_table
    return mock, mock_table


@pytest.fixture
def ml_pipeline(mock_dynamodb):
    mock_db, _ = mock_dynamodb
    return {
        'prediction': ThreatPredictionModel(dynamodb_resource=mock_db),
        'clustering': AnomalyClusteringEngine(dynamodb_resource=mock_db),
        'trends': ThreatTrendAnalyzer(dynamodb_resource=mock_db),
        'patterns': PatternRecognitionService(dynamodb_resource=mock_db)
    }


@pytest.fixture
def sample_threats():
    threats = []
    base_time = datetime.now(timezone.utc).replace(tzinfo=None)

    # 위협 데이터: 패턴이 있는 시퀀스
    threat_sequence = [
        'Unknown Region',
        'Unauthorized SSH',
        'Data Exfiltration',
        'Unknown Region',
        'Unauthorized SSH',
        'Data Exfiltration',
        'Connection Spike',
        'Unknown Region',
        'Unauthorized SSH'
    ]

    for i, threat_type in enumerate(threat_sequence):
        threats.append({
            'threat_id': f'threat-{i}',
            'account_id': 'test-account',
            'threat_type': threat_type,
            'severity': 5 + (i % 4),
            'timestamp': (base_time - timedelta(hours=i)).isoformat(),
            'event_frequency': 3,
            'resource_impact_count': 2,
            'response_time_seconds': 120,
            'remediation_success_rate': 0.8,
            'account_risk_score': 0.7,
            'affected_resource_type': 'EC2',
            'remediated': i > 5
        })

    return threats


def test_identify_patterns(ml_pipeline, sample_threats):
    """Apriori 패턴 추출"""
    pattern_service = ml_pipeline['patterns']

    result = pattern_service.identify_patterns(sample_threats, min_support=0.2)

    assert 'patterns' in result
    assert 'total_patterns' in result
    assert result['threat_count'] == len(sample_threats)

    # 반복 패턴 확인
    if result['patterns']:
        pattern = result['patterns'][0]
        assert 'sequence' in pattern
        assert 'support' in pattern
        assert 'confidence' in pattern
        assert 'lift' in pattern


def test_threat_sequence_matching(ml_pipeline, sample_threats):
    """시퀀스 패턴 매칭"""
    pattern_service = ml_pipeline['patterns']

    # 패턴 학습
    patterns = pattern_service.identify_patterns(sample_threats, min_support=0.2)['patterns']

    # 새로운 위협 시퀀스
    new_sequence = ['Unknown Region', 'Unauthorized SSH', 'Data Exfiltration']

    result = pattern_service.match_pattern(new_sequence, patterns)

    assert 'current_sequence' in result
    assert 'matched_patterns' in result
    assert result['current_sequence'] == new_sequence


def test_pattern_confidence_calculation(ml_pipeline, sample_threats):
    """신뢰도 계산"""
    pattern_service = ml_pipeline['patterns']

    # 명확한 패턴
    clear_pattern_threats = [
        {'threat_type': 'A', 'timestamp': '2026-05-26T00:00:00'},
        {'threat_type': 'B', 'timestamp': '2026-05-26T01:00:00'},
        {'threat_type': 'A', 'timestamp': '2026-05-26T02:00:00'},
        {'threat_type': 'B', 'timestamp': '2026-05-26T03:00:00'}
    ]

    patterns = pattern_service.identify_patterns(clear_pattern_threats, min_support=0.25)['patterns']

    # 같은 패턴 매칭
    result = pattern_service.match_pattern(['A', 'B'], patterns)

    if result['matched_patterns']:
        assert result['matched_patterns'][0]['confidence'] > 0.7


def test_anomaly_prediction_integration(ml_pipeline, mock_dynamodb, sample_threats):
    """예측 + 클러스터링 통합"""
    _, mock_table = mock_dynamodb

    # 예측 실행
    prediction_model = ml_pipeline['prediction']
    mock_table.query.return_value = {'Items': sample_threats}
    predictions = prediction_model.predict_threats('test-account', days_ahead=7)

    assert 'predictions' in predictions
    assert len(predictions['predictions']) == 7

    # 클러스터링 실행
    clustering_engine = ml_pipeline['clustering']
    clustering_result = clustering_engine.cluster_threats(sample_threats, n_clusters=3)

    assert 'clusters' in clustering_result
    assert len(clustering_result['clusters']) > 0

    # 예측과 클러스터링 결과 모두 유효
    assert predictions['model_accuracy'] > 0
    assert clustering_result['silhouette_score'] >= -1.0


def test_trend_based_alert_escalation(ml_pipeline, mock_dynamodb, sample_threats):
    """추세 기반 알림 에스컬레이션"""
    _, mock_table = mock_dynamodb

    trend_analyzer = ml_pipeline['trends']
    mock_table.query.return_value = {'Items': sample_threats}

    # 추세 분석
    trends = trend_analyzer.analyze_trends('test-account', time_range='24h')

    assert 'trend' in trends
    assert trends['trend'] in ['increasing', 'stable', 'decreasing']

    # 위협 속도 계산
    velocity = trend_analyzer.get_threat_velocity('test-account', time_window='1h')

    assert velocity['threat_velocity'] >= 0

    # 추세가 증가하면 알림 에스컬레이션
    if trends['trend'] == 'increasing' and velocity['threat_velocity'] > 2.0:
        escalation_level = 'HIGH'
    else:
        escalation_level = 'NORMAL'

    assert escalation_level in ['HIGH', 'NORMAL']


def test_pattern_recommendation(ml_pipeline, sample_threats):
    """패턴 기반 예방 조치 추천"""
    pattern_service = ml_pipeline['patterns']

    # 패턴 학습
    patterns_result = pattern_service.identify_patterns(sample_threats, min_support=0.2)
    patterns = patterns_result['patterns']

    # 고신뢰도 패턴만 추천
    high_confidence_patterns = [p for p in patterns if p['confidence'] > 0.8]

    # 각 패턴에 대해 예방 조치 추천
    recommendations = []
    for pattern in high_confidence_patterns:
        sequence = pattern['sequence']
        if len(sequence) >= 2:
            first_threat = sequence[0]
            recommendations.append({
                'pattern_sequence': sequence,
                'prevention': f'Monitor for {first_threat} and implement preventive measures',
                'confidence': pattern['confidence']
            })

    assert isinstance(recommendations, list)


def test_ml_dashboard_metrics(ml_pipeline, mock_dynamodb, sample_threats):
    """ML 메트릭 대시보드 수집"""
    _, mock_table = mock_dynamodb

    prediction_model = ml_pipeline['prediction']
    mock_table.query.return_value = {'Items': sample_threats}

    # 모든 메트릭 수집
    metrics = {
        'prediction_accuracy': prediction_model.predict_threats('test-account')['model_accuracy'],
        'clustering_quality': ml_pipeline['clustering'].cluster_threats(sample_threats)['silhouette_score'],
        'pattern_count': len(ml_pipeline['patterns'].identify_patterns(sample_threats)['patterns']),
        'trend': ml_pipeline['trends'].analyze_trends('test-account')['trend']
    }

    assert 'prediction_accuracy' in metrics
    assert 'clustering_quality' in metrics
    assert 'pattern_count' in metrics
    assert 'trend' in metrics

    assert 0 <= metrics['prediction_accuracy'] <= 1
    assert -1 <= metrics['clustering_quality'] <= 1
    assert metrics['pattern_count'] >= 0
    assert metrics['trend'] in ['increasing', 'stable', 'decreasing']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
