from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


class PlaybookOrchestrator:
    """복잡한 플레이북 조율 (순차/병렬 작업)"""

    def __init__(self, action_executor: Optional["ActionExecutor"] = None):
        """초기화"""
        from guardian.ml.action_executor import ActionExecutor
        self.action_executor = action_executor or ActionExecutor()
        self.playbook_executions: Dict[str, Dict[str, Any]] = {}

    def execute_playbook(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        """
        플레이북 실행

        Args:
            playbook: {
                'playbook_id': str,
                'threat_id': str,
                'threat_type': str,
                'actions': [
                    {
                        'action_id': str,
                        'action_type': str,
                        'target_id': str,
                        'parameters': dict,
                        'depends_on': [str] (optional),
                        'parallel_with': [str] (optional)
                    }
                ],
                'account_id': str,
                'dry_run': bool (optional)
            }

        Returns:
            {
                'execution_id': UUID,
                'playbook_id': str,
                'status': 'COMPLETED' | 'PARTIAL' | 'FAILED',
                'actions_executed': int,
                'actions_succeeded': int,
                'actions_failed': int,
                'execution_time_seconds': float,
                'action_results': [...]
            }
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        playbook_id = playbook.get('playbook_id')
        actions = playbook.get('actions', [])
        dry_run = playbook.get('dry_run', False)

        # 작업 그래프 구성
        action_graph = self._build_action_graph(actions)

        # 작업 실행 (위상 정렬 순서)
        executed_actions = {}
        failed_actions = {}
        action_results = []

        for action_spec in action_graph:
            action_id = action_spec.get('action_id')

            # 의존성 확인
            depends_on = action_spec.get('depends_on', [])
            if any(dep in failed_actions for dep in depends_on):
                # 의존성 작업이 실패했으면 이 작업은 스킵
                failed_actions[action_id] = {'error': 'Dependency failed'}
                action_results.append({
                    'action_id': action_id,
                    'status': 'SKIPPED',
                    'reason': 'Dependency failed'
                })
                continue

            # 작업 실행
            try:
                result = self.action_executor.execute_action(action_spec)
                result['dry_run'] = dry_run

                if result.get('status') == 'SUCCESS':
                    executed_actions[action_id] = result
                else:
                    failed_actions[action_id] = result

                action_results.append(result)
            except Exception as e:
                failed_actions[action_id] = {'error': str(e)}
                action_results.append({
                    'action_id': action_id,
                    'status': 'FAILED',
                    'error': str(e)
                })

        # 실행 결과 집계
        total_actions = len(actions)
        succeeded = len(executed_actions)
        failed = len(failed_actions)

        # 상태 결정
        if failed == 0:
            status = 'COMPLETED'
        elif succeeded > 0:
            status = 'PARTIAL'
        else:
            status = 'FAILED'

        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        execution_record = {
            'execution_id': execution_id,
            'playbook_id': playbook_id,
            'status': status,
            'actions_executed': total_actions,
            'actions_succeeded': succeeded,
            'actions_failed': failed,
            'execution_time_seconds': round(execution_time, 2),
            'action_results': action_results,
            'timestamp': end_time.isoformat() + 'Z'
        }

        self.playbook_executions[execution_id] = execution_record
        return execution_record

    def _build_action_graph(self, actions: List[Dict]) -> List[Dict]:
        """
        작업 그래프 구성 (위상 정렬)

        Args:
            actions: 작업 목록

        Returns:
            위상 정렬된 작업 목록
        """
        # 간단한 위상 정렬 (의존성 없는 작업 먼저)
        sorted_actions = []
        processed = set()

        def process_action(action):
            action_id = action.get('action_id')
            if action_id in processed:
                return

            depends_on = action.get('depends_on', [])
            for dep_id in depends_on:
                # 의존성 작업 먼저 처리
                for a in actions:
                    if a.get('action_id') == dep_id:
                        process_action(a)
                        break

            sorted_actions.append(action)
            processed.add(action_id)

        for action in actions:
            process_action(action)

        return sorted_actions

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        플레이북 실행 상태 조회

        Args:
            execution_id: 실행 ID

        Returns:
            실행 기록 또는 None
        """
        return self.playbook_executions.get(execution_id)

    def get_execution_summary(self, execution_id: str) -> Dict[str, Any]:
        """
        플레이북 실행 요약

        Args:
            execution_id: 실행 ID

        Returns:
            {
                'execution_id': str,
                'status': str,
                'total_actions': int,
                'success_rate': float,
                'execution_time_seconds': float
            }
        """
        execution = self.playbook_executions.get(execution_id)
        if not execution:
            return {
                'execution_id': execution_id,
                'status': 'NOT_FOUND',
                'total_actions': 0,
                'success_rate': 0.0
            }

        total = execution.get('actions_executed', 0)
        succeeded = execution.get('actions_succeeded', 0)
        success_rate = (succeeded / total) if total > 0 else 0.0

        return {
            'execution_id': execution_id,
            'status': execution.get('status'),
            'total_actions': total,
            'success_rate': round(success_rate, 3),
            'execution_time_seconds': execution.get('execution_time_seconds', 0)
        }

    def estimate_playbook_cost(self, playbook: Dict[str, Any]) -> float:
        """
        플레이북 예상 비용 절감액

        Args:
            playbook: 플레이북 정의

        Returns:
            예상 월간 절감액 (USD)
        """
        actions = playbook.get('actions', [])
        total_cost = 0.0

        for action in actions:
            action_type = action.get('action_type')
            cost = self.action_executor.get_action_cost_estimate(action_type)
            total_cost += cost

        return round(total_cost, 2)

    def get_parallel_actions(self, playbook: Dict[str, Any]) -> List[List[str]]:
        """
        병렬 실행 가능한 작업 그룹

        Args:
            playbook: 플레이북 정의

        Returns:
            [['action_id1', 'action_id2'], ['action_id3']]
        """
        actions = playbook.get('actions', [])
        action_dict = {a.get('action_id'): a for a in actions}

        # 병렬 그룹 계산
        parallel_groups = []
        processed = set()

        for action in actions:
            action_id = action.get('action_id')
            if action_id in processed:
                continue

            # 이 작업과 병렬 실행 가능한 작업들
            group = [action_id]
            for other_action in actions:
                other_id = other_action.get('action_id')
                if other_id in processed or other_id == action_id:
                    continue

                # 의존성 확인
                depends_on = other_action.get('depends_on', [])
                if not any(dep in group for dep in depends_on):
                    group.append(other_id)

            parallel_groups.append(group)
            processed.update(group)

        return parallel_groups
