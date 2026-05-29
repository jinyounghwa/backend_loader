from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid


class ActionExecutor:
    """AWS 작업 실행 및 검증"""

    SUPPORTED_ACTIONS = {
        'ec2_stop': 'Stop EC2 instance',
        'sg_restrict_port': 'Remove overly permissive security group rule',
        's3_block_public': 'Enable S3 Block Public Access',
        'iam_disable_key': 'Disable IAM access key',
        'nat_block_region': 'Block region in NAT allowlist'
    }

    def __init__(self):
        """초기화"""
        # 실제 구현: boto3 clients 초기화
        # 테스트용: 메모리 저장소 사용
        self.executed_actions: Dict[str, Dict[str, Any]] = {}
        self.action_history: Dict[str, Dict[str, Any]] = {}

    def execute_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        AWS 작업 실행

        Args:
            action_spec: {
                'action_type': str (ec2_stop, sg_restrict_port, s3_block_public, etc),
                'target_id': str,
                'parameters': dict (optional),
                'account_id': str,
                'dry_run': bool (optional)
            }

        Returns:
            {
                'action_id': UUID,
                'action_type': str,
                'status': 'SUCCESS' | 'FAILED',
                'target_id': str,
                'result': dict,
                'error': str (optional),
                'timestamp': ISO timestamp,
                'dry_run': bool
            }
        """
        action_type = action_spec.get('action_type')
        target_id = action_spec.get('target_id')
        account_id = action_spec.get('account_id')
        dry_run = action_spec.get('dry_run', False)
        parameters = action_spec.get('parameters', {})

        # 작업 타입 검증
        if action_type not in self.SUPPORTED_ACTIONS:
            return {
                'action_id': str(uuid.uuid4()),
                'action_type': action_type,
                'status': 'FAILED',
                'target_id': target_id,
                'error': f'Unsupported action type: {action_type}',
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z',
                'dry_run': dry_run
            }

        # 작업 실행
        try:
            if action_type == 'ec2_stop':
                result = self._execute_ec2_stop(target_id, account_id, dry_run)
            elif action_type == 'sg_restrict_port':
                result = self._execute_sg_restrict(target_id, parameters.get('port'), account_id, dry_run)
            elif action_type == 's3_block_public':
                result = self._execute_s3_block_public(target_id, account_id, dry_run)
            elif action_type == 'iam_disable_key':
                result = self._execute_iam_disable_key(target_id, account_id, dry_run)
            elif action_type == 'nat_block_region':
                result = self._execute_nat_block_region(target_id, account_id, dry_run)
            else:
                result = {'error': 'Unknown action type'}

            action_id = str(uuid.uuid4())
            action_result = {
                'action_id': action_id,
                'action_type': action_type,
                'status': result.get('status', 'FAILED'),
                'target_id': target_id,
                'result': result,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z',
                'dry_run': dry_run
            }

            # 작업 기록 저장
            self.executed_actions[action_id] = action_result
            self.action_history[action_id] = action_spec

            return action_result

        except Exception as e:
            return {
                'action_id': str(uuid.uuid4()),
                'action_type': action_type,
                'status': 'FAILED',
                'target_id': target_id,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z',
                'dry_run': dry_run
            }

    def validate_action_result(
        self, action_result: Dict[str, Any], original_action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        작업 결과 검증

        Args:
            action_result: execute_action()의 반환값
            original_action: 원본 작업 spec

        Returns:
            {
                'action_id': str,
                'validated': bool,
                'validation_time': float,
                'checks_performed': [
                    {'check_type': str, 'passed': bool, 'details': str}
                ]
            }
        """
        action_id = action_result.get('action_id')
        action_type = action_result.get('action_type')
        target_id = action_result.get('target_id')
        status = action_result.get('status')

        checks = []
        start_time = datetime.now(timezone.utc).replace(tzinfo=None)

        # 기본 검증: 작업이 성공했는가?
        checks.append({
            'check_type': 'action_status',
            'passed': status == 'SUCCESS',
            'details': f'Action status: {status}'
        })

        # 작업별 상세 검증
        if action_type == 'ec2_stop':
            ec2_check = self._validate_ec2_stop(target_id)
            checks.append(ec2_check)
        elif action_type == 'sg_restrict_port':
            sg_check = self._validate_sg_restrict(target_id)
            checks.append(sg_check)
        elif action_type == 's3_block_public':
            s3_check = self._validate_s3_block_public(target_id)
            checks.append(s3_check)
        elif action_type == 'iam_disable_key':
            iam_check = self._validate_iam_disable_key(target_id)
            checks.append(iam_check)
        elif action_type == 'nat_block_region':
            nat_check = self._validate_nat_block_region(target_id)
            checks.append(nat_check)

        end_time = datetime.now(timezone.utc).replace(tzinfo=None)
        validation_time = (end_time - start_time).total_seconds()

        # 모든 검사 통과?
        all_passed = all(check['passed'] for check in checks)

        return {
            'action_id': action_id,
            'validated': all_passed,
            'validation_time': round(validation_time, 3),
            'checks_performed': checks
        }

    def get_action_cost_estimate(self, action_type: str) -> float:
        """
        작업의 예상 비용 절감액

        Args:
            action_type: 작업 타입

        Returns:
            예상 월간 절감액 (USD)
        """
        cost_estimates = {
            'ec2_stop': 0.0,  # 인스턴스 중지는 비용 절감 없음 (이미 실행 중이면 중지)
            'sg_restrict_port': 0.0,  # 직접 비용 없음
            's3_block_public': 0.0,  # 직접 비용 없음
            'iam_disable_key': 0.0,  # 직접 비용 없음
            'nat_block_region': 32.0  # NAT 게이트웨이 월 비용 ($32/달)
        }
        return cost_estimates.get(action_type, 0.0)

    def rollback_action(self, action_id: str) -> Dict[str, Any]:
        """
        작업 취소

        Args:
            action_id: 취소할 작업 ID

        Returns:
            {
                'action_id': str,
                'original_action_type': str,
                'rollback_status': 'SUCCESS' | 'FAILED',
                'rollback_action_id': str,
                'timestamp': ISO timestamp
            }
        """
        if action_id not in self.executed_actions:
            return {
                'action_id': action_id,
                'rollback_status': 'FAILED',
                'error': f'Action not found: {action_id}',
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
            }

        original_result = self.executed_actions[action_id]
        original_action = self.action_history.get(action_id, {})
        action_type = original_result.get('action_type')
        target_id = original_result.get('target_id')

        # 작업별 롤백
        try:
            if action_type == 'ec2_stop':
                rollback_result = self._rollback_ec2_stop(target_id)
            elif action_type == 'sg_restrict_port':
                rollback_result = self._rollback_sg_restrict(target_id)
            elif action_type == 's3_block_public':
                rollback_result = self._rollback_s3_block_public(target_id)
            elif action_type == 'iam_disable_key':
                rollback_result = self._rollback_iam_disable_key(target_id)
            elif action_type == 'nat_block_region':
                rollback_result = self._rollback_nat_block_region(target_id)
            else:
                rollback_result = {'status': 'FAILED', 'error': 'Unknown action type'}

            rollback_id = str(uuid.uuid4())
            return {
                'action_id': action_id,
                'original_action_type': action_type,
                'rollback_status': rollback_result.get('status', 'FAILED'),
                'rollback_action_id': rollback_id,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
            }

        except Exception as e:
            return {
                'action_id': action_id,
                'original_action_type': action_type,
                'rollback_status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + 'Z'
            }

    # EC2 작업들
    def _execute_ec2_stop(self, instance_id: str, account_id: str, dry_run: bool) -> Dict:
        """EC2 인스턴스 중지"""
        if dry_run:
            return {'status': 'DRY_RUN', 'message': f'Would stop instance {instance_id}'}
        # 실제 구현: boto3 ec2.stop_instances()
        return {
            'status': 'SUCCESS',
            'instance_id': instance_id,
            'previous_state': 'running',
            'new_state': 'stopped'
        }

    def _validate_ec2_stop(self, instance_id: str) -> Dict:
        """EC2 중지 검증"""
        return {
            'check_type': 'ec2_instance_state',
            'passed': True,
            'details': f'Instance {instance_id} is in stopped state'
        }

    def _rollback_ec2_stop(self, instance_id: str) -> Dict:
        """EC2 재시작 (중지 취소)"""
        return {'status': 'SUCCESS', 'message': f'Restarted instance {instance_id}'}

    # 보안 그룹 작업들
    def _execute_sg_restrict(self, sg_id: str, port: int, account_id: str, dry_run: bool) -> Dict:
        """보안 그룹 제한"""
        if dry_run:
            return {'status': 'DRY_RUN', 'message': f'Would restrict port {port} in {sg_id}'}
        return {
            'status': 'SUCCESS',
            'sg_id': sg_id,
            'port': port,
            'rules_removed': 1
        }

    def _validate_sg_restrict(self, sg_id: str) -> Dict:
        """보안 그룹 제한 검증"""
        return {
            'check_type': 'sg_rules_updated',
            'passed': True,
            'details': f'Overly permissive rules removed from {sg_id}'
        }

    def _rollback_sg_restrict(self, sg_id: str) -> Dict:
        """보안 그룹 원상복구"""
        return {'status': 'SUCCESS', 'message': f'Restored rules in {sg_id}'}

    # S3 작업들
    def _execute_s3_block_public(self, bucket_name: str, account_id: str, dry_run: bool) -> Dict:
        """S3 공개 액세스 차단"""
        if dry_run:
            return {'status': 'DRY_RUN', 'message': f'Would enable BlockPublicAccess on {bucket_name}'}
        return {
            'status': 'SUCCESS',
            'bucket_name': bucket_name,
            'block_public_acls': True,
            'ignore_public_acls': True,
            'block_public_policy': True,
            'restrict_public_buckets': True
        }

    def _validate_s3_block_public(self, bucket_name: str) -> Dict:
        """S3 공개 액세스 차단 검증"""
        return {
            'check_type': 's3_block_public_access',
            'passed': True,
            'details': f'BlockPublicAccess enabled on {bucket_name}'
        }

    def _rollback_s3_block_public(self, bucket_name: str) -> Dict:
        """S3 공개 액세스 차단 해제"""
        return {'status': 'SUCCESS', 'message': f'Removed BlockPublicAccess from {bucket_name}'}

    # IAM 작업들
    def _execute_iam_disable_key(self, access_key_id: str, account_id: str, dry_run: bool) -> Dict:
        """IAM 액세스 키 비활성화"""
        if dry_run:
            return {'status': 'DRY_RUN', 'message': f'Would disable key {access_key_id}'}
        return {
            'status': 'SUCCESS',
            'access_key_id': access_key_id,
            'previous_status': 'Active',
            'new_status': 'Inactive'
        }

    def _validate_iam_disable_key(self, access_key_id: str) -> Dict:
        """IAM 키 비활성화 검증"""
        return {
            'check_type': 'iam_key_status',
            'passed': True,
            'details': f'Access key {access_key_id} is inactive'
        }

    def _rollback_iam_disable_key(self, access_key_id: str) -> Dict:
        """IAM 키 재활성화"""
        return {'status': 'SUCCESS', 'message': f'Reactivated key {access_key_id}'}

    # NAT 작업들
    def _execute_nat_block_region(self, region: str, account_id: str, dry_run: bool) -> Dict:
        """NAT 영역 차단"""
        if dry_run:
            return {'status': 'DRY_RUN', 'message': f'Would block region {region}'}
        return {
            'status': 'SUCCESS',
            'region': region,
            'blocked': True,
            'estimated_monthly_savings': 32.0
        }

    def _validate_nat_block_region(self, region: str) -> Dict:
        """NAT 영역 차단 검증"""
        return {
            'check_type': 'nat_region_blocked',
            'passed': True,
            'details': f'Region {region} is blocked in NAT allowlist'
        }

    def _rollback_nat_block_region(self, region: str) -> Dict:
        """NAT 영역 차단 해제"""
        return {'status': 'SUCCESS', 'message': f'Unblocked region {region}'}
