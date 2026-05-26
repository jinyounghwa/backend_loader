import pytest
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/Users/younghwa.jin/Documents/backend_loader/lambda')
from guardian.ml.execution_metrics_collector import ExecutionMetricsCollector


class TestExecutionMetricsCollector:
    """Execution 메트릭 수집 테스트"""

    def setup_method(self):
        """ExecutionMetricsCollector 초기화"""
        self.collector = ExecutionMetricsCollector()

    def test_record_execution_result(self):
        """Execution 결과 기록"""
        execution = {
            'execution_id': 'exec-001',
            'playbook_id': 'pb-ssh-block',
            'threat_id': 'threat-001',
            'threat_type': 'Unauthorized SSH',
            'account_id': 'test-account',
            'status': 'COMPLETED',
            'started_at': '2026-05-26T10:00:00Z',
            'completed_at': '2026-05-26T10:00:05Z',
            'actions_executed': [
                {'action_type': 'security_group_update', 'success': True}
            ],
            'actions_failed': []
        }

        result = self.collector.record_execution_result(execution)

        # 기록 저장 확인
        assert result['execution_id'] == 'exec-001'
        assert result['playbook_id'] == 'pb-ssh-block'

        # 메트릭 계산 확인
        assert result['duration_seconds'] == 5.0
        assert result['success'] is True
        assert result['action_count'] == 1
        assert result['success_count'] == 1
        assert result['failure_count'] == 0

    def test_get_execution_history(self):
        """Playbook 실행 이력 조회"""
        # 여러 실행 기록 추가
        now = datetime.utcnow()
        for i in range(3):
            execution = {
                'execution_id': f'exec-00{i}',
                'playbook_id': 'pb-ssh-block',
                'threat_id': f'threat-00{i}',
                'threat_type': 'Unauthorized SSH',
                'account_id': 'test-account',
                'status': 'COMPLETED',
                'started_at': (now - timedelta(days=i)).isoformat() + 'Z',
                'completed_at': (now - timedelta(days=i) + timedelta(seconds=5)).isoformat() + 'Z',
                'actions_executed': [{'action_type': 'security_group_update', 'success': True}],
                'actions_failed': []
            }
            self.collector.record_execution_result(execution)

        # 다른 playbook 실행도 추가 (필터링되어야 함)
        execution_other = {
            'execution_id': 'exec-other',
            'playbook_id': 'pb-unknown-region-block',
            'threat_id': 'threat-other',
            'threat_type': 'Unknown Region',
            'account_id': 'test-account',
            'status': 'COMPLETED',
            'started_at': now.isoformat() + 'Z',
            'completed_at': (now + timedelta(seconds=3)).isoformat() + 'Z',
            'actions_executed': [{'action_type': 'ec2_stop', 'success': True}],
            'actions_failed': []
        }
        self.collector.record_execution_result(execution_other)

        # 조회
        history = self.collector.get_execution_history('pb-ssh-block', days=7)

        # pb-ssh-block만 3개 반환
        assert len(history) == 3
        for record in history:
            assert record['playbook_id'] == 'pb-ssh-block'

    def test_calculate_execution_metrics(self):
        """실행 메트릭 집계"""
        # 5개 실행: 4 성공, 1 실패
        now = datetime.utcnow()
        records = []

        # 4개 성공
        for i in range(4):
            records.append({
                'playbook_id': 'pb-ssh-block',
                'success': True,
                'duration_seconds': 10 + i,  # 10, 11, 12, 13초
                'actions_executed': [{'action_type': 'security_group_update'}],
                'actions_failed': []
            })

        # 1개 실패
        records.append({
            'playbook_id': 'pb-ssh-block',
            'success': False,
            'duration_seconds': 15,
            'actions_executed': [],
            'actions_failed': [{'action_type': 'security_group_update', 'error': 'Access denied'}]
        })

        metrics = self.collector.calculate_execution_metrics(records)

        # 통계 확인
        assert metrics['total_executions'] == 5
        assert metrics['successful'] == 4
        assert metrics['failed'] == 1
        assert metrics['success_rate'] == 0.8  # 4/5

        # 시간 통계
        assert metrics['avg_duration_seconds'] == 12.2  # (10+11+12+13+15)/5
        assert metrics['min_duration_seconds'] == 10.0
        assert metrics['max_duration_seconds'] == 15.0

        # Action 실패 패턴
        assert metrics['action_failure_counts']['security_group_update'] == 1

    def test_get_threat_type_metrics(self):
        """위협 타입별 메트릭"""
        now = datetime.utcnow()

        # Unknown Region 위협에 대한 실행 3개
        for i in range(3):
            execution = {
                'execution_id': f'exec-ur-{i}',
                'playbook_id': 'pb-unknown-region-block',
                'threat_id': f'threat-ur-{i}',
                'threat_type': 'Unknown Region',
                'account_id': 'test-account',
                'status': 'COMPLETED',
                'started_at': (now - timedelta(days=i)).isoformat() + 'Z',
                'completed_at': (now - timedelta(days=i) + timedelta(seconds=5)).isoformat() + 'Z',
                'actions_executed': [{'action_type': 'ec2_stop', 'success': True}],
                'actions_failed': []
            }
            self.collector.record_execution_result(execution)

        # SSH 위협에 대한 실행 2개 (필터링되어야 함)
        for i in range(2):
            execution = {
                'execution_id': f'exec-ssh-{i}',
                'playbook_id': 'pb-ssh-block',
                'threat_id': f'threat-ssh-{i}',
                'threat_type': 'Unauthorized SSH',
                'account_id': 'test-account',
                'status': 'COMPLETED',
                'started_at': (now - timedelta(days=i)).isoformat() + 'Z',
                'completed_at': (now - timedelta(days=i) + timedelta(seconds=3)).isoformat() + 'Z',
                'actions_executed': [{'action_type': 'security_group_update', 'success': True}],
                'actions_failed': []
            }
            self.collector.record_execution_result(execution)

        # Unknown Region 메트릭만 조회
        metrics = self.collector.get_threat_type_metrics('Unknown Region', days=7)

        # Unknown Region 실행만 포함
        assert metrics['total_executions'] == 3
        assert metrics['successful'] == 3
        assert metrics['success_rate'] == 1.0

    def test_get_playbook_impact_metrics(self):
        """Playbook 영향도 메트릭"""
        now = datetime.utcnow()

        # pb-ssh-block 실행 3개: 2 성공, 1 실패

        # 성공 1
        self.collector.record_execution_result({
            'execution_id': 'exec-impact-1',
            'playbook_id': 'pb-ssh-block',
            'threat_id': 'threat-impact-1',
            'threat_type': 'Unauthorized SSH',
            'account_id': 'test-account',
            'status': 'COMPLETED',
            'started_at': (now - timedelta(seconds=10)).isoformat() + 'Z',
            'completed_at': now.isoformat() + 'Z',
            'actions_executed': [{'action_type': 'security_group_update', 'success': True}],
            'actions_failed': []
        })

        # 성공 2
        self.collector.record_execution_result({
            'execution_id': 'exec-impact-2',
            'playbook_id': 'pb-ssh-block',
            'threat_id': 'threat-impact-2',
            'threat_type': 'Unauthorized SSH',
            'account_id': 'test-account',
            'status': 'COMPLETED',
            'started_at': (now - timedelta(seconds=8)).isoformat() + 'Z',
            'completed_at': now.isoformat() + 'Z',
            'actions_executed': [{'action_type': 'security_group_update', 'success': True}],
            'actions_failed': []
        })

        # 실패
        self.collector.record_execution_result({
            'execution_id': 'exec-impact-3',
            'playbook_id': 'pb-ssh-block',
            'threat_id': 'threat-impact-3',
            'threat_type': 'Unauthorized SSH',
            'account_id': 'test-account',
            'status': 'FAILED',
            'started_at': (now - timedelta(seconds=15)).isoformat() + 'Z',
            'completed_at': (now - timedelta(seconds=10)).isoformat() + 'Z',
            'actions_executed': [],
            'actions_failed': [{'action_type': 'security_group_update', 'error': 'Access denied'}]
        })

        impact = self.collector.get_playbook_impact_metrics('pb-ssh-block', days=7)

        # 영향도 확인
        assert impact['total_threats_targeted'] == 3  # 3개 고유 threat_id
        assert impact['threats_resolved'] == 2  # 성공한 것만
        assert impact['mitigation_rate'] == pytest.approx(0.667, abs=0.01)  # 2/3
        assert impact['total_resources_affected'] == 3
        assert impact['avg_response_time_seconds'] == pytest.approx(7.67, abs=0.1)  # (10+8+5)/3

    def test_empty_execution_history(self):
        """빈 실행 이력 처리"""
        # 존재하지 않는 playbook 조회
        history = self.collector.get_execution_history('pb-nonexistent', days=7)
        assert history == []

        # 빈 기록으로 메트릭 계산
        metrics = self.collector.calculate_execution_metrics([])
        assert metrics['total_executions'] == 0
        assert metrics['successful'] == 0
        assert metrics['failed'] == 0
        assert metrics['success_rate'] == 0.0

    def test_playbook_impact_no_results(self):
        """결과 없는 impact 메트릭"""
        impact = self.collector.get_playbook_impact_metrics('pb-nonexistent', days=7)

        assert impact['playbook_id'] == 'pb-nonexistent'
        assert impact['total_threats_targeted'] == 0
        assert impact['threats_resolved'] == 0
        assert impact['mitigation_rate'] == 0.0
