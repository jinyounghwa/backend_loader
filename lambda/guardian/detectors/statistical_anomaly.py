import logging
import uuid
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StatisticalAnomalyDetector:
    """통계 기반 이상 탐지 (Z-score)"""

    def __init__(self):
        """이상 탐지기 초기화"""
        self.baselines = {}
        self.anomalies = []

    def train_baseline(self, historical_data: List[Dict], window_days: int = 7) -> Dict:
        """
        정상 패턴 학습

        Args:
            historical_data: 과거 데이터 (event_count, latency_ms, error_rate 등)
            window_days: 학습 윈도우 (일수)

        Returns:
            {
                'baseline_id': str,
                'metrics': {
                    'mean': float,
                    'std_dev': float,
                    'percentile_95': float,
                    'percentile_99': float
                },
                'trained_at': str
            }
        """
        if not historical_data:
            return {
                'baseline_id': None,
                'error': 'No historical data provided'
            }

        baseline_id = str(uuid.uuid4())

        # 이벤트 개수 기반 메트릭 추출
        event_counts = []
        latencies = []
        error_rates = []

        for data in historical_data:
            if 'event_count' in data:
                event_counts.append(data['event_count'])
            if 'latency_ms' in data:
                latencies.append(data['latency_ms'])
            if 'error_rate' in data:
                error_rates.append(data['error_rate'])

        # 통계 계산
        metrics = {}

        if event_counts:
            metrics['event_count'] = self._calculate_metrics(event_counts)
        if latencies:
            metrics['latency'] = self._calculate_metrics(latencies)
        if error_rates:
            metrics['error_rate'] = self._calculate_metrics(error_rates)

        self.baselines[baseline_id] = {
            'baseline_id': baseline_id,
            'metrics': metrics,
            'trained_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'window_days': window_days
        }

        logger.info(f"Baseline trained: {baseline_id} with {len(historical_data)} data points")

        return {
            'baseline_id': baseline_id,
            'metrics': metrics,
            'trained_at': self.baselines[baseline_id]['trained_at']
        }

    def detect_anomaly(self, event: Dict, baseline: Dict) -> Dict:
        """
        이상 탐지 (Z-score)

        Args:
            event: 현재 이벤트
            baseline: 기준선

        Returns:
            {
                'is_anomaly': bool,
                'z_score': float,
                'anomaly_type': str,  # 'volumetric', 'behavioral', 'pattern'
                'severity': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
                'confidence': float (0-1)
            }
        """
        max_z_score = 0.0
        selected_anomaly_type = None
        selected_severity = 'LOW'
        selected_confidence = 0.0

        # Event count 이상 탐지
        if 'event_count' in event and 'event_count' in baseline.get('metrics', {}):
            z_score, atype, sev, conf = self._detect_volumetric_anomaly(
                event['event_count'],
                baseline['metrics']['event_count']
            )
            if abs(z_score) > abs(max_z_score):
                max_z_score = z_score
                selected_anomaly_type = atype
                selected_severity = sev
                selected_confidence = conf

        # Latency 이상 탐지
        if 'latency_ms' in event and 'latency' in baseline.get('metrics', {}):
            z_score, atype, sev, conf = self._detect_behavioral_anomaly(
                event['latency_ms'],
                baseline['metrics']['latency']
            )
            if abs(z_score) > abs(max_z_score):
                max_z_score = z_score
                selected_anomaly_type = atype
                selected_severity = sev
                selected_confidence = conf

        # Error rate 이상 탐지
        if 'error_rate' in event and 'error_rate' in baseline.get('metrics', {}):
            z_score, atype, sev, conf = self._detect_pattern_anomaly(
                event['error_rate'],
                baseline['metrics']['error_rate']
            )
            if abs(z_score) > abs(max_z_score):
                max_z_score = z_score
                selected_anomaly_type = atype
                selected_severity = sev
                selected_confidence = conf

        is_anomaly = max_z_score > 1.5

        result = {
            'is_anomaly': is_anomaly,
            'z_score': round(max_z_score, 2),
            'anomaly_type': selected_anomaly_type,
            'severity': selected_severity,
            'confidence': round(selected_confidence, 3)
        }

        if is_anomaly:
            self.anomalies.append(result)
            logger.info(f"Anomaly detected: {selected_anomaly_type} (Z={max_z_score}, severity={selected_severity})")

        return result

    def get_anomaly_insights(self, event: Dict, baseline: Dict) -> Dict:
        """
        이상에 대한 인사이트 제공

        Args:
            event: 현재 이벤트
            baseline: 기준선

        Returns:
            {
                'expected_value': float,
                'actual_value': float,
                'deviation_percent': float,
                'recommendation': str
            }
        """
        insights = {}

        # Event count 인사이트
        if 'event_count' in event and 'event_count' in baseline.get('metrics', {}):
            expected = baseline['metrics']['event_count']['mean']
            actual = event['event_count']
            deviation = ((actual - expected) / expected * 100) if expected > 0 else 0

            insights['event_count'] = {
                'expected_value': expected,
                'actual_value': actual,
                'deviation_percent': round(deviation, 2),
                'recommendation': self._get_recommendation(deviation)
            }

        # Latency 인사이트
        if 'latency_ms' in event and 'latency' in baseline.get('metrics', {}):
            expected = baseline['metrics']['latency']['mean']
            actual = event['latency_ms']
            deviation = ((actual - expected) / expected * 100) if expected > 0 else 0

            insights['latency'] = {
                'expected_value': expected,
                'actual_value': actual,
                'deviation_percent': round(deviation, 2),
                'recommendation': self._get_recommendation(deviation)
            }

        return insights

    def update_baseline(self, new_data: List[Dict]) -> None:
        """
        기준선 업데이트 (점진적 학습)

        Args:
            new_data: 새로운 데이터
        """
        if not new_data or not self.baselines:
            return

        # 가장 최근 baseline 업데이트
        baseline_id = list(self.baselines.keys())[-1]
        baseline = self.baselines[baseline_id]

        # 새 데이터 병합
        event_counts = []
        latencies = []
        error_rates = []

        for data in new_data:
            if 'event_count' in data:
                event_counts.append(data['event_count'])
            if 'latency_ms' in data:
                latencies.append(data['latency_ms'])
            if 'error_rate' in data:
                error_rates.append(data['error_rate'])

        # 기준선 메트릭 업데이트 (가중 평균)
        if event_counts and 'event_count' in baseline['metrics']:
            old_mean = baseline['metrics']['event_count']['mean']
            new_mean = (old_mean * 0.7 + statistics.mean(event_counts) * 0.3) if event_counts else old_mean
            baseline['metrics']['event_count']['mean'] = new_mean

        if latencies and 'latency' in baseline['metrics']:
            old_mean = baseline['metrics']['latency']['mean']
            new_mean = (old_mean * 0.7 + statistics.mean(latencies) * 0.3) if latencies else old_mean
            baseline['metrics']['latency']['mean'] = new_mean

        logger.info(f"Baseline {baseline_id} updated with {len(new_data)} new data points")

    def _calculate_metrics(self, values: List[float]) -> Dict:
        """통계 메트릭 계산"""
        if not values:
            return {'mean': 0, 'std_dev': 0, 'percentile_95': 0, 'percentile_99': 0}

        sorted_values = sorted(values)
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

        # Percentile 계산
        p95_idx = int(len(sorted_values) * 0.95)
        p99_idx = int(len(sorted_values) * 0.99)

        percentile_95 = sorted_values[p95_idx] if p95_idx < len(sorted_values) else sorted_values[-1]
        percentile_99 = sorted_values[p99_idx] if p99_idx < len(sorted_values) else sorted_values[-1]

        return {
            'mean': round(mean, 2),
            'std_dev': round(std_dev, 2),
            'percentile_95': round(percentile_95, 2),
            'percentile_99': round(percentile_99, 2)
        }

    def _calculate_z_score(self, value: float, mean: float, std_dev: float) -> float:
        """Z-score 계산"""
        if std_dev == 0:
            return 0.0
        return (value - mean) / std_dev

    def _get_severity(self, z_score: float) -> str:
        """Z-score에 따른 심각도 결정"""
        if z_score > 3:
            return 'CRITICAL'
        elif z_score > 2:
            return 'HIGH'
        elif z_score > 1.5:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _get_confidence(self, z_score: float) -> float:
        """Z-score에 따른 신뢰도 계산"""
        # Z-score를 신뢰도로 변환 (0-1 범위)
        confidence = min(abs(z_score) / 4.0, 1.0)
        return confidence

    def _detect_volumetric_anomaly(self, event_count: float, baseline_metrics: Dict) -> tuple:
        """
        볼륨 이상 탐지 (이벤트 개수)

        Returns: (z_score, anomaly_type, severity, confidence)
        """
        mean = baseline_metrics['mean']
        std_dev = baseline_metrics['std_dev']

        z_score = self._calculate_z_score(event_count, mean, std_dev)
        severity = self._get_severity(z_score)
        confidence = self._get_confidence(z_score)

        return z_score, 'volumetric', severity, confidence

    def _detect_behavioral_anomaly(self, latency: float, baseline_metrics: Dict) -> tuple:
        """
        행동 이상 탐지 (지연시간)

        Returns: (z_score, anomaly_type, severity, confidence)
        """
        mean = baseline_metrics['mean']
        std_dev = baseline_metrics['std_dev']

        z_score = self._calculate_z_score(latency, mean, std_dev)
        severity = self._get_severity(z_score)
        confidence = self._get_confidence(z_score)

        return z_score, 'behavioral', severity, confidence

    def _detect_pattern_anomaly(self, error_rate: float, baseline_metrics: Dict) -> tuple:
        """
        패턴 이상 탐지 (에러율)

        Returns: (z_score, anomaly_type, severity, confidence)
        """
        mean = baseline_metrics['mean']
        std_dev = baseline_metrics['std_dev']

        z_score = self._calculate_z_score(error_rate, mean, std_dev)
        severity = self._get_severity(z_score)
        confidence = self._get_confidence(z_score)

        return z_score, 'pattern', severity, confidence

    def _get_recommendation(self, deviation: float) -> str:
        """편차에 따른 권장사항"""
        if deviation > 50:
            return 'Immediate investigation required - significant increase detected'
        elif deviation > 25:
            return 'Monitor closely - moderate increase detected'
        elif deviation < -50:
            return 'Check system health - significant decrease detected'
        elif deviation < -25:
            return 'Monitor closely - moderate decrease detected'
        else:
            return 'Normal variation - within expected range'
