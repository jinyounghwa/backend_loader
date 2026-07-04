import pytest
from datetime import datetime, timedelta, timezone
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from guardian.ml.threat_prediction_model import ThreatPredictionModel


@pytest.fixture
def mock_dynamodb():
    mock = Mock()
    mock_table = Mock()
    mock.Table.return_value = mock_table
    return mock, mock_table


@pytest.fixture
def threat_prediction_model(mock_dynamodb):
    mock_db, _ = mock_dynamodb
    return ThreatPredictionModel(dynamodb_resource=mock_db)


def test_predict_threats_with_sufficient_data(threat_prediction_model, mock_dynamodb):
    """기본 예측 (충분한 데이터)"""
    _, mock_table = mock_dynamodb

    # 30일 치 위협 데이터 생성
    historical_threats = []
    for i in range(30):
        date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=i)).isoformat()
        for j in range(2 + i % 5):  # 일일 2-6개 위협
            historical_threats.append({
                'threat_id': f'threat-{i}-{j}',
                'account_id': 'test-account',
                'threat_type': 'Unknown Region',
                'severity': 5 + (i % 3),
                'timestamp': date,
                'event_frequency': 3,
                'resource_impact_count': 1,
                'response_time_seconds': 60,
                'remediation_success_rate': 0.8
            })

    mock_table.query.return_value = {'Items': historical_threats}

    result = threat_prediction_model.predict_threats('test-account', days_ahead=7)

    assert 'predictions' in result
    assert len(result['predictions']) == 7
    assert 'trend' in result
    assert 'anomaly_score' in result
    assert 'model_accuracy' in result
    assert 0 <= result['anomaly_score'] <= 1
    assert 0 <= result['model_accuracy'] <= 1


def test_train_model(threat_prediction_model, mock_dynamodb):
    """모델 재학습"""
    _, mock_table = mock_dynamodb

    historical_threats = []
    for i in range(20):
        date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=i)).isoformat()
        historical_threats.append({
            'threat_id': f'threat-{i}',
            'account_id': 'test-account',
            'threat_type': 'Unknown Region',
            'severity': 5,
            'timestamp': date,
            'event_frequency': 2,
            'resource_impact_count': 1,
            'response_time_seconds': 60,
            'remediation_success_rate': 0.8
        })

    mock_table.query.return_value = {'Items': historical_threats}

    result = threat_prediction_model.train_model('test-account', lookback_days=30)

    assert 'status' in result
    assert result['account_id'] == 'test-account'


def test_predict_with_seasonality(threat_prediction_model, mock_dynamodb):
    """계절성 포함 예측"""
    _, mock_table = mock_dynamodb

    # 계절성 패턴을 가진 데이터 (일주일 주기)
    historical_threats = []
    for day in range(30):
        date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=day)).isoformat()
        day_of_week = day % 7
        threat_count = 5 if day_of_week < 5 else 2  # 평일 많음, 주말 적음

        for i in range(threat_count):
            historical_threats.append({
                'threat_id': f'threat-{day}-{i}',
                'account_id': 'test-account',
                'threat_type': 'Connection Spike',
                'severity': 4,
                'timestamp': date,
                'event_frequency': 3,
                'resource_impact_count': 2,
                'response_time_seconds': 45,
                'remediation_success_rate': 0.85
            })

    mock_table.query.return_value = {'Items': historical_threats}

    result = threat_prediction_model.predict_threats('test-account', days_ahead=7)

    assert 'predictions' in result
    assert len(result['predictions']) == 7
    # 신뢰도 간격 확인
    for pred in result['predictions']:
        assert pred['lower_bound'] <= pred['expected_threats'] <= pred['upper_bound']


def test_prediction_confidence_score(threat_prediction_model):
    """신뢰도 점수 계산"""
    # 모델이 학습되지 않은 상태
    confidence = threat_prediction_model.get_prediction_confidence('test-account')
    assert confidence == 0.0

    # 모델 학습 후 신뢰도 증가
    threat_prediction_model.models['test-account'] = {
        'model': Mock(),
        'trained_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        'data_points': 30
    }
    confidence = threat_prediction_model.get_prediction_confidence('test-account')
    assert confidence >= 0.9  # 30 / 30 ≈ 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
