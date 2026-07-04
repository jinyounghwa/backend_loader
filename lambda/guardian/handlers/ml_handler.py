import json
import boto3
import os
from datetime import datetime, timezone
from typing import Dict, Any

from guardian.ml.threat_prediction_model import ThreatPredictionModel
from guardian.ml.anomaly_clustering_engine import AnomalyClusteringEngine
from guardian.ml.threat_trend_analyzer import ThreatTrendAnalyzer
from guardian.ml.pattern_recognition_service import PatternRecognitionService


class MLHandler:
    def __init__(self):
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        except Exception:
            # Fallback for testing
            self.dynamodb = None

        self.prediction_model = ThreatPredictionModel(self.dynamodb)
        self.clustering_engine = AnomalyClusteringEngine(self.dynamodb)
        self.trend_analyzer = ThreatTrendAnalyzer(self.dynamodb)
        self.pattern_service = PatternRecognitionService(self.dynamodb)

    def handle_predict_threats(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /ml/predict
        위협 예측 엔드포인트
        """
        try:
            body = json.loads(event.get('body', '{}'))
            account_id = body.get('account_id')
            days_ahead = body.get('days_ahead', 7)

            if not account_id:
                return self._error_response(400, 'account_id is required')

            result = self.prediction_model.predict_threats(account_id, days_ahead)

            return self._success_response(200, {
                'predictions': result['predictions'],
                'trend': result['trend'],
                'anomaly_score': result['anomaly_score'],
                'model_accuracy': result['model_accuracy'],
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def handle_cluster_threats(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /ml/cluster
        위협 클러스터링 엔드포인트
        """
        try:
            body = json.loads(event.get('body', '{}'))
            threats = body.get('threats', [])
            n_clusters = body.get('n_clusters', 5)

            if not threats:
                return self._error_response(400, 'threats list is required')

            result = self.clustering_engine.cluster_threats(threats, n_clusters)

            return self._success_response(200, {
                'clusters': result['clusters'],
                'silhouette_score': result['silhouette_score'],
                'cluster_count': len(result['clusters']),
                'threat_count': result.get('threat_count', len(threats)),
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def handle_analyze_trends(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        GET /ml/trends
        추세 분석 엔드포인트
        """
        try:
            query_params = event.get('queryStringParameters', {}) or {}
            account_id = query_params.get('account_id')
            time_range = query_params.get('time_range', '24h')

            if not account_id:
                return self._error_response(400, 'account_id is required')

            result = self.trend_analyzer.analyze_trends(account_id, time_range)

            return self._success_response(200, {
                'hourly_breakdown': result['hourly_breakdown'],
                'daily_breakdown': result['daily_breakdown'],
                'peak_hours': result['peak_hours'],
                'safe_hours': result['safe_hours'],
                'anomaly_hours': result['anomaly_hours'],
                'trend': result['trend'],
                'time_range': time_range,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def handle_get_threat_velocity(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        GET /ml/velocity
        위협 속도 계산 엔드포인트
        """
        try:
            query_params = event.get('queryStringParameters', {}) or {}
            account_id = query_params.get('account_id')
            time_window = query_params.get('time_window', '1h')

            if not account_id:
                return self._error_response(400, 'account_id is required')

            result = self.trend_analyzer.get_threat_velocity(account_id, time_window)

            return self._success_response(200, {
                'threat_velocity': result['threat_velocity'],
                'threats_per_hour': result['threats_per_hour'],
                'total_threats': result['total_threats'],
                'trend': result['trend'],
                'time_window': time_window,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def handle_get_threat_density(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        GET /ml/density
        위협 밀도 계산 엔드포인트
        """
        try:
            query_params = event.get('queryStringParameters', {}) or {}
            account_id = query_params.get('account_id')
            time_window = query_params.get('time_window', '1h')

            if not account_id:
                return self._error_response(400, 'account_id is required')

            result = self.trend_analyzer.get_threat_density(account_id, time_window)

            return self._success_response(200, {
                'threat_density': result['threat_density'],
                'total_threats': result['total_threats'],
                'severity_distribution': result['severity_distribution'],
                'resource_distribution': result['resource_distribution'],
                'time_window': time_window,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def handle_identify_patterns(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /ml/patterns
        패턴 발견 엔드포인트
        """
        try:
            body = json.loads(event.get('body', '{}'))
            threats = body.get('threats', [])
            min_support = body.get('min_support', 0.3)

            if not threats:
                return self._error_response(400, 'threats list is required')

            result = self.pattern_service.identify_patterns(threats, min_support)

            return self._success_response(200, {
                'patterns': result['patterns'],
                'total_patterns': result['total_patterns'],
                'threat_count': result['threat_count'],
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def handle_match_pattern(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /ml/match-pattern
        패턴 매칭 엔드포인트
        """
        try:
            body = json.loads(event.get('body', '{}'))
            threat_sequence = body.get('threat_sequence', [])
            patterns = body.get('patterns', [])

            if not threat_sequence or not patterns:
                return self._error_response(400, 'threat_sequence and patterns are required')

            result = self.pattern_service.match_pattern(threat_sequence, patterns)

            return self._success_response(200, {
                'current_sequence': result['current_sequence'],
                'matched_patterns': result['matched_patterns'],
                'pattern_count': result['pattern_count'],
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def handle_get_similar_threats(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /ml/similar-threats
        유사 위협 검색 엔드포인트
        """
        try:
            body = json.loads(event.get('body', '{}'))
            threat_id = body.get('threat_id')
            all_threats = body.get('all_threats', [])
            similarity_threshold = body.get('similarity_threshold', 0.7)

            if not threat_id or not all_threats:
                return self._error_response(400, 'threat_id and all_threats are required')

            result = self.clustering_engine.get_similar_threats(
                threat_id,
                all_threats,
                similarity_threshold
            )

            return self._success_response(200, {
                'threat_id': result['threat_id'],
                'similar_threats': result['similar_threats'],
                'count': result['count'],
                'threshold': similarity_threshold,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def handle_train_model(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /ml/train
        모델 재학습 엔드포인트
        """
        try:
            body = json.loads(event.get('body', '{}'))
            account_id = body.get('account_id')
            lookback_days = body.get('lookback_days', 30)

            if not account_id:
                return self._error_response(400, 'account_id is required')

            result = self.prediction_model.train_model(account_id, lookback_days)

            return self._success_response(200, {
                'status': result['status'],
                'account_id': result['account_id'],
                'trained_at': result.get('trained_at'),
                'data_points': result.get('data_points'),
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        except Exception as e:
            return self._error_response(500, str(e))

    def _success_response(self, status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
        """성공 응답 생성"""
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(body)
        }

    def _error_response(self, status_code: int, error_message: str) -> Dict[str, Any]:
        """에러 응답 생성"""
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': error_message,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            })
        }


# Lambda 핸들러 진입점
ml_handler = MLHandler()


def handle_predict_threats(event, context):
    """예측 핸들러"""
    return ml_handler.handle_predict_threats(event)


def handle_cluster_threats(event, context):
    """클러스터링 핸들러"""
    return ml_handler.handle_cluster_threats(event)


def handle_analyze_trends(event, context):
    """추세 분석 핸들러"""
    return ml_handler.handle_analyze_trends(event)


def handle_get_threat_velocity(event, context):
    """위협 속도 핸들러"""
    return ml_handler.handle_get_threat_velocity(event)


def handle_get_threat_density(event, context):
    """위협 밀도 핸들러"""
    return ml_handler.handle_get_threat_density(event)


def handle_identify_patterns(event, context):
    """패턴 발견 핸들러"""
    return ml_handler.handle_identify_patterns(event)


def handle_match_pattern(event, context):
    """패턴 매칭 핸들러"""
    return ml_handler.handle_match_pattern(event)


def handle_get_similar_threats(event, context):
    """유사 위협 핸들러"""
    return ml_handler.handle_get_similar_threats(event)


def handle_train_model(event, context):
    """모델 재학습 핸들러"""
    return ml_handler.handle_train_model(event)
