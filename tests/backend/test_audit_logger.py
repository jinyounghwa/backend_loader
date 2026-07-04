import pytest
from datetime import datetime
import sys
from guardian.ml.audit_logger import AuditLogger


class TestAuditLogger:
    """감사 로깅 테스트"""

    def setup_method(self):
        """AuditLogger 초기화"""
        self.logger = AuditLogger()

    def test_log_action_execution(self):
        """작업 실행 로깅"""
        action_result = {
            'action_id': 'action-001',
            'action_type': 'ec2_stop',
            'target_id': 'i-12345678',
            'status': 'SUCCESS',
            'timestamp': '2026-05-26T10:00:00Z'
        }
        metadata = {
            'user_id': 'user-123',
            'playbook_id': 'pb-ssh',
            'threat_id': 'threat-456'
        }

        log_id = self.logger.log_action_execution(action_result, metadata)

        assert log_id == 'action-001'
        assert log_id in self.logger.audit_logs

    def test_log_playbook_execution(self):
        """플레이북 실행 로깅"""
        execution_result = {
            'execution_id': 'exec-001',
            'playbook_id': 'pb-ssh-block',
            'status': 'COMPLETED',
            'actions_executed': 2,
            'actions_succeeded': 2,
            'actions_failed': 0,
            'timestamp': '2026-05-26T10:05:00Z'
        }
        metadata = {
            'user_id': 'user-123',
            'threat_id': 'threat-456'
        }

        log_id = self.logger.log_playbook_execution(execution_result, metadata)

        assert log_id == 'exec-001'
        assert self.logger.audit_logs['exec-001']['playbook_id'] == 'pb-ssh-block'

    def test_get_audit_trail(self):
        """플레이북 감사 추적"""
        # 여러 작업 로깅
        for i in range(3):
            action_result = {
                'action_id': f'action-{i}',
                'action_type': 'ec2_stop',
                'status': 'SUCCESS',
                'timestamp': f'2026-05-26T10:0{i}:00Z'
            }
            self.logger.log_action_execution(action_result, {
                'playbook_id': 'pb-test',
                'threat_id': 'threat-test'
            })

        trail = self.logger.get_audit_trail('pb-test')

        assert len(trail) == 3
        assert all(log['playbook_id'] == 'pb-test' for log in trail)

    def test_get_threat_response_history(self):
        """위협별 대응 이력"""
        # 같은 위협에 대한 여러 대응
        for i in range(2):
            action_result = {
                'action_id': f'action-threat-{i}',
                'action_type': 'sg_restrict_port',
                'status': 'SUCCESS',
                'timestamp': f'2026-05-26T10:0{i}:00Z'
            }
            self.logger.log_action_execution(action_result, {
                'threat_id': 'threat-ssh-001'
            })

        history = self.logger.get_threat_response_history('threat-ssh-001')

        assert len(history) == 2
        assert all(log['threat_id'] == 'threat-ssh-001' for log in history)

    def test_get_action_statistics(self):
        """작업 통계"""
        # 여러 작업 로깅 (성공/실패 섞음)
        for i in range(5):
            action_result = {
                'action_id': f'action-stat-{i}',
                'action_type': 'ec2_stop',
                'target_id': f'i-{i % 2}',  # 2개 대상
                'status': 'SUCCESS' if i < 4 else 'FAILED',
                'timestamp': f'2026-05-26T10:{i:02d}:00Z'
            }
            self.logger.log_action_execution(action_result, {})

        stats = self.logger.get_action_statistics('ec2_stop')

        assert stats['total_executions'] == 5
        assert stats['successful'] == 4
        assert stats['failed'] == 1
        assert stats['success_rate'] == pytest.approx(0.8, abs=0.01)

    def test_empty_audit_trail(self):
        """빈 감사 추적"""
        trail = self.logger.get_audit_trail('pb-nonexistent')
        assert trail == []

        history = self.logger.get_threat_response_history('threat-nonexistent')
        assert history == []

    def test_action_statistics_not_found(self):
        """작업 통계 없음"""
        stats = self.logger.get_action_statistics('nonexistent_action')

        assert stats['total_executions'] == 0
        assert stats['successful'] == 0
        assert stats['failed'] == 0
