from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class ExecutionMetricsCollector:
    """Playbook 실행 메트릭 수집 및 집계"""

    def __init__(self, storage: Optional["ExecutionResultsStorage"] = None):
        """
        초기화

        Args:
            storage: ExecutionResultsStorage 인스턴스 (DynamoDB 접근)
        """
        self.storage = storage or ExecutionResultsStorage()

    def record_execution_result(self, execution_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Playbook 실행 결과 기록

        Args:
            execution_record: {
                'execution_id': UUID,
                'playbook_id': str,
                'threat_id': str,
                'threat_type': str,
                'account_id': str,
                'status': 'COMPLETED' | 'FAILED',
                'started_at': ISO timestamp,
                'completed_at': ISO timestamp,
                'actions_executed': list[dict],
                'actions_failed': list[dict]
            }

        Returns:
            저장된 기록 (duration, success 필드 추가)
        """
        # 실행 시간 계산
        started = datetime.fromisoformat(execution_record['started_at'].replace('Z', '+00:00'))
        completed = datetime.fromisoformat(execution_record['completed_at'].replace('Z', '+00:00'))
        duration_seconds = (completed - started).total_seconds()

        # 성공 여부 판단
        success = (
            execution_record.get('status') == 'COMPLETED'
            and len(execution_record.get('actions_failed', [])) == 0
        )

        # 메트릭 계산
        record_with_metrics = {
            **execution_record,
            'duration_seconds': duration_seconds,
            'success': success,
            'action_count': len(execution_record.get('actions_executed', [])),
            'success_count': len(execution_record.get('actions_executed', [])),
            'failure_count': len(execution_record.get('actions_failed', []))
        }

        # DynamoDB에 저장
        self.storage.save_execution(record_with_metrics)
        return record_with_metrics

    def get_execution_history(
        self, playbook_id: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Playbook의 실행 이력 조회

        Args:
            playbook_id: Playbook ID
            days: 조회 기간 (일)

        Returns:
            실행 기록 리스트
        """
        end_time = datetime.utcnow().isoformat() + 'Z'
        start_time = (datetime.utcnow() - timedelta(days=days)).isoformat() + 'Z'

        return self.storage.query_by_playbook(playbook_id, start_time, end_time)

    def calculate_execution_metrics(
        self, execution_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        실행 메트릭 집계

        Args:
            execution_records: 실행 기록 리스트

        Returns:
            {
                'playbook_id': str,
                'total_executions': int,
                'successful': int,
                'failed': int,
                'success_rate': float (0-1),
                'avg_duration_seconds': float,
                'min_duration_seconds': float,
                'max_duration_seconds': float,
                'action_failure_counts': {action_type: count}
            }
        """
        if not execution_records:
            return {
                'total_executions': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'avg_duration_seconds': 0.0,
                'min_duration_seconds': 0.0,
                'max_duration_seconds': 0.0,
                'action_failure_counts': {}
            }

        total = len(execution_records)
        successful = sum(1 for r in execution_records if r.get('success', False))
        failed = total - successful
        success_rate = successful / total if total > 0 else 0.0

        # 실행 시간 통계
        durations = [r.get('duration_seconds', 0) for r in execution_records]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        min_duration = min(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        # Action 실패 패턴
        action_failure_counts = {}
        for record in execution_records:
            for failed_action in record.get('actions_failed', []):
                action_type = failed_action.get('action_type', 'unknown')
                action_failure_counts[action_type] = action_failure_counts.get(action_type, 0) + 1

        playbook_id = execution_records[0].get('playbook_id', 'unknown')

        return {
            'playbook_id': playbook_id,
            'total_executions': total,
            'successful': successful,
            'failed': failed,
            'success_rate': round(success_rate, 3),
            'avg_duration_seconds': round(avg_duration, 2),
            'min_duration_seconds': round(min_duration, 2),
            'max_duration_seconds': round(max_duration, 2),
            'action_failure_counts': action_failure_counts
        }

    def get_threat_type_metrics(
        self, threat_type: str, days: int = 7
    ) -> Dict[str, Any]:
        """
        위협 타입별 메트릭 조회

        Args:
            threat_type: 위협 타입 (e.g., 'Unknown Region')
            days: 조회 기간

        Returns:
            메트릭 딕셔너리 (calculate_execution_metrics 포맷)
        """
        end_time = datetime.utcnow().isoformat() + 'Z'
        start_time = (datetime.utcnow() - timedelta(days=days)).isoformat() + 'Z'

        records = self.storage.query_by_threat_type(threat_type, start_time, end_time)
        return self.calculate_execution_metrics(records)

    def get_playbook_impact_metrics(
        self, playbook_id: str, days: int = 7
    ) -> Dict[str, Any]:
        """
        Playbook의 실제 영향도 메트릭

        Args:
            playbook_id: Playbook ID
            days: 조회 기간

        Returns:
            {
                'playbook_id': str,
                'total_threats_targeted': int,
                'threats_resolved': int,
                'mitigation_rate': float (0-1),
                'total_resources_affected': int,
                'avg_response_time_seconds': float
            }
        """
        execution_history = self.get_execution_history(playbook_id, days)

        if not execution_history:
            return {
                'playbook_id': playbook_id,
                'total_threats_targeted': 0,
                'threats_resolved': 0,
                'mitigation_rate': 0.0,
                'total_resources_affected': 0,
                'avg_response_time_seconds': 0.0
            }

        # 타겟된 위협 수 (고유)
        threat_ids = set(r.get('threat_id') for r in execution_history if r.get('threat_id'))
        total_threats = len(threat_ids)

        # 해결된 위협 (성공한 execution)
        resolved_threat_ids = set(
            r.get('threat_id')
            for r in execution_history
            if r.get('threat_id') and r.get('success', False)
        )
        threats_resolved = len(resolved_threat_ids)

        # 완화율 (resolved / total)
        mitigation_rate = threats_resolved / total_threats if total_threats > 0 else 0.0

        # 영향받은 리소스 (고유 threat_id = 고유 타겟)
        total_resources = total_threats

        # 평균 응답 시간
        durations = [r.get('duration_seconds', 0) for r in execution_history]
        avg_response_time = sum(durations) / len(durations) if durations else 0.0

        return {
            'playbook_id': playbook_id,
            'total_threats_targeted': total_threats,
            'threats_resolved': threats_resolved,
            'mitigation_rate': round(mitigation_rate, 3),
            'total_resources_affected': total_resources,
            'avg_response_time_seconds': round(avg_response_time, 2)
        }


class ExecutionResultsStorage:
    """Execution 결과 DynamoDB 저장소"""

    def __init__(self):
        """초기화"""
        # 실제 구현에서는 DynamoDB 클라이언트 초기화
        # 테스트용으로 메모리 저장소 사용
        self.executions: Dict[str, Dict[str, Any]] = {}

    def save_execution(self, execution_record: Dict[str, Any]) -> bool:
        """
        Execution 결과 저장

        Args:
            execution_record: 저장할 기록

        Returns:
            성공 여부
        """
        execution_id = execution_record.get('execution_id')
        if not execution_id:
            return False

        self.executions[execution_id] = execution_record
        return True

    def query_by_playbook(
        self, playbook_id: str, start_timestamp: str, end_timestamp: str
    ) -> List[Dict[str, Any]]:
        """
        Playbook별 쿼리

        Args:
            playbook_id: Playbook ID
            start_timestamp: 시작 시간 (ISO 포맷)
            end_timestamp: 종료 시간 (ISO 포맷)

        Returns:
            해당 조건의 기록 리스트
        """
        results = []
        for record in self.executions.values():
            if record.get('playbook_id') != playbook_id:
                continue

            # 시간 범위 확인
            record_time = record.get('started_at', '')
            if start_timestamp <= record_time <= end_timestamp:
                results.append(record)

        return results

    def query_by_threat_type(
        self, threat_type: str, start_timestamp: str, end_timestamp: str
    ) -> List[Dict[str, Any]]:
        """
        위협 타입별 쿼리

        Args:
            threat_type: 위협 타입
            start_timestamp: 시작 시간
            end_timestamp: 종료 시간

        Returns:
            해당 조건의 기록 리스트
        """
        results = []
        for record in self.executions.values():
            if record.get('threat_type') != threat_type:
                continue

            # 시간 범위 확인
            record_time = record.get('started_at', '')
            if start_timestamp <= record_time <= end_timestamp:
                results.append(record)

        return results
