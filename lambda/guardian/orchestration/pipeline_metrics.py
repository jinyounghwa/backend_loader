import logging
from typing import Dict, List, Any
from collections import Counter
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PipelineMetrics:
    """파이프라인 실행 메트릭 수집 및 분석"""

    def __init__(self, dynamodb_table):
        """
        Args:
            dynamodb_table: DynamoDB 테이블 (파이프라인 실행 기록 저장)
        """
        self.table = dynamodb_table

    async def record_pipeline_execution(self, execution: Dict[str, Any]) -> None:
        """
        파이프라인 실행 기록 저장

        Args:
            execution: {
                'pipeline_id': str,
                'status': 'HEALTHY' | 'DEGRADED' | 'FAILED',
                'stages': {...},
                'errors': [...],
                'total_threats': int,
                'mitigated_threats': int,
                'end_to_end_latency_ms': float,
                'timestamp': str
            }
        """
        try:
            self.table.put_item(Item=execution)
            logger.debug(f"Recorded pipeline execution: {execution.get('pipeline_id')}")
        except Exception as e:
            logger.error(f"Failed to record pipeline execution: {e}")

    async def get_pipeline_health(self, lookback_minutes: int = 60) -> Dict[str, Any]:
        """
        최근 N분간의 파이프라인 상태 통계

        Args:
            lookback_minutes: 조회 기간 (분)

        Returns:
            {
                'overall_status': str,
                'total_executions': int,
                'successful_executions': int,
                'degraded_executions': int,
                'failed_executions': int,
                'success_rate': float,
                'avg_latency_ms': float,
                'stage_success_rates': {
                    'anomaly_detection': float,
                    'prediction': float,
                    ...
                },
                'error_summary': {...}
            }
        """
        try:
            # 최근 기록 조회
            executions = await self._query_recent_executions(lookback_minutes)

            if not executions:
                return {
                    'overall_status': 'UNKNOWN',
                    'total_executions': 0,
                    'successful_executions': 0,
                    'degraded_executions': 0,
                    'failed_executions': 0,
                    'success_rate': 0.0,
                    'avg_latency_ms': 0.0,
                    'stage_success_rates': {},
                    'error_summary': {}
                }

            # 통계 계산
            total = len(executions)
            successful = sum(1 for e in executions if e['status'] == 'HEALTHY')
            degraded = sum(1 for e in executions if e['status'] == 'DEGRADED')
            failed = sum(1 for e in executions if e['status'] == 'FAILED')

            avg_latency = sum(e.get('end_to_end_latency_ms', 0) for e in executions) / total if total > 0 else 0

            return {
                'overall_status': self._determine_overall_status(successful, degraded, failed, total),
                'total_executions': total,
                'successful_executions': successful,
                'degraded_executions': degraded,
                'failed_executions': failed,
                'success_rate': successful / total if total > 0 else 0,
                'avg_latency_ms': round(avg_latency, 2),
                'stage_success_rates': self._calculate_stage_success_rates(executions),
                'error_summary': self._summarize_errors(executions)
            }

        except Exception as e:
            logger.error(f"Failed to get pipeline health: {e}")
            return {
                'overall_status': 'ERROR',
                'error': str(e)
            }

    async def get_stage_metrics(self, stage_name: str, lookback_minutes: int = 60) -> Dict[str, Any]:
        """
        특정 단계의 메트릭

        Returns:
            {
                'stage_name': str,
                'total_executions': int,
                'successful_executions': int,
                'failed_executions': int,
                'success_rate': float,
                'avg_latency_ms': float,
                'errors': [str]
            }
        """
        try:
            executions = await self._query_recent_executions(lookback_minutes)

            stage_results = []
            for execution in executions:
                if stage_name in execution.get('stages', {}):
                    stage_results.append(execution['stages'][stage_name])

            if not stage_results:
                return {
                    'stage_name': stage_name,
                    'total_executions': 0,
                    'successful_executions': 0,
                    'failed_executions': 0,
                    'success_rate': 0.0,
                    'avg_latency_ms': 0.0,
                    'errors': []
                }

            total = len(stage_results)
            successful = sum(1 for r in stage_results if r.get('status') == 'SUCCESS')
            failed = sum(1 for r in stage_results if r.get('status') == 'FAILED')
            avg_latency = sum(r.get('latency_ms', 0) for r in stage_results) / total

            return {
                'stage_name': stage_name,
                'total_executions': total,
                'successful_executions': successful,
                'failed_executions': failed,
                'success_rate': successful / total if total > 0 else 0,
                'avg_latency_ms': round(avg_latency, 2),
                'errors': [r.get('error', '') for r in stage_results if r.get('status') == 'FAILED']
            }

        except Exception as e:
            logger.error(f"Failed to get stage metrics: {e}")
            return {'stage_name': stage_name, 'error': str(e)}

    def _determine_overall_status(self, successful: int, degraded: int, failed: int, total: int) -> str:
        """전체 상태 결정"""
        if total == 0:
            return 'UNKNOWN'

        success_rate = successful / total

        if success_rate >= 0.95:
            return 'HEALTHY'
        elif success_rate >= 0.75:
            return 'DEGRADED'
        else:
            return 'FAILED'

    def _calculate_stage_success_rates(self, executions: List[Dict]) -> Dict[str, float]:
        """단계별 성공률"""
        stage_stats = {}

        for execution in executions:
            stages = execution.get('stages', {})
            for stage_name, result in stages.items():
                if stage_name not in stage_stats:
                    stage_stats[stage_name] = {'total': 0, 'successful': 0}

                stage_stats[stage_name]['total'] += 1
                if result.get('status') == 'SUCCESS':
                    stage_stats[stage_name]['successful'] += 1

        return {
            stage: (stats['successful'] / stats['total'] if stats['total'] > 0 else 0)
            for stage, stats in stage_stats.items()
        }

    def _summarize_errors(self, executions: List[Dict]) -> Dict[str, int]:
        """에러 요약"""
        all_errors = []
        for execution in executions:
            all_errors.extend(execution.get('errors', []))

        return dict(Counter(all_errors))

    async def _query_recent_executions(self, lookback_minutes: int) -> List[Dict]:
        """최근 실행 기록 조회"""
        # 실제 구현에서는 DynamoDB 조회
        # 여기서는 모의 구현
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=lookback_minutes)
            # self.table.query(...)
            return []
        except Exception as e:
            logger.error(f"Failed to query recent executions: {e}")
            return []

    async def detect_anomaly(self, execution: Dict[str, Any]) -> bool:
        """
        파이프라인 실행에서 이상 탐지

        Rules:
        - 성공률 급락 (50% 이상 감소)
        - 지연 시간 급증 (2배 이상)
        - 특정 단계 계속 실패
        """
        # 향후 구현: 통계 기반 이상 탐지
        return False
