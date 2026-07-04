import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Set AWS region for boto3
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
@pytest.fixture
def ml_handler():
    with patch('guardian.handlers.ml_handler.boto3.resource') as mock_resource:
        mock_dynamodb = MagicMock()
        mock_resource.return_value = mock_dynamodb

        from guardian.handlers.ml_handler import MLHandler
        handler = MLHandler()

        # Replace services with mocks
        handler.prediction_model = Mock()
        handler.clustering_engine = Mock()
        handler.trend_analyzer = Mock()
        handler.pattern_service = Mock()

        return handler


@pytest.fixture
def sample_event_predict():
    return {
        'body': json.dumps({
            'account_id': 'test-account',
            'days_ahead': 7
        })
    }


@pytest.fixture
def sample_event_cluster():
    return {
        'body': json.dumps({
            'threats': [
                {
                    'threat_id': 'threat-1',
                    'severity': 8,
                    'account_risk_score': 0.8,
                    'event_frequency': 5,
                    'resource_impact_count': 3,
                    'response_time_seconds': 120,
                    'remediation_success_rate': 0.7
                },
                {
                    'threat_id': 'threat-2',
                    'severity': 7,
                    'account_risk_score': 0.75,
                    'event_frequency': 4,
                    'resource_impact_count': 2,
                    'response_time_seconds': 100,
                    'remediation_success_rate': 0.75
                }
            ],
            'n_clusters': 2
        })
    }


@pytest.fixture
def sample_event_trends():
    return {
        'queryStringParameters': {
            'account_id': 'test-account',
            'time_range': '24h'
        }
    }


@pytest.fixture
def sample_event_patterns():
    return {
        'body': json.dumps({
            'threats': [
                {'threat_type': 'Unknown Region', 'timestamp': '2026-05-26T00:00:00'},
                {'threat_type': 'Unauthorized SSH', 'timestamp': '2026-05-26T01:00:00'},
                {'threat_type': 'Data Exfil', 'timestamp': '2026-05-26T02:00:00'},
                {'threat_type': 'Unknown Region', 'timestamp': '2026-05-26T03:00:00'},
                {'threat_type': 'Unauthorized SSH', 'timestamp': '2026-05-26T04:00:00'}
            ],
            'min_support': 0.3
        })
    }


def test_handle_predict_threats(ml_handler, sample_event_predict):
    """위협 예측 핸들러"""
    with patch.object(ml_handler.prediction_model, 'predict_threats') as mock_predict:
        mock_predict.return_value = {
            'predictions': [
                {'date': '2026-05-27', 'expected_threats': 2.5, 'confidence': 0.95},
                {'date': '2026-05-28', 'expected_threats': 2.3, 'confidence': 0.93}
            ],
            'trend': 'stable',
            'anomaly_score': 0.5,
            'model_accuracy': 0.85
        }

        response = ml_handler.handle_predict_threats(sample_event_predict)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'predictions' in body
        assert body['trend'] == 'stable'
        assert body['model_accuracy'] == 0.85


def test_handle_cluster_threats(ml_handler, sample_event_cluster):
    """위협 클러스터링 핸들러"""
    with patch.object(ml_handler.clustering_engine, 'cluster_threats') as mock_cluster:
        mock_cluster.return_value = {
            'clusters': [
                {
                    'id': 'cluster-1',
                    'threats': ['threat-1'],
                    'threat_count': 1,
                    'cohesion': 0.95,
                    'avg_severity': 8.0
                }
            ],
            'silhouette_score': 0.8,
            'threat_count': 2
        }

        response = ml_handler.handle_cluster_threats(sample_event_cluster)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'clusters' in body
        assert body['silhouette_score'] == 0.8
        assert body['cluster_count'] == 1


def test_handle_analyze_trends(ml_handler, sample_event_trends):
    """추세 분석 핸들러"""
    with patch.object(ml_handler.trend_analyzer, 'analyze_trends') as mock_trends:
        mock_trends.return_value = {
            'hourly_breakdown': [
                {'hour': '2026-05-26T00', 'threats': 5, 'avg_severity': 6.2},
                {'hour': '2026-05-26T01', 'threats': 3, 'avg_severity': 5.8}
            ],
            'daily_breakdown': [],
            'peak_hours': ['2026-05-26T00'],
            'safe_hours': ['2026-05-26T02'],
            'anomaly_hours': [],
            'trend': 'stable'
        }

        response = ml_handler.handle_analyze_trends(sample_event_trends)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'hourly_breakdown' in body
        assert body['trend'] == 'stable'


