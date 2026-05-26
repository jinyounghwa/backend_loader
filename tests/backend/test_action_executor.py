import pytest
from datetime import datetime
import sys
sys.path.insert(0, '/Users/younghwa.jin/Documents/backend_loader/lambda')
from guardian.ml.action_executor import ActionExecutor


class TestActionExecutor:
    """작업 실행 및 검증 테스트"""

    def setup_method(self):
        """ActionExecutor 초기화"""
        self.executor = ActionExecutor()

    def test_execute_ec2_stop(self):
        """EC2 인스턴스 중지"""
        action = {
            'action_type': 'ec2_stop',
            'target_id': 'i-1234567890abcdef0',
            'account_id': 'test-account',
            'dry_run': False
        }

        result = self.executor.execute_action(action)

        # 실행 결과 확인
        assert result['action_type'] == 'ec2_stop'
        assert result['status'] == 'SUCCESS'
        assert result['target_id'] == 'i-1234567890abcdef0'
        assert 'action_id' in result
        assert 'timestamp' in result

    def test_execute_sg_restrict_port(self):
        """보안 그룹 포트 제한"""
        action = {
            'action_type': 'sg_restrict_port',
            'target_id': 'sg-12345678',
            'parameters': {'port': 22},
            'account_id': 'test-account',
            'dry_run': False
        }

        result = self.executor.execute_action(action)

        # 실행 결과 확인
        assert result['action_type'] == 'sg_restrict_port'
        assert result['status'] == 'SUCCESS'
        assert result['result']['port'] == 22
        assert result['result']['rules_removed'] == 1

    def test_execute_s3_block_public(self):
        """S3 공개 액세스 차단"""
        action = {
            'action_type': 's3_block_public',
            'target_id': 'my-sensitive-bucket',
            'account_id': 'test-account',
            'dry_run': False
        }

        result = self.executor.execute_action(action)

        # 실행 결과 확인
        assert result['action_type'] == 's3_block_public'
        assert result['status'] == 'SUCCESS'
        assert result['result']['block_public_acls'] is True
        assert result['result']['ignore_public_acls'] is True

    def test_validate_action_result(self):
        """작업 결과 검증"""
        # 먼저 작업 실행
        action = {
            'action_type': 'ec2_stop',
            'target_id': 'i-9876543210fedcba0',
            'account_id': 'test-account',
            'dry_run': False
        }
        action_result = self.executor.execute_action(action)

        # 검증
        validation = self.executor.validate_action_result(action_result, action)

        # 검증 결과 확인
        assert validation['action_id'] == action_result['action_id']
        assert validation['validated'] is True
        assert len(validation['checks_performed']) >= 2
        assert validation['validation_time'] >= 0

        # 모든 검사가 통과했는지 확인
        for check in validation['checks_performed']:
            assert check['passed'] is True

    def test_get_action_cost_estimate(self):
        """작업 비용 추정"""
        # EC2 중지: 비용 절감 없음 (이미 실행 중이면 중지)
        cost_ec2 = self.executor.get_action_cost_estimate('ec2_stop')
        assert cost_ec2 == 0.0

        # SG 제한: 비용 절감 없음
        cost_sg = self.executor.get_action_cost_estimate('sg_restrict_port')
        assert cost_sg == 0.0

        # NAT 차단: 월 비용 절감
        cost_nat = self.executor.get_action_cost_estimate('nat_block_region')
        assert cost_nat > 0  # NAT 게이트웨이 비용

    def test_rollback_action(self):
        """작업 취소"""
        # 먼저 작업 실행
        action = {
            'action_type': 'iam_disable_key',
            'target_id': 'AKIAIOSFODNN7EXAMPLE',
            'account_id': 'test-account',
            'dry_run': False
        }
        action_result = self.executor.execute_action(action)
        action_id = action_result['action_id']

        # 롤백
        rollback_result = self.executor.rollback_action(action_id)

        # 롤백 결과 확인
        assert rollback_result['action_id'] == action_id
        assert rollback_result['original_action_type'] == 'iam_disable_key'
        assert rollback_result['rollback_status'] == 'SUCCESS'
        assert 'rollback_action_id' in rollback_result

    def test_dry_run_mode(self):
        """드라이런 모드"""
        action = {
            'action_type': 'ec2_stop',
            'target_id': 'i-dryrun123',
            'account_id': 'test-account',
            'dry_run': True
        }

        result = self.executor.execute_action(action)

        # 드라이런 결과 확인
        assert result['status'] == 'DRY_RUN'
        assert result['dry_run'] is True
        # 실제 작업이 실행되지 않음 (status DRY_RUN)

    def test_unsupported_action_type(self):
        """지원하지 않는 작업 타입"""
        action = {
            'action_type': 'unsupported_action',
            'target_id': 'some-target',
            'account_id': 'test-account'
        }

        result = self.executor.execute_action(action)

        # 실패 결과 확인
        assert result['status'] == 'FAILED'
        assert 'Unsupported action type' in result['error']

    def test_rollback_nonexistent_action(self):
        """존재하지 않는 작업 롤백"""
        rollback_result = self.executor.rollback_action('nonexistent-action-id')

        # 실패 결과 확인
        assert rollback_result['rollback_status'] == 'FAILED'
        assert 'not found' in rollback_result['error'].lower()

    def test_multiple_actions_independent(self):
        """여러 작업이 독립적으로 실행"""
        action1 = {
            'action_type': 'ec2_stop',
            'target_id': 'i-instance1',
            'account_id': 'test-account'
        }
        action2 = {
            'action_type': 's3_block_public',
            'target_id': 'bucket1',
            'account_id': 'test-account'
        }

        result1 = self.executor.execute_action(action1)
        result2 = self.executor.execute_action(action2)

        # 두 작업이 다른 action_id를 가짐
        assert result1['action_id'] != result2['action_id']
        assert result1['status'] == 'SUCCESS'
        assert result2['status'] == 'SUCCESS'
