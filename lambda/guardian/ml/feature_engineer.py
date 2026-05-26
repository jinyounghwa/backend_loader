import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """피드백 데이터에서 머신러닝용 특성 추출"""

    def __init__(self):
        self.threat_type_encoder = {}
        self.time_of_day_encoder = {}
        self.severity_encoder = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}

    def extract_features(self, feedback_logs: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """
        피드백 로그 → 특성 벡터 및 레이블 추출

        Args:
            feedback_logs: 피드백 레코드 목록
                - threat_id, threat_type, severity, is_correct, timestamp, evidence

        Returns:
            (X, y): 특성 배열과 레이블 배열
        """
        if not feedback_logs:
            return np.array([]), np.array([])

        features = []
        labels = []

        for log in feedback_logs:
            try:
                feature_dict = self.engineer_single_feedback(log)
                feature_vector = self._dict_to_vector(feature_dict)
                label = 1 if log.get('is_correct', False) else 0

                features.append(feature_vector)
                labels.append(label)
            except Exception as e:
                logger.warning(f"Failed to engineer feature for {log.get('threat_id')}: {e}")
                continue

        return np.array(features), np.array(labels)

    def engineer_single_feedback(self, feedback: Dict[str, Any]) -> Dict[str, float]:
        """단일 피드백 → 특성 딕셔너리"""
        return {
            'threat_type_id': self._encode_threat_type(feedback.get('threat_type')),
            'severity_numeric': self.severity_encoder.get(feedback.get('severity', 'LOW'), 0),
            'evidence_count': len(feedback.get('evidence', [])),
            'detection_latency_sec': feedback.get('detection_latency_sec', 0),
            'action_success_rate': feedback.get('action_success_rate', 0.0),
            'hour_of_day': self._extract_hour(feedback.get('timestamp')),
            'day_of_week': self._extract_day_of_week(feedback.get('timestamp')),
            'is_night_time': float(self._is_night_time(feedback.get('timestamp'))),
            'account_id_hash': hash(feedback.get('account_id', '')) % 1000,
            'source_ip_anomaly': float(feedback.get('source_ip_anomaly', False)),
        }

    def engineer_batch_features(self, threats: List[Dict]) -> Dict[str, Any]:
        """배치 데이터에서 집계 특성 추출"""
        return {
            'num_threats_detected': len(threats),
            'threat_type_distribution': self._get_threat_distribution(threats),
            'severity_distribution': self._get_severity_distribution(threats),
            'average_detection_latency': self._get_avg_latency(threats),
            'peak_time': self._get_peak_time(threats),
            'affected_account_ids': len(set(t.get('account_id') for t in threats)),
        }

    def extract_threat_patterns(
        self,
        detections: List[Dict],
        actions: List[Dict],
        outcomes: List[Dict]
    ) -> Dict[str, Any]:
        """위협-대응-결과 패턴 추출"""
        patterns = {
            'threat_to_action_mapping': self._build_threat_action_mapping(detections, actions),
            'action_success_patterns': self._analyze_action_outcomes(actions, outcomes),
            'temporal_patterns': self._extract_temporal_patterns(detections),
            'account_vulnerability_profile': self._build_account_profiles(detections),
        }
        return patterns

    def _encode_threat_type(self, threat_type: str) -> int:
        """위협 유형 → 숫자 인코딩"""
        if threat_type not in self.threat_type_encoder:
            self.threat_type_encoder[threat_type] = len(self.threat_type_encoder)
        return self.threat_type_encoder[threat_type]

    def _extract_hour(self, timestamp: str) -> int:
        """타임스탬프 → 시간 (0-23)"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.hour
        except:
            return 12

    def _extract_day_of_week(self, timestamp: str) -> int:
        """타임스탬프 → 요일 (0=월요일, 6=일요일)"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.weekday()
        except:
            return 0

    def _is_night_time(self, timestamp: str) -> bool:
        """야간 여부 (22:00-06:00)"""
        hour = self._extract_hour(timestamp)
        return hour >= 22 or hour < 6

    def _get_threat_distribution(self, threats: List[Dict]) -> Dict[str, int]:
        """위협 유형별 분포"""
        types = [t.get('threat_type', 'unknown') for t in threats]
        return dict(Counter(types))

    def _get_severity_distribution(self, threats: List[Dict]) -> Dict[str, int]:
        """심각도별 분포"""
        severities = [t.get('severity', 'LOW') for t in threats]
        return dict(Counter(severities))

    def _get_avg_latency(self, threats: List[Dict]) -> float:
        """평균 탐지 지연 시간"""
        latencies = [t.get('detection_latency_sec', 0) for t in threats]
        return sum(latencies) / len(latencies) if latencies else 0.0

    def _get_peak_time(self, threats: List[Dict]) -> str:
        """위협이 가장 많은 시간대"""
        hours = [self._extract_hour(t.get('timestamp', '')) for t in threats]
        if not hours:
            return '00:00'
        peak_hour = Counter(hours).most_common(1)[0][0]
        return f'{peak_hour:02d}:00'

    def _build_threat_action_mapping(self, detections: List[Dict], actions: List[Dict]) -> Dict:
        """위협 유형별 실행된 작업 매핑"""
        mapping = {}
        for detection in detections:
            threat_type = detection.get('threat_type')
            related_actions = [a for a in actions if a.get('threat_id') == detection.get('threat_id')]
            action_types = [a.get('action_type') for a in related_actions]
            mapping[threat_type] = action_types
        return mapping

    def _analyze_action_outcomes(self, actions: List[Dict], outcomes: List[Dict]) -> Dict:
        """작업별 성공률"""
        success_rates = {}
        for action_type in set(a.get('action_type') for a in actions):
            related = [a for a in actions if a.get('action_type') == action_type]
            successful = sum(1 for a in related if any(o.get('action_id') == a.get('action_id') and o.get('success') for o in outcomes))
            success_rates[action_type] = successful / len(related) if related else 0.0
        return success_rates

    def _extract_temporal_patterns(self, detections: List[Dict]) -> Dict:
        """시간대별 패턴"""
        hourly_counts = [0] * 24
        for detection in detections:
            hour = self._extract_hour(detection.get('timestamp', ''))
            hourly_counts[hour] += 1
        return {'hourly_distribution': hourly_counts}

    def _build_account_profiles(self, detections: List[Dict]) -> Dict:
        """계정별 취약점 프로필"""
        profiles = {}
        for detection in detections:
            account_id = detection.get('account_id')
            if account_id not in profiles:
                profiles[account_id] = {'threat_count': 0, 'threat_types': []}
            profiles[account_id]['threat_count'] += 1
            profiles[account_id]['threat_types'].append(detection.get('threat_type'))
        return profiles

    def _dict_to_vector(self, feature_dict: Dict[str, Any]) -> np.ndarray:
        """특성 딕셔너리 → 벡터 (일정한 순서)"""
        keys = sorted(feature_dict.keys())
        values = [feature_dict[k] for k in keys]
        return np.array(values, dtype=np.float32)