def test_handle_get_threat_velocity(ml_handler):
    """위협 속도 계산 핸들러"""
    event = {
        'queryStringParameters': {
            'account_id': 'test-account',
            'time_window': '1h'
        }
    }

    with patch.object(ml_handler.trend_analyzer, 'get_threat_velocity') as mock_velocity:
        mock_velocity.return_value = {
            'threat_velocity': 2.5,
            'threats_per_hour': 2.5,
            'total_threats': 5,
            'trend': 'increasing'
        }

        response = ml_handler.handle_get_threat_velocity(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['threat_velocity'] == 2.5
        assert body['trend'] == 'increasing'


def test_handle_identify_patterns(ml_handler, sample_event_patterns):
    """패턴 발견 핸들러"""
    with patch.object(ml_handler.pattern_service, 'identify_patterns') as mock_patterns:
        mock_patterns.return_value = {
            'patterns': [
                {
                    'id': 'pattern-1',
                    'sequence': ['Unknown Region', 'Unauthorized SSH'],
                    'support': 0.4,
                    'confidence': 0.8,
                    'lift': 2.0,
                    'occurrences': 2
                }
            ],
            'total_patterns': 1,
            'threat_count': 5
        }

        response = ml_handler.handle_identify_patterns(sample_event_patterns)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'patterns' in body
        assert body['total_patterns'] == 1


def test_handle_match_pattern(ml_handler):
    """패턴 매칭 핸들러"""
    event = {
        'body': json.dumps({
            'threat_sequence': ['Unknown Region', 'Unauthorized SSH'],
            'patterns': [
                {
                    'id': 'pattern-1',
                    'sequence': ['Unknown Region', 'Unauthorized SSH'],
                    'confidence': 0.85
                }
            ]
        })
    }

    with patch.object(ml_handler.pattern_service, 'match_pattern') as mock_match:
        mock_match.return_value = {
            'current_sequence': ['Unknown Region', 'Unauthorized SSH'],
            'matched_patterns': [
                {
                    'pattern_id': 'pattern-1',
                    'pattern_sequence': ['Unknown Region', 'Unauthorized SSH'],
                    'confidence': 0.85,
                    'match_position': 0
                }
            ],
            'pattern_count': 1
        }

        response = ml_handler.handle_match_pattern(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['pattern_count'] == 1


def test_handle_get_similar_threats(ml_handler):
    """유사 위협 검색 핸들러"""
    event = {
        'body': json.dumps({
            'threat_id': 'threat-1',
            'all_threats': [
                {'threat_id': 'threat-1', 'severity': 8},
                {'threat_id': 'threat-2', 'severity': 7}
            ],
            'similarity_threshold': 0.7
        })
    }

    with patch.object(ml_handler.clustering_engine, 'get_similar_threats') as mock_similar:
        mock_similar.return_value = {
            'threat_id': 'threat-1',
            'similar_threats': [
                {'threat_id': 'threat-2', 'similarity': 0.85}
            ],
            'count': 1
        }

        response = ml_handler.handle_get_similar_threats(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 1


def test_handle_train_model(ml_handler):
    """모델 재학습 핸들러"""
    event = {
        'body': json.dumps({
            'account_id': 'test-account',
            'lookback_days': 30
        })
    }

    with patch.object(ml_handler.prediction_model, 'train_model') as mock_train:
        mock_train.return_value = {
            'status': 'trained',
            'account_id': 'test-account',
            'trained_at': '2026-05-26T00:00:00',
            'data_points': 30
        }

        response = ml_handler.handle_train_model(event)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'trained'
        assert body['data_points'] == 30


def test_error_handling_missing_required_field(ml_handler):
    """필수 필드 누락 에러 처리"""
    event = {'body': json.dumps({})}

    response = ml_handler.handle_predict_threats(event)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
