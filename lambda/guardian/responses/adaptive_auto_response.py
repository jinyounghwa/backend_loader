import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AdaptiveAutoResponse:
    """학습 기반의 적응형 자동 대응"""

    RESPONSE_ACTIONS = {
        'alert': {'cost': 0, 'severity_threshold': 'LOW'},
        'notify_admin': {'cost': 0, 'severity_threshold': 'MEDIUM'},
        'isolate_resource': {'cost': 100, 'severity_threshold': 'HIGH'},
        'terminate_resource': {'cost': 500, 'severity_threshold': 'CRITICAL'},
        'escalate_incident': {'cost': 0, 'severity_threshold': 'CRITICAL'}
    }

    def __init__(self):
        """적응형 자동 대응기 초기화"""
        self.decisions = []
        self.feedback_history = []
        self.learning_data = {}

    def decide_response(self, anomaly: Dict, context: Dict) -> Dict:
        """
        이상에 대한 대응 결정

        Args:
            anomaly: 탐지된 이상
            context: 컨텍스트 (리소스, 비용, 등)

        Returns:
            {
                'decision_id': str,
                'action': str,
                'confidence': float,
                'estimated_cost': float,
                'reasoning': str
            }
        """
        decision_id = str(uuid.uuid4())

        # 심각도에 따른 기본 대응 결정
        severity = anomaly.get('severity', 'LOW')
        confidence = anomaly.get('confidence', 0.5)

        # 비용-효과 분석
        action, cost, reasoning = self._analyze_cost_benefit(
            severity,
            confidence,
            context.get('current_cost', 0),
            context.get('daily_budget', 1000)
        )

        # 학습 데이터에 기반한 대응 조정
        adjusted_action, adjusted_confidence = self._apply_learning(
            action,
            confidence,
            context
        )

        result = {
            'decision_id': decision_id,
            'action': adjusted_action,
            'confidence': round(adjusted_confidence, 3),
            'estimated_cost': cost,
            'reasoning': reasoning,
            'timestamp': datetime.utcnow().isoformat()
        }

        self.decisions.append(result)
        logger.info(f"Decision made: {adjusted_action} (confidence={adjusted_confidence}, cost=${cost})")

        return result

    def record_feedback(self, decision_id: str, outcome: Dict, user_rating: Optional[float] = None) -> Dict:
        """
        대응 결과 피드백 기록

        Args:
            decision_id: 결정 ID
            outcome: 대응 결과 (success, failure, partial)
            user_rating: 사용자 평가 (0-5)

        Returns:
            {
                'feedback_id': str,
                'effectiveness_score': float,
                'learning_update': bool
            }
        """
        feedback_id = str(uuid.uuid4())

        # 효과성 점수 계산
        effectiveness = self._calculate_effectiveness(outcome, user_rating)

        feedback = {
            'feedback_id': feedback_id,
            'decision_id': decision_id,
            'outcome': outcome.get('status', 'unknown'),
            'effectiveness_score': effectiveness,
            'user_rating': user_rating,
            'timestamp': datetime.utcnow().isoformat()
        }

        self.feedback_history.append(feedback)

        # 학습 데이터 업데이트
        self._update_learning_data(decision_id, feedback)

        logger.info(f"Feedback recorded: {decision_id} (effectiveness={effectiveness})")

        return {
            'feedback_id': feedback_id,
            'effectiveness_score': round(effectiveness, 2),
            'learning_update': True
        }

    def get_action_effectiveness(self, action: str, days: int = 7) -> Dict:
        """
        특정 대응 액션의 효과성

        Args:
            action: 액션명
            days: 조회 기간 (일)

        Returns:
            {
                'action': str,
                'total_executions': int,
                'successful': int,
                'success_rate': float,
                'avg_effectiveness': float,
                'trend': str  # 'improving', 'declining', 'stable'
            }
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        # 필터링된 피드백
        filtered = [
            fb for fb in self.feedback_history
            if fb['decision_id'] in [d['decision_id'] for d in self.decisions if d['action'] == action]
            and datetime.fromisoformat(fb['timestamp']) > cutoff_time
        ]

        if not filtered:
            return {
                'action': action,
                'total_executions': 0,
                'successful': 0,
                'success_rate': 0.0,
                'avg_effectiveness': 0.0,
                'trend': 'no_data'
            }

        successful = sum(1 for fb in filtered if fb['effectiveness_score'] > 0.7)
        success_rate = successful / len(filtered) if filtered else 0.0
        avg_effectiveness = sum(fb['effectiveness_score'] for fb in filtered) / len(filtered)

        # 추세 분석
        recent = filtered[-min(3, len(filtered)):]
        older = filtered[:-min(3, len(filtered))]

        recent_avg = sum(fb['effectiveness_score'] for fb in recent) / len(recent) if recent else 0
        older_avg = sum(fb['effectiveness_score'] for fb in older) / len(older) if older else 0

        if recent_avg > older_avg * 1.1:
            trend = 'improving'
        elif recent_avg < older_avg * 0.9:
            trend = 'declining'
        else:
            trend = 'stable'

        return {
            'action': action,
            'total_executions': len(filtered),
            'successful': successful,
            'success_rate': round(success_rate, 3),
            'avg_effectiveness': round(avg_effectiveness, 3),
            'trend': trend
        }

    def _analyze_cost_benefit(
        self,
        severity: str,
        confidence: float,
        current_cost: float,
        daily_budget: float
    ) -> tuple:
        """
        비용-효과 분석

        Returns: (action, cost, reasoning)
        """
        severity_levels = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
        severity_score = severity_levels.get(severity, 1)

        # 신뢰도와 심각도에 따른 가중치
        risk_score = severity_score * confidence

        # 비용 여유 확인
        remaining_budget = daily_budget - current_cost
        budget_factor = remaining_budget / daily_budget if daily_budget > 0 else 0.5

        # 대응 액션 결정
        if severity == 'CRITICAL' and confidence > 0.8:
            action = 'terminate_resource'
            cost = 500
            reasoning = 'Critical severity with high confidence requires immediate termination'
        elif severity == 'CRITICAL':
            action = 'isolate_resource'
            cost = 100
            reasoning = 'Critical severity requires isolation'
        elif severity == 'HIGH' and budget_factor > 0.3:
            action = 'isolate_resource'
            cost = 100
            reasoning = 'High severity with sufficient budget'
        elif severity == 'HIGH':
            action = 'notify_admin'
            cost = 0
            reasoning = 'High severity but limited budget - escalate to admin'
        elif severity == 'MEDIUM':
            action = 'alert'
            cost = 0
            reasoning = 'Medium severity - send alert'
        else:
            action = 'alert'
            cost = 0
            reasoning = 'Low severity - send alert for monitoring'

        return action, cost, reasoning

    def _apply_learning(self, action: str, confidence: float, context: Dict) -> tuple:
        """
        학습 데이터에 기반한 대응 조정

        Returns: (adjusted_action, adjusted_confidence)
        """
        # 해당 액션의 최근 효과성 조회
        effectiveness = self.get_action_effectiveness(action, days=7)

        adjusted_confidence = confidence

        # 액션이 최근에 효과적이었으면 신뢰도 증가
        if effectiveness.get('success_rate', 0) > 0.8:
            adjusted_confidence = min(confidence * 1.2, 1.0)
        # 액션이 최근에 비효과적이었으면 신뢰도 감소
        elif effectiveness.get('success_rate', 0) < 0.4:
            adjusted_confidence = confidence * 0.8

        # 추세에 따른 액션 조정
        trend = effectiveness.get('trend', 'stable')
        adjusted_action = action

        if trend == 'declining' and action == 'alert':
            # Alert만으로는 효과가 떨어지는 경향이면 notify_admin으로 상향
            adjusted_action = 'notify_admin'

        return adjusted_action, adjusted_confidence

    def _calculate_effectiveness(self, outcome: Dict, user_rating: Optional[float] = None) -> float:
        """
        대응 효과성 점수 계산 (0-1)

        Args:
            outcome: 대응 결과
            user_rating: 사용자 평가 (0-5)

        Returns:
            효과성 점수 (0-1)
        """
        effectiveness = 0.5  # 기본값

        # 결과 상태에 따른 점수
        status = outcome.get('status', 'unknown')
        if status == 'success':
            effectiveness = 0.95
        elif status == 'partial':
            effectiveness = 0.6
        elif status == 'failure':
            effectiveness = 0.2

        # 사용자 평가 반영 (가중치 30%)
        if user_rating is not None:
            user_score = user_rating / 5.0
            effectiveness = effectiveness * 0.7 + user_score * 0.3

        return effectiveness

    def _update_learning_data(self, decision_id: str, feedback: Dict) -> None:
        """
        학습 데이터 업데이트

        Args:
            decision_id: 결정 ID
            feedback: 피드백
        """
        # 결정과 피드백 매칭
        decision = None
        for d in self.decisions:
            if d['decision_id'] == decision_id:
                decision = d
                break

        if not decision:
            return

        action = decision['action']
        effectiveness = feedback['effectiveness_score']

        # 액션별 학습 데이터 누적
        if action not in self.learning_data:
            self.learning_data[action] = {
                'total': 0,
                'successful': 0,
                'total_effectiveness': 0.0
            }

        self.learning_data[action]['total'] += 1
        self.learning_data[action]['total_effectiveness'] += effectiveness

        if effectiveness > 0.7:
            self.learning_data[action]['successful'] += 1

        logger.info(f"Learning data updated for action {action}: {self.learning_data[action]}")

    def get_learning_summary(self) -> Dict:
        """
        학습 데이터 요약

        Returns:
            {
                'total_decisions': int,
                'total_feedback': int,
                'avg_effectiveness': float,
                'best_action': str,
                'actions_summary': {action: {success_rate, avg_effectiveness}}
            }
        """
        total_decisions = len(self.decisions)
        total_feedback = len(self.feedback_history)

        avg_effectiveness = (
            sum(fb['effectiveness_score'] for fb in self.feedback_history) / total_feedback
            if self.feedback_history else 0.0
        )

        actions_summary = {}
        for action, data in self.learning_data.items():
            success_rate = data['successful'] / data['total'] if data['total'] > 0 else 0.0
            avg_eff = data['total_effectiveness'] / data['total'] if data['total'] > 0 else 0.0
            actions_summary[action] = {
                'success_rate': round(success_rate, 3),
                'avg_effectiveness': round(avg_eff, 3)
            }

        # 최고 성능 액션 찾기
        best_action = 'unknown'
        best_score = 0.0
        for action, summary in actions_summary.items():
            if summary['avg_effectiveness'] > best_score:
                best_score = summary['avg_effectiveness']
                best_action = action

        return {
            'total_decisions': total_decisions,
            'total_feedback': total_feedback,
            'avg_effectiveness': round(avg_effectiveness, 3),
            'best_action': best_action,
            'actions_summary': actions_summary
        }
