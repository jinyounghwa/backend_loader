from typing import Dict, Any, List, Optional
from datetime import datetime


class AuditLogger:
    """실행 작업 감사 로깅"""

    def __init__(self):
        """초기화"""
        self.audit_logs: Dict[str, Dict[str, Any]] = {}

    def log_action_execution(self, action_result: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """
        작업 실행 로깅

        Args:
            action_result: execute_action() 결과
            metadata: {
                'user_id': str (optional),
                'request_id': str (optional),
                'ip_address': str (optional),
                'playbook_id': str,
                'threat_id': str
            }

        Returns:
            로그 ID
        """
        log_id = action_result.get('action_id', '')
        log_entry = {
            'log_id': log_id,
            'action_id': action_result.get('action_id'),
            'action_type': action_result.get('action_type'),
            'target_id': action_result.get('target_id'),
            'status': action_result.get('status'),
            'timestamp': action_result.get('timestamp'),
            'user_id': metadata.get('user_id'),
            'playbook_id': metadata.get('playbook_id'),
            'threat_id': metadata.get('threat_id'),
            'ip_address': metadata.get('ip_address'),
            'error': action_result.get('error')
        }
        self.audit_logs[log_id] = log_entry
        return log_id

    def log_playbook_execution(self, execution_result: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """
        플레이북 실행 로깅

        Args:
            execution_result: execute_playbook() 결과
            metadata: 메타데이터

        Returns:
            로그 ID
        """
        log_id = execution_result.get('execution_id', '')
        log_entry = {
            'log_id': log_id,
            'execution_id': execution_result.get('execution_id'),
            'playbook_id': execution_result.get('playbook_id'),
            'status': execution_result.get('status'),
            'actions_executed': execution_result.get('actions_executed'),
            'actions_succeeded': execution_result.get('actions_succeeded'),
            'actions_failed': execution_result.get('actions_failed'),
            'timestamp': execution_result.get('timestamp'),
            'user_id': metadata.get('user_id'),
            'threat_id': metadata.get('threat_id')
        }
        self.audit_logs[log_id] = log_entry
        return log_id

    def get_audit_trail(self, playbook_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        플레이북 감사 추적

        Args:
            playbook_id: 플레이북 ID
            days: 조회 기간

        Returns:
            감사 로그 리스트
        """
        results = []
        for log in self.audit_logs.values():
            if log.get('playbook_id') == playbook_id:
                results.append(log)
        return sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)

    def get_threat_response_history(self, threat_id: str) -> List[Dict[str, Any]]:
        """
        위협별 대응 이력

        Args:
            threat_id: 위협 ID

        Returns:
            대응 로그 리스트
        """
        results = []
        for log in self.audit_logs.values():
            if log.get('threat_id') == threat_id:
                results.append(log)
        return sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)

    def get_action_statistics(self, action_type: str, days: int = 7) -> Dict[str, Any]:
        """
        작업 통계

        Args:
            action_type: 작업 타입
            days: 조회 기간

        Returns:
            {
                'action_type': str,
                'total_executions': int,
                'successful': int,
                'failed': int,
                'success_rate': float,
                'most_common_target': str
            }
        """
        executions = [
            log for log in self.audit_logs.values()
            if log.get('action_type') == action_type
        ]

        if not executions:
            return {
                'action_type': action_type,
                'total_executions': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0
            }

        total = len(executions)
        successful = sum(1 for e in executions if e.get('status') == 'SUCCESS')
        failed = total - successful
        success_rate = (successful / total) if total > 0 else 0.0

        # 가장 자주 대상이 되는 리소스
        target_counts = {}
        for e in executions:
            target = e.get('target_id', 'unknown')
            target_counts[target] = target_counts.get(target, 0) + 1

        most_common = max(target_counts.items(), key=lambda x: x[1])[0] if target_counts else None

        return {
            'action_type': action_type,
            'total_executions': total,
            'successful': successful,
            'failed': failed,
            'success_rate': round(success_rate, 3),
            'most_common_target': most_common
        }
