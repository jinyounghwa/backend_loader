import pytest
from datetime import datetime, timedelta, timezone
import sys
from guardian.ml.response_feedback_collector import ResponseFeedbackCollector


class TestResponseFeedbackCollector:
    """피드백 수집 및 학습 분석 테스트"""

    def setup_method(self):
        """ResponseFeedbackCollector 초기화"""
        self.collector = ResponseFeedbackCollector()

    def test_record_execution_feedback(self):
        """실행 피드백 기록"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        feedback = {
            'execution_id': 'exec-fb-001',
            'playbook_id': 'pb-ssh-block',
            'threat_id': 'threat-001',
            'threat_type': 'Unauthorized SSH',
            'account_id': 'test-account',
            'threat_resolved': True,
            'resolution_time_minutes': 5,
            'side_effects': False,
            'feedback_rating': 5,
            'feedback_timestamp': now.isoformat() + 'Z'
        }

        result = self.collector.record_execution_feedback(feedback)

        # 피드백 저장 확인
        assert result['execution_id'] == 'exec-fb-001'
        assert result['threat_resolved'] is True
        assert result['feedback_rating'] == 5
        assert result['side_effects'] is False

    def test_calculate_feedback_metrics(self):
        """피드백 메트릭 계산"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 4개 성공 피드백
        for i in range(4):
            feedback = {
                'execution_id': f'exec-fb-success-{i}',
                'playbook_id': 'pb-ssh-block',
                'threat_id': f'threat-{i}',
                'threat_type': 'Unauthorized SSH',
                'account_id': 'test-account',
                'threat_resolved': True,
                'resolution_time_minutes': 5 + i,  # 5, 6, 7, 8분
                'side_effects': False,
                'feedback_rating': 5 - i,  # 5, 4, 3, 2
                'feedback_timestamp': (now - timedelta(days=i)).isoformat() + 'Z'
            }
            self.collector.record_execution_feedback(feedback)

        # 1개 실패 피드백
        feedback_fail = {
            'execution_id': 'exec-fb-fail-1',
            'playbook_id': 'pb-ssh-block',
            'threat_id': 'threat-fail',
            'threat_type': 'Unauthorized SSH',
            'account_id': 'test-account',
            'threat_resolved': False,
            'resolution_time_minutes': 0,
            'side_effects': True,
            'feedback_rating': 2,
            'feedback_timestamp': now.isoformat() + 'Z'
        }
        self.collector.record_execution_feedback(feedback_fail)

        metrics = self.collector.calculate_feedback_metrics('pb-ssh-block', days=7)

        # 통계 확인
        assert metrics['feedback_count'] == 5
        assert metrics['threat_resolution_rate'] == pytest.approx(0.8, abs=0.01)  # 4/5
        assert metrics['avg_feedback_rating'] == pytest.approx(3.2, abs=0.1)  # (5+4+3+2+2)/5
        assert metrics['side_effect_rate'] == pytest.approx(0.2, abs=0.01)  # 1/5
        assert 0 <= metrics['effectiveness_score'] <= 100

    def test_get_threat_resolution_impact(self):
        """위협 타입별 해결 영향도"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Unknown Region 위협 3개 (2 성공, 1 실패)
        for i in range(3):
            feedback = {
                'execution_id': f'exec-ur-{i}',
                'playbook_id': 'pb-unknown-region-block' if i < 2 else 'pb-generic-block',
                'threat_id': f'threat-ur-{i}',
                'threat_type': 'Unknown Region',
                'account_id': 'test-account',
                'threat_resolved': i < 2,  # 처음 2개는 성공
                'resolution_time_minutes': 10 if i < 2 else 0,
                'side_effects': False,
                'feedback_rating': 5 if i < 2 else 1,
                'feedback_timestamp': (now - timedelta(days=i)).isoformat() + 'Z'
            }
            self.collector.record_execution_feedback(feedback)

        # SSH 위협 2개 (필터링되어야 함)
        for i in range(2):
            feedback = {
                'execution_id': f'exec-ssh-{i}',
                'playbook_id': 'pb-ssh-block',
                'threat_id': f'threat-ssh-{i}',
                'threat_type': 'Unauthorized SSH',
                'account_id': 'test-account',
                'threat_resolved': True,
                'resolution_time_minutes': 5,
                'side_effects': False,
                'feedback_rating': 5,
                'feedback_timestamp': (now - timedelta(days=i)).isoformat() + 'Z'
            }
            self.collector.record_execution_feedback(feedback)

        # Unknown Region만 조회
        impact = self.collector.get_threat_resolution_impact('Unknown Region', days=7)

        # Unknown Region 결과만 포함
        assert impact['threat_type'] == 'Unknown Region'
        assert impact['total_detections'] == 3
        assert impact['threats_resolved'] == 2
        assert impact['resolution_effectiveness'] == pytest.approx(0.667, abs=0.01)  # 2/3
        assert len(impact['top_effective_playbooks']) > 0

    def test_get_learning_recommendations(self):
        """학습 기반 권장사항 생성"""
        # 시나리오 1: 높은 효율성 → 우선순위 올리기
        high_effectiveness_metrics = {
            'playbook_id': 'pb-good',
            'effectiveness_score': 85,
            'threat_resolution_rate': 0.9,
            'avg_feedback_rating': 4.5,
            'side_effect_rate': 0.05
        }
        recommendations = self.collector.get_learning_recommendations(high_effectiveness_metrics)
        assert any(r['type'] == 'increase_priority' for r in recommendations['recommendations'])

        # 시나리오 2: 높은 부작용률 → 신뢰도 낮추기
        side_effect_metrics = {
            'playbook_id': 'pb-risky',
            'effectiveness_score': 50,
            'threat_resolution_rate': 0.8,
            'avg_feedback_rating': 3.0,
            'side_effect_rate': 0.3
        }
        recommendations = self.collector.get_learning_recommendations(side_effect_metrics)
        assert any(r['type'] == 'adjust_threshold' for r in recommendations['recommendations'])

        # 시나리오 3: 낮은 효율성 → 비활성화
        low_effectiveness_metrics = {
            'playbook_id': 'pb-bad',
            'effectiveness_score': 15,
            'threat_resolution_rate': 0.2,
            'avg_feedback_rating': 1.5,
            'side_effect_rate': 0.8
        }
        recommendations = self.collector.get_learning_recommendations(low_effectiveness_metrics)
        assert any(r['type'] == 'disable_playbook' for r in recommendations['recommendations'])

    def test_empty_feedback_metrics(self):
        """빈 피드백 메트릭"""
        # 존재하지 않는 playbook 조회
        metrics = self.collector.calculate_feedback_metrics('pb-nonexistent', days=7)

        assert metrics['feedback_count'] == 0
        assert metrics['threat_resolution_rate'] == 0.0
        assert metrics['avg_feedback_rating'] == 0.0
        assert metrics['effectiveness_score'] == 0.0

    def test_empty_threat_impact(self):
        """빈 위협 영향도"""
        impact = self.collector.get_threat_resolution_impact('Unknown Region', days=7)

        assert impact['threat_type'] == 'Unknown Region'
        assert impact['total_detections'] == 0
        assert impact['threats_resolved'] == 0
        assert impact['resolution_effectiveness'] == 0.0
        assert len(impact['top_effective_playbooks']) == 0
