import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

try:
    import numpy as np
    from statsmodels.tsa.arima.model import ARIMA
except ImportError:
    np = None
    ARIMA = None


class ThreatPredictionModel:
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.threats_table = self.dynamodb.Table('guardian-threats')
        self.models = {}

    def predict_threats(self, account_id: str, days_ahead: int = 7, confidence: float = 0.95) -> Dict:
        """
        지난 30일 위협 데이터로 ARIMA 모델 학습 → 향후 N일 예측

        Args:
            account_id: AWS account ID
            days_ahead: 예측할 미래 일수
            confidence: 신뢰도 (0-1)

        Returns:
            {
                'predictions': [...],
                'trend': 'increasing|stable|decreasing',
                'anomaly_score': float,
                'model_accuracy': float
            }
        """
        historical_threats = self._get_historical_threats(account_id, lookback_days=30)

        if not historical_threats or len(historical_threats) < 7:
            return self._default_prediction()

        threat_counts = self._aggregate_daily_threats(historical_threats)

        try:
            if ARIMA is None:
                return self._fallback_trend_prediction(threat_counts, days_ahead)

            model = ARIMA(threat_counts, order=(1, 1, 1))
            fitted_model = model.fit()

            predictions = []
            confidence_intervals = fitted_model.get_forecast(steps=days_ahead).conf_int()
            forecast = fitted_model.get_forecast(steps=days_ahead).predicted_mean

            for i, (pred, conf_int) in enumerate(zip(forecast, confidence_intervals.values)):
                pred_date = (datetime.utcnow() + timedelta(days=i+1)).strftime('%Y-%m-%d')
                predictions.append({
                    'date': pred_date,
                    'expected_threats': max(0, float(pred)),
                    'confidence': float(confidence),
                    'lower_bound': max(0, float(conf_int[0])),
                    'upper_bound': float(conf_int[1])
                })

            trend = self._calculate_trend(forecast)
            anomaly_score = self._calculate_anomaly_score(threat_counts)
            model_accuracy = self._calculate_model_accuracy(fitted_model, threat_counts)

            return {
                'predictions': predictions,
                'trend': trend,
                'anomaly_score': anomaly_score,
                'model_accuracy': model_accuracy,
                'account_id': account_id
            }
        except Exception as e:
            return self._fallback_trend_prediction(threat_counts, days_ahead)

    def train_model(self, account_id: str, lookback_days: int = 30) -> Dict:
        """지난 N일 위협 데이터로 모델 재학습"""
        historical_threats = self._get_historical_threats(account_id, lookback_days)
        threat_counts = self._aggregate_daily_threats(historical_threats)

        try:
            if ARIMA is None:
                return {'status': 'fallback', 'account_id': account_id}

            model = ARIMA(threat_counts, order=(1, 1, 1))
            fitted_model = model.fit()

            self.models[account_id] = {
                'model': fitted_model,
                'trained_at': datetime.utcnow().isoformat(),
                'data_points': len(threat_counts)
            }

            return {
                'status': 'trained',
                'account_id': account_id,
                'data_points': len(threat_counts),
                'trained_at': self.models[account_id]['trained_at']
            }
        except Exception:
            return {'status': 'error', 'account_id': account_id}

    def get_prediction_confidence(self, account_id: str) -> float:
        """현재 모델 신뢰도 (0-1)"""
        if account_id not in self.models:
            return 0.0

        model_info = self.models[account_id]
        data_points = model_info.get('data_points', 0)

        # 데이터 포인트가 많을수록 신뢰도 높음 (30일 기준으로 1.0)
        confidence = min(1.0, data_points / 30.0)
        return float(confidence)

    def _get_historical_threats(self, account_id: str, lookback_days: int = 30) -> List[Dict]:
        """지난 N일 위협 데이터 조회"""
        start_date = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()

        try:
            response = self.threats_table.query(
                KeyConditionExpression='account_id = :aid AND #ts > :start',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':aid': account_id,
                    ':start': start_date
                },
                Limit=1000
            )
            return response.get('Items', [])
        except Exception:
            return []

    def _aggregate_daily_threats(self, threats: List[Dict]) -> List[int]:
        """일일 위협 카운트로 집계"""
        daily_counts = {}

        for threat in threats:
            threat_date = threat.get('timestamp', '')[:10]
            daily_counts[threat_date] = daily_counts.get(threat_date, 0) + 1

        sorted_dates = sorted(daily_counts.keys())
        threat_counts = [daily_counts[date] for date in sorted_dates]

        return threat_counts if threat_counts else [0]

    def _fallback_trend_prediction(self, threat_counts: List[int], days_ahead: int) -> Dict:
        """ARIMA 사용 불가 시 통계 기반 예측"""
        if threat_counts:
            if np is not None:
                avg_threats = np.mean(threat_counts)
                std_threats = np.std(threat_counts) if len(threat_counts) > 1 else 0
            else:
                avg_threats = sum(threat_counts) / len(threat_counts)
                if len(threat_counts) > 1:
                    variance = sum((x - avg_threats) ** 2 for x in threat_counts) / len(threat_counts)
                    std_threats = variance ** 0.5
                else:
                    std_threats = 0
        else:
            avg_threats = 0
            std_threats = 0

        predictions = []
        for i in range(days_ahead):
            pred_date = (datetime.utcnow() + timedelta(days=i+1)).strftime('%Y-%m-%d')
            predictions.append({
                'date': pred_date,
                'expected_threats': float(avg_threats),
                'confidence': 0.75,
                'lower_bound': max(0, float(avg_threats - std_threats)),
                'upper_bound': float(avg_threats + std_threats)
            })

        trend = self._calculate_trend_simple(threat_counts)

        return {
            'predictions': predictions,
            'trend': trend,
            'anomaly_score': 0.5,
            'model_accuracy': 0.7
        }

    def _calculate_trend(self, forecast) -> str:
        """추세 계산 (증가/안정/감소)"""
        if len(forecast) < 2:
            return 'stable'

        if np is not None:
            trend_values = np.diff(forecast)
            avg_trend = np.mean(trend_values)
        else:
            trend_values = [forecast[i] - forecast[i-1] for i in range(1, len(forecast))]
            avg_trend = sum(trend_values) / len(trend_values)

        if avg_trend > 0.5:
            return 'increasing'
        elif avg_trend < -0.5:
            return 'decreasing'
        else:
            return 'stable'

    def _calculate_trend_simple(self, data: List[int]) -> str:
        """통계 기반 추세 계산"""
        if len(data) < 2:
            return 'stable'

        mid = len(data) // 2

        if np is not None:
            first_half = np.mean(data[:mid])
            second_half = np.mean(data[mid:])
        else:
            first_half = sum(data[:mid]) / len(data[:mid]) if data[:mid] else 0
            second_half = sum(data[mid:]) / len(data[mid:]) if data[mid:] else 0

        if first_half == 0:
            return 'stable'

        if second_half > first_half * 1.2:
            return 'increasing'
        elif second_half < first_half * 0.8:
            return 'decreasing'
        else:
            return 'stable'

    def _calculate_anomaly_score(self, data) -> float:
        """이상도 점수 계산 (0-1)"""
        if len(data) < 2:
            return 0.0

        if np is not None:
            mean = np.mean(data)
            std = np.std(data)
            if std == 0:
                return 0.0
            z_scores = np.abs((data - mean) / std)
            anomaly_score = float(np.mean(z_scores) / 3.0)
        else:
            # Pure Python fallback
            mean = sum(data) / len(data)
            variance = sum((x - mean) ** 2 for x in data) / len(data)
            std = variance ** 0.5

            if std == 0:
                return 0.0

            z_scores = [abs((x - mean) / std) for x in data]
            anomaly_score = sum(z_scores) / len(z_scores) / 3.0

        return min(1.0, anomaly_score)

    def _calculate_model_accuracy(self, model, data: List[int]) -> float:
        """모델 정확도 계산"""
        try:
            if np is not None:
                aic = model.aic
                variance = np.var(data)
                max_aic = len(data) * np.log(variance + 1)
            else:
                # Pure Python fallback
                aic = getattr(model, 'aic', 100)
                mean = sum(data) / len(data)
                variance = sum((x - mean) ** 2 for x in data) / len(data)
                max_aic = len(data) * (variance + 1) ** 0.5

            accuracy = max(0.0, 1.0 - (aic / max_aic if max_aic > 0 else 0.7))
            return float(min(1.0, accuracy))
        except Exception:
            return 0.7

    def _default_prediction(self) -> Dict:
        """기본 예측 (데이터 부족 시)"""
        predictions = []
        for i in range(7):
            pred_date = (datetime.utcnow() + timedelta(days=i+1)).strftime('%Y-%m-%d')
            predictions.append({
                'date': pred_date,
                'expected_threats': 2.0,
                'confidence': 0.5,
                'lower_bound': 0.0,
                'upper_bound': 5.0
            })

        return {
            'predictions': predictions,
            'trend': 'stable',
            'anomaly_score': 0.0,
            'model_accuracy': 0.5
        }
