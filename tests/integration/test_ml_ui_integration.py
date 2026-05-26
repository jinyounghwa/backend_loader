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

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda'))


class MockResponse:
    """Mock response object for testing"""
    def __init__(self, status_code=200, body=None):
        self.statusCode = status_code
        self.body = json.dumps(body) if body else '{}'


@pytest.fixture
def ml_handler():
    """Create ML handler with mocked services"""
    with patch('guardian.handlers.ml_handler.boto3.resource') as mock_resource:
        mock_dynamodb = MagicMock()
        mock_resource.return_value = mock_dynamodb

        from guardian.handlers.ml_handler import MLHandler
        handler = MLHandler()

        # Mock all ML services
        handler.prediction_model = Mock()
        handler.clustering_engine = Mock()
        handler.trend_analyzer = Mock()
        handler.pattern_service = Mock()

        return handler


def test_prediction_to_dashboard_flow(ml_handler):
    """
    Integration test: Prediction → Dashboard display
    Simulates user clicking "Predict" button in ThreatPredictionPanel
    """
    # Mock prediction model response
    ml_handler.prediction_model.predict_threats.return_value = {
        'predictions': [
            {'date': '2026-05-27', 'expected_threats': 2.5, 'confidence': 0.95},
            {'date': '2026-05-28', 'expected_threats': 2.3, 'confidence': 0.93}
        ],
        'trend': 'stable',
        'anomaly_score': 0.5,
        'model_accuracy': 0.85
    }

    # Simulate API call
    event = {
        'body': json.dumps({
            'account_id': 'test-account',
            'days_ahead': 7
        })
    }

    response = ml_handler.handle_predict_threats(event)

    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'predictions' in body
    assert len(body['predictions']) == 2
    assert body['model_accuracy'] == 0.85
    assert body['trend'] == 'stable'


def test_clustering_to_dashboard_flow(ml_handler):
    """
    Integration test: Clustering → Dashboard display
    Simulates user submitting threats to AnomalyClusterPanel
    """
    # Mock clustering response
    ml_handler.clustering_engine.cluster_threats.return_value = {
        'clusters': [
            {
                'id': 'C1',
                'threats': ['t1'],
                'threat_count': 1,
                'cohesion': 0.95,
                'avg_severity': 8.0
            }
        ],
        'silhouette_score': 0.8,
        'threat_count': 1
    }

    # Simulate API call
    event = {
        'body': json.dumps({
            'threats': [
                {
                    'threat_id': 't1',
                    'severity': 8,
                    'account_risk_score': 0.8,
                    'event_frequency': 5,
                    'resource_impact_count': 3,
                    'response_time_seconds': 120,
                    'remediation_success_rate': 0.7
                }
            ],
            'n_clusters': 1
        })
    }

    response = ml_handler.handle_cluster_threats(event)

    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'clusters' in body
    assert body['cluster_count'] == 1
    assert body['silhouette_score'] == 0.8


