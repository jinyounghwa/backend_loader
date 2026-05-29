from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone


class ResponseFeedbackCollector:
    """실행 피드백 수집 및 학습 분석"""

    def __init__(self, storage: Optional["FeedbackResultsStorage"] = None):
        """
        초기화

        Args:
            storage: FeedbackResultsStorage 인스턴스 (DynamoDB 접근)
        """
        self.storage = storage or FeedbackResultsStorage()

    def record_execution_feedback(self, feedback_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        실행 피드백 기록

        Args:
            feedback_record: {
                'execution_id': UUID,
                'playbook_id': str,
                'threat_id': str,
                'threat_type': str,
                'account_id': str,
                'threat_resolved': bool,
                'resolution_time_minutes': int,
                'side_effects': bool,
                'side_effect_details': str (optional),
                'feedback_rating': 1-5,
                'feedback_timestamp': ISO timestamp
            }

        Returns:
            저장된 피드백 기록
        """
        # 피드백 검증
        if 'execution_id' not in feedback_record:
            raise ValueError("execution_id required")
        if 'threat_resolved' not in feedback_record:
            raise ValueError("threat_resolved required")
        if not isinstance(feedback_record['threat_resolved'], bool):
            raise ValueError("threat_resolved must be boolean")

        # 피드백 기록 저장
        self.storage.save_feedback(feedback_record)
        return feedback_record

    def calculate_feedback_metrics(
        self, playbook_id: str, days: int = 7
    ) -> Dict[str, Any]:
        """
        피드백 기반 메트릭 계산

        Args:
            playbook_id: Playbook ID
            days: 조회 기간 (일)

        Returns:
            {
                'playbook_id': str,
                'feedback_count': int,
                'threat_resolution_rate': float (0-1),
                'avg_resolution_time_minutes': float,
                'avg_feedback_rating': float (1-5),
                'side_effect_rate': float (0-1),
                'effectiveness_score': float (0-100)
            }
        """
        end_time = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
        start_time = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat() + 'Z'

        feedback_records = self.storage.query_by_playbook(playbook_id, start_time, end_time)

        if not feedback_records:
            return {
                'playbook_id': playbook_id,
                'feedback_count': 0,
                'threat_resolution_rate': 0.0,
                'avg_resolution_time_minutes': 0.0,
                'avg_feedback_rating': 0.0,
                'side_effect_rate': 0.0,
                'effectiveness_score': 0.0
            }

        total = len(feedback_records)
        resolved = sum(1 for r in feedback_records if r.get('threat_resolved', False))
        resolution_rate = resolved / total if total > 0 else 0.0

        # 해결 시간 평균
        resolution_times = [
            r.get('resolution_time_minutes', 0)
            for r in feedback_records
            if r.get('threat_resolved', False)
        ]
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0

        # 피드백 등급 평균
        ratings = [r.get('feedback_rating', 3) for r in feedback_records]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        # 부작용 발생률
        side_effects = sum(1 for r in feedback_records if r.get('side_effects', False))
        side_effect_rate = side_effects / total if total > 0 else 0.0

        # 종합 효율성 점수 (0-100)
        # 해결율(40%) + 등급(40%) + 부작용 페널티(20%)
        effectiveness_score = round(
            (resolution_rate * 40) + ((avg_rating / 5) * 40) - (side_effect_rate * 20),
            2
        )
        effectiveness_score = max(0, min(100, effectiveness_score))

        return {
            'playbook_id': playbook_id,
            'feedback_count': total,
            'threat_resolution_rate': round(resolution_rate, 3),
            'avg_resolution_time_minutes': round(avg_resolution_time, 2),
            'avg_feedback_rating': round(avg_rating, 2),
            'side_effect_rate': round(side_effect_rate, 3),
            'effectiveness_score': effectiveness_score
        }

    def get_threat_resolution_impact(
        self, threat_type: str, days: int = 7
    ) -> Dict[str, Any]:
        """
        위협 타입별 해결 영향도

        Args:
            threat_type: 위협 타입
            days: 조회 기간

        Returns:
            {
                'threat_type': str,
                'total_detections': int,
                'executions_triggered': int,
                'threats_resolved': int,
                'resolution_effectiveness': float (0-1),
                'avg_time_to_resolution_minutes': float,
                'top_effective_playbooks': [...]
            }
        """
        end_time = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
        start_time = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)).isoformat() + 'Z'

        feedback_records = self.storage.query_by_threat_type(threat_type, start_time, end_time)

        if not feedback_records:
            return {
                'threat_type': threat_type,
                'total_detections': 0,
                'executions_triggered': 0,
                'threats_resolved': 0,
                'resolution_effectiveness': 0.0,
                'avg_time_to_resolution_minutes': 0.0,
                'top_effective_playbooks': []
            }

        total = len(feedback_records)
        resolved = sum(1 for r in feedback_records if r.get('threat_resolved', False))
        resolution_effectiveness = resolved / total if total > 0 else 0.0

        # 해결 시간 평균
        resolution_times = [
            r.get('resolution_time_minutes', 0)
            for r in feedback_records
            if r.get('threat_resolved', False)
        ]
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0

        # Playbook별 효율성 점수 계산
        playbook_scores = {}
        for record in feedback_records:
            pb_id = record.get('playbook_id', 'unknown')
            if pb_id not in playbook_scores:
                playbook_scores[pb_id] = {'resolved': 0, 'total': 0, 'ratings': []}

            playbook_scores[pb_id]['total'] += 1
            if record.get('threat_resolved', False):
                playbook_scores[pb_id]['resolved'] += 1
            playbook_scores[pb_id]['ratings'].append(record.get('feedback_rating', 3))

        # 상위 효율적인 Playbook
        top_playbooks = []
        for pb_id, scores in sorted(
            playbook_scores.items(),
            key=lambda x: (x[1]['resolved'] / x[1]['total'], sum(x[1]['ratings']) / len(x[1]['ratings'])),
            reverse=True
        )[:3]:
            effectiveness = scores['resolved'] / scores['total'] if scores['total'] > 0 else 0.0
            avg_rating = sum(scores['ratings']) / len(scores['ratings']) if scores['ratings'] else 0.0
            top_playbooks.append({
                'playbook_id': pb_id,
                'effectiveness_score': round(effectiveness * 100, 2),
                'avg_rating': round(avg_rating, 2)
            })

        return {
            'threat_type': threat_type,
            'total_detections': total,
            'executions_triggered': total,
            'threats_resolved': resolved,
            'resolution_effectiveness': round(resolution_effectiveness, 3),
            'avg_time_to_resolution_minutes': round(avg_resolution_time, 2),
            'top_effective_playbooks': top_playbooks
        }

    def get_learning_recommendations(
        self, playbook_feedback_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        학습 기반 권장사항 생성

        Args:
            playbook_feedback_metrics: {
                'playbook_id': str,
                'effectiveness_score': float,
                'threat_resolution_rate': float,
                'avg_feedback_rating': float,
                'side_effect_rate': float
            }

        Returns:
            {
                'recommendations': [
                    {
                        'type': 'adjust_threshold' | 'disable_playbook' | 'increase_priority',
                        'target': str,
                        'reason': str,
                        'current_value': float,
                        'suggested_value': float (optional)
                    }
                ]
            }
        """
        recommendations = []

        effectiveness_score = playbook_feedback_metrics.get('effectiveness_score', 0)
        resolution_rate = playbook_feedback_metrics.get('threat_resolution_rate', 0)
        avg_rating = playbook_feedback_metrics.get('avg_feedback_rating', 0)
        side_effect_rate = playbook_feedback_metrics.get('side_effect_rate', 0)
        playbook_id = playbook_feedback_metrics.get('playbook_id', 'unknown')

        # 높은 부작용률 → 신뢰도 낮추기
        if side_effect_rate > 0.2:
            recommendations.append({
                'type': 'adjust_threshold',
                'target': playbook_id,
                'metric': 'confidence',
                'reason': f'high_side_effect_rate: {side_effect_rate:.1%}',
                'current_value': 0.85,
                'suggested_value': 0.95
            })

        # 낮은 효율성 → 비활성화
        if effectiveness_score < 30:
            recommendations.append({
                'type': 'disable_playbook',
                'playbook_id': playbook_id,
                'reason': 'low_effectiveness_score',
                'current_score': effectiveness_score
            })

        # 높은 해결률 → 우선순위 올리기
        if resolution_rate > 0.8 and avg_rating > 4.0:
            recommendations.append({
                'type': 'increase_priority',
                'playbook_id': playbook_id,
                'reason': 'high_resolution_rate_and_rating',
                'resolution_rate': resolution_rate,
                'avg_rating': avg_rating
            })

        return {'recommendations': recommendations}

    def wait_for_feedback(
        self, execution_id: str, timeout_minutes: int = 60
    ) -> Optional[Dict[str, Any]]:
        """
        실행에 대한 피드백 대기

        Args:
            execution_id: 실행 ID
            timeout_minutes: 타임아웃 시간 (분)

        Returns:
            피드백 기록 또는 None
        """
        # 실제 구현: DynamoDB 폴링
        # 테스트에서는 메모리 저장소 사용
        feedback = self.storage.get_feedback(execution_id)
        return feedback


class FeedbackResultsStorage:
    """피드백 결과 DynamoDB 저장소"""

    def __init__(self):
        """초기화"""
        # 실제 구현에서는 DynamoDB 클라이언트 초기화
        # 테스트용으로 메모리 저장소 사용
        self.feedbacks: Dict[str, Dict[str, Any]] = {}

    def save_feedback(self, feedback_record: Dict[str, Any]) -> bool:
        """
        피드백 저장

        Args:
            feedback_record: 저장할 피드백 기록

        Returns:
            성공 여부
        """
        execution_id = feedback_record.get('execution_id')
        if not execution_id:
            return False

        self.feedbacks[execution_id] = feedback_record
        return True

    def get_feedback(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        피드백 조회

        Args:
            execution_id: 실행 ID

        Returns:
            피드백 기록 또는 None
        """
        return self.feedbacks.get(execution_id)

    def query_by_playbook(
        self, playbook_id: str, start_timestamp: str, end_timestamp: str
    ) -> List[Dict[str, Any]]:
        """
        Playbook별 피드백 조회

        Args:
            playbook_id: Playbook ID
            start_timestamp: 시작 시간 (ISO 포맷)
            end_timestamp: 종료 시간 (ISO 포맷)

        Returns:
            해당 조건의 피드백 리스트
        """
        results = []
        for record in self.feedbacks.values():
            if record.get('playbook_id') != playbook_id:
                continue

            # 시간 범위 확인
            record_time = record.get('feedback_timestamp', '')
            if start_timestamp <= record_time <= end_timestamp:
                results.append(record)

        return results

    def query_by_threat_type(
        self, threat_type: str, start_timestamp: str, end_timestamp: str
    ) -> List[Dict[str, Any]]:
        """
        위협 타입별 피드백 조회

        Args:
            threat_type: 위협 타입
            start_timestamp: 시작 시간
            end_timestamp: 종료 시간

        Returns:
            해당 조건의 피드백 리스트
        """
        results = []
        for record in self.feedbacks.values():
            if record.get('threat_type') != threat_type:
                continue

            # 시간 범위 확인
            record_time = record.get('feedback_timestamp', '')
            if start_timestamp <= record_time <= end_timestamp:
                results.append(record)

        return results
