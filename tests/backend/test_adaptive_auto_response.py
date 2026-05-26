import pytest
from guardian.responses.adaptive_auto_response import AdaptiveAutoResponse


class TestAdaptiveAutoResponse:
    """AdaptiveAutoResponse 테스트"""

    @pytest.fixture
    def responder(self):
        """AdaptiveAutoResponse 인스턴스"""
        return AdaptiveAutoResponse()

    @pytest.fixture
    def critical_anomaly(self):
        """심각한 이상 탐지"""
        return {
            'severity': 'CRITICAL',
            'confidence': 0.95,
            'z_score': 5.0,
            'anomaly_type': 'volumetric'
        }

    @pytest.fixture
    def high_anomaly(self):
        """높은 심각도 이상"""
        return {
            'severity': 'HIGH',
            'confidence': 0.85,
            'z_score': 3.0,
            'anomaly_type': 'behavioral'
        }

    @pytest.fixture
    def medium_anomaly(self):
        """중간 심각도 이상"""
        return {
            'severity': 'MEDIUM',
            'confidence': 0.65,
            'z_score': 2.0,
            'anomaly_type': 'pattern'
        }

    @pytest.fixture
    def context(self):
        """컨텍스트"""
        return {
            'current_cost': 200,
            'daily_budget': 1000,
            'resource_type': 'ec2_instance',
            'region': 'us-east-1'
        }

    def test_decide_response_critical(self, responder, critical_anomaly, context):
        """Critical 이상에 대한 대응 결정"""
        result = responder.decide_response(critical_anomaly, context)

        assert result['decision_id'] is not None
        assert result['action'] == 'terminate_resource'
        assert result['confidence'] > 0.7  # Learning may adjust confidence
        assert result['estimated_cost'] == 500

    def test_decide_response_high(self, responder, high_anomaly, context):
        """High 이상에 대한 대응 결정"""
        result = responder.decide_response(high_anomaly, context)

        assert result['decision_id'] is not None
        assert result['action'] in ['isolate_resource', 'notify_admin']
        assert result['confidence'] > 0.6  # Learning may adjust confidence

    def test_decide_response_medium(self, responder, medium_anomaly, context):
        """Medium 이상에 대한 대응 결정"""
        result = responder.decide_response(medium_anomaly, context)

        assert result['decision_id'] is not None
        assert result['action'] == 'alert'
        assert result['estimated_cost'] == 0

    def test_record_feedback_success(self, responder, critical_anomaly, context):
        """성공적인 대응 피드백"""
        # 대응 결정
        decision = responder.decide_response(critical_anomaly, context)

        # 피드백 기록
        feedback = responder.record_feedback(
            decision['decision_id'],
            {'status': 'success'},
            user_rating=5.0
        )

        assert feedback['feedback_id'] is not None
        assert feedback['effectiveness_score'] > 0.9
        assert feedback['learning_update'] is True

    def test_record_feedback_partial(self, responder, high_anomaly, context):
        """부분 성공 대응 피드백"""
        decision = responder.decide_response(high_anomaly, context)

        feedback = responder.record_feedback(
            decision['decision_id'],
            {'status': 'partial'},
            user_rating=3.0
        )

        assert feedback['effectiveness_score'] > 0.5
        assert feedback['effectiveness_score'] < 0.8

    def test_record_feedback_failure(self, responder, medium_anomaly, context):
        """실패한 대응 피드백"""
        decision = responder.decide_response(medium_anomaly, context)

        feedback = responder.record_feedback(
            decision['decision_id'],
            {'status': 'failure'},
            user_rating=1.0
        )

        assert feedback['effectiveness_score'] < 0.4

    def test_get_action_effectiveness(self, responder, critical_anomaly, context):
        """액션 효과성 조회"""
        # 여러 결정과 피드백
        for i in range(3):
            decision = responder.decide_response(critical_anomaly, context)
            responder.record_feedback(
                decision['decision_id'],
                {'status': 'success' if i < 2 else 'failure'},
                user_rating=5.0 if i < 2 else 2.0
            )

        effectiveness = responder.get_action_effectiveness('terminate_resource', days=7)

        assert effectiveness['action'] == 'terminate_resource'
        assert effectiveness['total_executions'] == 3
        assert effectiveness['successful'] == 2
        assert effectiveness['success_rate'] > 0.6

    def test_cost_benefit_analysis_budget_limited(self, responder):
        """비용 효과 분석 - 예산 제한"""
        # 예산이 거의 없는 상황
        context = {
            'current_cost': 950,
            'daily_budget': 1000,
            'resource_type': 'ec2_instance'
        }

        high_anomaly = {
            'severity': 'HIGH',
            'confidence': 0.8,
            'z_score': 3.0,
            'anomaly_type': 'behavioral'
        }

        result = responder.decide_response(high_anomaly, context)

        # 예산이 부족하면 notify_admin 선택
        assert result['action'] in ['notify_admin', 'alert']
        assert result['estimated_cost'] < 100

    def test_learning_summary(self, responder, critical_anomaly, high_anomaly, context):
        """학습 데이터 요약"""
        # 여러 결정과 피드백으로 학습
        for anomaly in [critical_anomaly, high_anomaly]:
            decision = responder.decide_response(anomaly, context)
            responder.record_feedback(
                decision['decision_id'],
                {'status': 'success'},
                user_rating=4.0
            )

        summary = responder.get_learning_summary()

        assert summary['total_decisions'] >= 2
        assert summary['total_feedback'] >= 2
        assert summary['avg_effectiveness'] > 0.6
        assert summary['best_action'] in AdaptiveAutoResponse.RESPONSE_ACTIONS
        assert 'actions_summary' in summary
