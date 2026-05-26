import pytest
from datetime import datetime
import sys
sys.path.insert(0, '/Users/younghwa.jin/Documents/backend_loader/lambda')
from guardian.ml.dashboard_metrics import DashboardMetrics


class TestDashboardMetrics:
    """대시보드 메트릭 테스트"""

    def setup_method(self):
        """DashboardMetrics 초기화"""
        self.metrics = DashboardMetrics()

    def test_register_and_get_execution_summary(self):
        """실행 등록 및 요약 조회"""
        execution_result = {
            'execution_id': 'exec-001',
            'playbook_id': 'pb-test',
            'status': 'COMPLETED',
            'actions_executed': 4,
            'actions_succeeded': 4,
            'actions_failed': 0,
            'execution_time_seconds': 15.5,
            'timestamp': '2026-05-26T10:00:00Z'
        }

        self.metrics.register_execution(execution_result)
        summary = self.metrics.get_execution_summary('exec-001')

        assert summary is not None
        assert summary['execution_id'] == 'exec-001'
        assert summary['success_rate'] == 1.0
        assert summary['total_actions'] == 4

    def test_get_playbook_health(self):
        """플레이북 상태"""
        # 여러 실행 등록
        for i in range(5):
            execution_result = {
                'execution_id': f'exec-health-{i}',
                'playbook_id': 'pb-health-test',
                'status': 'COMPLETED' if i < 4 else 'PARTIAL',
                'actions_executed': 2,
                'actions_succeeded': 2 if i < 4 else 1,
                'actions_failed': 0 if i < 4 else 1,
                'execution_time_seconds': 10.0 + i,
                'timestamp': f'2026-05-26T10:{i:02d}:00Z'
            }
            self.metrics.register_execution(execution_result)

        health = self.metrics.get_playbook_health('pb-health-test')

        assert health['playbook_id'] == 'pb-health-test'
        assert health['total_executions'] == 5
        assert health['success_rate'] == pytest.approx(0.8, abs=0.01)
        assert health['status'] == 'DEGRADED'  # 80% success = DEGRADED

    def test_get_playbook_health_healthy(self):
        """플레이북 상태 (건강함)"""
        for i in range(3):
            execution_result = {
                'execution_id': f'exec-healthy-{i}',
                'playbook_id': 'pb-healthy',
                'status': 'COMPLETED',
                'actions_executed': 2,
                'actions_succeeded': 2,
                'execution_time_seconds': 10.0,
                'timestamp': f'2026-05-26T10:{i:02d}:00Z'
            }
            self.metrics.register_execution(execution_result)

        health = self.metrics.get_playbook_health('pb-healthy')

        assert health['status'] == 'HEALTHY'
        assert health['success_rate'] == 1.0

    def test_get_threat_response_effectiveness(self):
        """위협 대응 효율성"""
        # 실행 등록
        for i in range(3):
            execution_result = {
                'execution_id': f'exec-threat-{i}',
                'playbook_id': 'pb-threat-response',
                'status': 'COMPLETED',
                'actions_executed': 2,
                'actions_succeeded': 2,
                'execution_time_seconds': 20.0 + i,
                'timestamp': f'2026-05-26T10:{i:02d}:00Z'
            }
            self.metrics.register_execution(execution_result)

        effectiveness = self.metrics.get_threat_response_effectiveness('Unknown Region')

        assert effectiveness['threat_type'] == 'Unknown Region'
        assert effectiveness['total_detections'] == 3
        assert effectiveness['responses_triggered'] == 3
        assert effectiveness['effectiveness_score'] > 0

    def test_get_system_overview(self):
        """시스템 전체 개요"""
        # 여러 실행 등록
        for i in range(5):
            execution_result = {
                'execution_id': f'exec-overview-{i}',
                'playbook_id': f'pb-overview-{i % 2}',
                'status': 'COMPLETED' if i < 4 else 'FAILED',
                'actions_executed': 3,
                'actions_succeeded': 3 if i < 4 else 0,
                'execution_time_seconds': 12.0,
                'timestamp': f'2026-05-26T10:{i:02d}:00Z'
            }
            self.metrics.register_execution(execution_result)

        overview = self.metrics.get_system_overview()

        assert overview['total_executions'] == 5
        assert overview['successful_executions'] == 4
        assert overview['failed_executions'] == 1
        assert overview['success_rate'] == pytest.approx(0.8, abs=0.01)
        assert overview['total_actions_executed'] == 15

    def test_get_recent_executions(self):
        """최근 실행 목록"""
        # 10개 실행 등록
        for i in range(10):
            execution_result = {
                'execution_id': f'exec-recent-{i}',
                'playbook_id': 'pb-recent',
                'status': 'COMPLETED',
                'actions_executed': 2,
                'actions_succeeded': 2,
                'execution_time_seconds': 10.0,
                'timestamp': f'2026-05-26T10:{i:02d}:00Z'
            }
            self.metrics.register_execution(execution_result)

        recent = self.metrics.get_recent_executions(limit=5)

        assert len(recent) == 5
        # 최신 순서로 정렬됨
        assert recent[0]['execution_id'].endswith('-9')

    def test_empty_metrics(self):
        """빈 메트릭"""
        summary = self.metrics.get_execution_summary('nonexistent')
        assert summary is None

        health = self.metrics.get_playbook_health('pb-nonexistent')
        assert health['total_executions'] == 0
        assert health['status'] == 'UNKNOWN'

        overview = self.metrics.get_system_overview()
        assert overview['total_executions'] == 0
        assert overview['success_rate'] == 0.0
