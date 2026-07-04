import pytest
from datetime import datetime
import sys
from guardian.ml.playbook_orchestrator import PlaybookOrchestrator
from guardian.ml.action_executor import ActionExecutor


class TestPlaybookOrchestrator:
    """플레이북 조율 및 실행 테스트"""

    def setup_method(self):
        """PlaybookOrchestrator 초기화"""
        self.executor = ActionExecutor()
        self.orchestrator = PlaybookOrchestrator(self.executor)

    def test_execute_simple_playbook(self):
        """단순 플레이북 실행"""
        playbook = {
            'playbook_id': 'pb-ssh-response',
            'threat_id': 'threat-001',
            'threat_type': 'Unauthorized SSH',
            'account_id': 'test-account',
            'actions': [
                {
                    'action_id': 'action-1',
                    'action_type': 'sg_restrict_port',
                    'target_id': 'sg-12345678',
                    'parameters': {'port': 22}
                },
                {
                    'action_id': 'action-2',
                    'action_type': 'ec2_stop',
                    'target_id': 'i-1234567890abcdef0'
                }
            ]
        }

        result = self.orchestrator.execute_playbook(playbook)

        # 실행 결과 확인
        assert result['playbook_id'] == 'pb-ssh-response'
        assert result['status'] == 'COMPLETED'
        assert result['actions_executed'] == 2
        assert result['actions_succeeded'] == 2
        assert result['actions_failed'] == 0
        assert 'execution_id' in result
        assert result['execution_time_seconds'] >= 0

    def test_execute_playbook_with_dependencies(self):
        """의존성이 있는 플레이북 실행"""
        playbook = {
            'playbook_id': 'pb-s3-security',
            'threat_id': 'threat-002',
            'threat_type': 'Public S3 Bucket',
            'account_id': 'test-account',
            'actions': [
                {
                    'action_id': 'action-1',
                    'action_type': 's3_block_public',
                    'target_id': 'my-bucket'
                },
                {
                    'action_id': 'action-2',
                    'action_type': 'sg_restrict_port',
                    'target_id': 'sg-87654321',
                    'parameters': {'port': 443},
                    'depends_on': ['action-1']
                }
            ]
        }

        result = self.orchestrator.execute_playbook(playbook)

        # 의존성을 따라 순차 실행
        assert result['status'] == 'COMPLETED'
        assert result['actions_succeeded'] == 2
        assert len(result['action_results']) == 2

    def test_get_execution_status(self):
        """실행 상태 조회"""
        playbook = {
            'playbook_id': 'pb-test',
            'threat_id': 'threat-test',
            'threat_type': 'Test Threat',
            'account_id': 'test-account',
            'actions': [
                {
                    'action_id': 'action-1',
                    'action_type': 'ec2_stop',
                    'target_id': 'i-test'
                }
            ]
        }

        result = self.orchestrator.execute_playbook(playbook)
        execution_id = result['execution_id']

        # 상태 조회
        status = self.orchestrator.get_execution_status(execution_id)

        assert status is not None
        assert status['execution_id'] == execution_id
        assert status['playbook_id'] == 'pb-test'

    def test_get_execution_summary(self):
        """실행 요약 조회"""
        playbook = {
            'playbook_id': 'pb-summary-test',
            'threat_id': 'threat-summary',
            'threat_type': 'Test',
            'account_id': 'test-account',
            'actions': [
                {
                    'action_id': f'action-{i}',
                    'action_type': 'ec2_stop',
                    'target_id': f'i-{i}'
                } for i in range(3)
            ]
        }

        result = self.orchestrator.execute_playbook(playbook)
        execution_id = result['execution_id']

        # 요약 조회
        summary = self.orchestrator.get_execution_summary(execution_id)

        assert summary['execution_id'] == execution_id
        assert summary['total_actions'] == 3
        assert summary['success_rate'] == 1.0  # 모두 성공
        assert summary['execution_time_seconds'] >= 0

    def test_estimate_playbook_cost(self):
        """플레이북 비용 추정"""
        playbook = {
            'playbook_id': 'pb-cost-test',
            'threat_id': 'threat-cost',
            'threat_type': 'Test',
            'account_id': 'test-account',
            'actions': [
                {
                    'action_id': 'action-1',
                    'action_type': 'ec2_stop',
                    'target_id': 'i-1'
                },
                {
                    'action_id': 'action-2',
                    'action_type': 'nat_block_region',
                    'target_id': 'us-west-1'
                }
            ]
        }

        cost = self.orchestrator.estimate_playbook_cost(playbook)

        # EC2 stop ($0) + NAT block ($32) = $32
        assert cost == 32.0

    def test_get_parallel_actions(self):
        """병렬 실행 가능한 작업 그룹"""
        playbook = {
            'playbook_id': 'pb-parallel-test',
            'threat_id': 'threat-parallel',
            'threat_type': 'Test',
            'account_id': 'test-account',
            'actions': [
                {
                    'action_id': 'action-1',
                    'action_type': 'ec2_stop',
                    'target_id': 'i-1'
                },
                {
                    'action_id': 'action-2',
                    'action_type': 's3_block_public',
                    'target_id': 'bucket-1'
                },
                {
                    'action_id': 'action-3',
                    'action_type': 'sg_restrict_port',
                    'target_id': 'sg-1',
                    'depends_on': ['action-1', 'action-2']
                }
            ]
        }

        parallel_groups = self.orchestrator.get_parallel_actions(playbook)

        # action-1, action-2는 병렬 가능
        # action-3은 이들에 의존하므로 별도 그룹
        assert len(parallel_groups) >= 2

    def test_dry_run_mode(self):
        """드라이런 모드"""
        playbook = {
            'playbook_id': 'pb-dryrun',
            'threat_id': 'threat-dryrun',
            'threat_type': 'Test',
            'account_id': 'test-account',
            'dry_run': True,
            'actions': [
                {
                    'action_id': 'action-1',
                    'action_type': 'ec2_stop',
                    'target_id': 'i-dryrun'
                }
            ]
        }

        result = self.orchestrator.execute_playbook(playbook)

        # 드라이런 모드 확인
        assert result['action_results'][0].get('dry_run') is True

    def test_nonexistent_execution(self):
        """존재하지 않는 실행 조회"""
        status = self.orchestrator.get_execution_status('nonexistent-id')
        assert status is None

        summary = self.orchestrator.get_execution_summary('nonexistent-id')
        assert summary['status'] == 'NOT_FOUND'

    def test_playbook_with_multiple_actions(self):
        """많은 작업이 있는 플레이북"""
        actions = [
            {
                'action_id': f'action-{i}',
                'action_type': ['ec2_stop', 's3_block_public', 'sg_restrict_port'][i % 3],
                'target_id': f'target-{i}',
                'parameters': {'port': 22} if i % 3 == 2 else {}
            } for i in range(5)
        ]

        playbook = {
            'playbook_id': 'pb-multi-action',
            'threat_id': 'threat-multi',
            'threat_type': 'Complex Threat',
            'account_id': 'test-account',
            'actions': actions
        }

        result = self.orchestrator.execute_playbook(playbook)

        assert result['actions_executed'] == 5
        assert result['actions_succeeded'] == 5
        assert result['status'] == 'COMPLETED'
