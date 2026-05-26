from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class DashboardMetrics:
    """대시보드용 실시간 메트릭"""

    def __init__(self):
        """초기화"""
        self.execution_cache: Dict[str, Dict[str, Any]] = {}

    def register_execution(self, execution_result: Dict[str, Any]) -> None:
        """
        실행 결과 등록 (캐시)

        Args:
            execution_result: execute_playbook() 결과
        """
        execution_id = execution_result.get('execution_id')
        if execution_id:
            self.execution_cache[execution_id] = execution_result

    def get_execution_summary(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        실행 요약 조회

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
        execution = self.execution_cache.get(execution_id)
        if not execution:
            return None

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

    def get_playbook_health(self, playbook_id: str) -> Dict[str, Any]:
        """
        플레이북 상태

        Args:
            playbook_id: 플레이북 ID

        Returns:
            {
                'playbook_id': str,
                'total_executions': int,
                'success_rate': float,
                'avg_execution_time': float,
                'status': 'HEALTHY' | 'DEGRADED' | 'FAILED'
            }
        """
        executions = [
            exec for exec in self.execution_cache.values()
            if exec.get('playbook_id') == playbook_id
        ]

        if not executions:
            return {
                'playbook_id': playbook_id,
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_execution_time': 0.0,
                'status': 'UNKNOWN'
            }

        total = len(executions)
        succeeded = sum(1 for e in executions if e.get('status') == 'COMPLETED')
        success_rate = (succeeded / total) if total > 0 else 0.0

        execution_times = [e.get('execution_time_seconds', 0) for e in executions]
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0.0

        # 상태 결정
        if success_rate == 1.0:
            status = 'HEALTHY'
        elif success_rate >= 0.8:
            status = 'DEGRADED'
        else:
            status = 'FAILED'

        return {
            'playbook_id': playbook_id,
            'total_executions': total,
            'success_rate': round(success_rate, 3),
            'avg_execution_time': round(avg_time, 2),
            'status': status
        }

    def get_threat_response_effectiveness(self, threat_type: str) -> Dict[str, Any]:
        """
        위협 대응 효율성

        Args:
            threat_type: 위협 타입 (optional)

        Returns:
            {
                'threat_type': str,
                'total_detections': int,
                'responses_triggered': int,
                'response_rate': float,
                'avg_resolution_time': float,
                'effectiveness_score': float (0-100)
            }
        """
        # threat_type 필터링으로 관련 실행 찾기
        # 실제 구현에서는 ExecutionMetricsCollector와 통합
        executions = list(self.execution_cache.values())

        if not executions:
            return {
                'threat_type': threat_type,
                'total_detections': 0,
                'responses_triggered': 0,
                'response_rate': 0.0,
                'effectiveness_score': 0.0
            }

        response_rate = len(executions) / max(1, len(executions))
        avg_time = sum(e.get('execution_time_seconds', 0) for e in executions) / len(executions)

        # 효율성 점수 계산 (성공률 기반)
        success_rate = sum(1 for e in executions if e.get('status') == 'COMPLETED') / len(executions)
        effectiveness_score = success_rate * 100

        return {
            'threat_type': threat_type,
            'total_detections': len(executions),
            'responses_triggered': len(executions),
            'response_rate': round(response_rate, 3),
            'avg_resolution_time': round(avg_time, 2),
            'effectiveness_score': round(effectiveness_score, 2)
        }

    def get_system_overview(self) -> Dict[str, Any]:
        """
        시스템 전체 개요

        Returns:
            {
                'total_executions': int,
                'successful_executions': int,
                'failed_executions': int,
                'success_rate': float,
                'total_actions_executed': int,
                'avg_execution_time': float
            }
        """
        executions = list(self.execution_cache.values())

        if not executions:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'success_rate': 0.0,
                'total_actions_executed': 0,
                'avg_execution_time': 0.0
            }

        total = len(executions)
        successful = sum(1 for e in executions if e.get('status') == 'COMPLETED')
        failed = total - successful
        success_rate = (successful / total) if total > 0 else 0.0

        total_actions = sum(e.get('actions_executed', 0) for e in executions)
        execution_times = [e.get('execution_time_seconds', 0) for e in executions]
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0.0

        return {
            'total_executions': total,
            'successful_executions': successful,
            'failed_executions': failed,
            'success_rate': round(success_rate, 3),
            'total_actions_executed': total_actions,
            'avg_execution_time': round(avg_time, 2)
        }

    def get_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        최근 실행 목록

        Args:
            limit: 반환할 최대 개수

        Returns:
            최근 실행 결과 리스트
        """
        executions = sorted(
            self.execution_cache.values(),
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        return executions[:limit]