def test_trends_to_chart_flow(ml_handler):
    """
    Integration test: Trends → Chart visualization
    Simulates ThreatTrendChart fetching and rendering data
    """
    # Mock trend analyzer response
    ml_handler.trend_analyzer.analyze_trends.return_value = {
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

    # Simulate API call (GET request)
    event = {
        'queryStringParameters': {
            'account_id': 'test-account',
            'time_range': '24h'
        }
    }

    response = ml_handler.handle_analyze_trends(event)

    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'hourly_breakdown' in body
    assert len(body['hourly_breakdown']) == 2
    assert '2026-05-26T00' in body['peak_hours']


def test_patterns_to_dashboard_flow(ml_handler):
    """
    Integration test: Pattern Recognition → Dashboard display
    Simulates PatternRecognitionPanel analyzing threat sequences
    """
    # Mock pattern service response
    ml_handler.pattern_service.identify_patterns.return_value = {
        'patterns': [
            {
                'id': 'P1',
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

    # Simulate API call
    event = {
        'body': json.dumps({
            'threats': [
                {'threat_type': 'Unknown Region', 'timestamp': '2026-05-26T00:00:00'},
                {'threat_type': 'Unauthorized SSH', 'timestamp': '2026-05-26T01:00:00'}
            ],
            'min_support': 0.3
        })
    }

    response = ml_handler.handle_identify_patterns(event)

    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'patterns' in body
    assert body['total_patterns'] == 1
    assert body['patterns'][0]['confidence'] == 0.8


def test_full_ml_dashboard_integration(ml_handler):
    """
    Integration test: Complete dashboard workflow
    All 4 ML components working together
    """
    # Setup all mock responses
    ml_handler.prediction_model.predict_threats.return_value = {
        'predictions': [
            {'date': '2026-05-27', 'expected_threats': 2.5, 'confidence': 0.95}
        ],
        'trend': 'increasing',
        'anomaly_score': 0.6,
        'model_accuracy': 0.88
    }

    ml_handler.clustering_engine.cluster_threats.return_value = {
        'clusters': [
            {
                'id': 'C1',
                'threats': ['t1', 't2'],
                'threat_count': 2,
                'cohesion': 0.92,
                'avg_severity': 7.5
            }
        ],
        'silhouette_score': 0.75,
        'threat_count': 2
    }

    ml_handler.trend_analyzer.analyze_trends.return_value = {
        'hourly_breakdown': [
            {'hour': '2026-05-26T00', 'threats': 5, 'avg_severity': 6.2}
        ],
        'daily_breakdown': [],
        'peak_hours': ['2026-05-26T00'],
        'safe_hours': ['2026-05-26T02'],
        'anomaly_hours': [],
        'trend': 'stable'
    }

    ml_handler.pattern_service.identify_patterns.return_value = {
        'patterns': [
            {
                'id': 'P1',
                'sequence': ['Unknown Region', 'Unauthorized SSH'],
                'support': 0.45,
                'confidence': 0.85,
                'lift': 2.1,
                'occurrences': 3
            }
        ],
        'total_patterns': 1,
        'threat_count': 5
    }

    # Execute all 4 ML operations
    account_id = 'test-account'

    # 1. Predictions
    pred_response = ml_handler.handle_predict_threats({
        'body': json.dumps({'account_id': account_id, 'days_ahead': 7})
    })
    assert pred_response['statusCode'] == 200

    # 2. Clustering
    cluster_response = ml_handler.handle_cluster_threats({
        'body': json.dumps({
            'threats': [
                {'threat_id': 't1', 'severity': 7, 'account_risk_score': 0.75,
                 'event_frequency': 4, 'resource_impact_count': 2,
                 'response_time_seconds': 100, 'remediation_success_rate': 0.75},
                {'threat_id': 't2', 'severity': 8, 'account_risk_score': 0.8,
                 'event_frequency': 5, 'resource_impact_count': 3,
                 'response_time_seconds': 120, 'remediation_success_rate': 0.7}
            ],
            'n_clusters': 1
        })
    })
    assert cluster_response['statusCode'] == 200

    # 3. Trends
    trend_response = ml_handler.handle_analyze_trends({
        'queryStringParameters': {
            'account_id': account_id,
            'time_range': '24h'
        }
    })
    assert trend_response['statusCode'] == 200

    # 4. Patterns
    pattern_response = ml_handler.handle_identify_patterns({
        'body': json.dumps({
            'threats': [
                {'threat_type': 'Unknown Region', 'timestamp': '2026-05-26T00:00:00'},
                {'threat_type': 'Unauthorized SSH', 'timestamp': '2026-05-26T01:00:00'},
                {'threat_type': 'Unknown Region', 'timestamp': '2026-05-26T02:00:00'}
            ],
            'min_support': 0.3
        })
    })
    assert pattern_response['statusCode'] == 200

    # Verify all results contain expected data
    pred_body = json.loads(pred_response['body'])
    assert pred_body['trend'] == 'increasing'
    assert pred_body['model_accuracy'] == 0.88

    cluster_body = json.loads(cluster_response['body'])
    assert cluster_body['cluster_count'] == 1
    assert cluster_body['silhouette_score'] == 0.75

    trend_body = json.loads(trend_response['body'])
    assert len(trend_body['hourly_breakdown']) > 0

    pattern_body = json.loads(pattern_response['body'])
    assert pattern_body['total_patterns'] == 1


def test_dashboard_metric_aggregation(ml_handler):
    """
    Integration test: ML metrics for dashboard display
    Verifies that dashboard can aggregate all ML metrics
    """
    # Setup metrics
    ml_handler.prediction_model.get_prediction_confidence.return_value = 0.85
    ml_handler.clustering_engine.cluster_threats.return_value = {
        'clusters': [],
        'silhouette_score': 0.8,
        'threat_count': 10
    }
    ml_handler.trend_analyzer.get_threat_velocity.return_value = {
        'threat_velocity': 2.5,
        'threats_per_hour': 2.5,
        'total_threats': 5,
        'trend': 'increasing'
    }
    ml_handler.trend_analyzer.get_threat_density.return_value = {
        'threat_density': 5.0,
        'total_threats': 5,
        'severity_distribution': {'high': 2, 'medium': 2, 'low': 1},
        'resource_distribution': {'EC2': 3, 'S3': 2}
    }

    # Simulate dashboard metric collection
    account_id = 'test-account'

    velocity_resp = ml_handler.handle_get_threat_velocity({
        'queryStringParameters': {
            'account_id': account_id,
            'time_window': '1h'
        }
    })
    assert velocity_resp['statusCode'] == 200

    density_resp = ml_handler.handle_get_threat_density({
        'queryStringParameters': {
            'account_id': account_id,
            'time_window': '1h'
        }
    })
    assert density_resp['statusCode'] == 200

    # Verify metrics
    velocity_body = json.loads(velocity_resp['body'])
    assert velocity_body['threat_velocity'] == 2.5

    density_body = json.loads(density_resp['body'])
    assert density_body['threat_density'] == 5.0
    assert density_body['severity_distribution']['high'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
