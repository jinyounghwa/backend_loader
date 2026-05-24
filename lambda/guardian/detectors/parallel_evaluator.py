import asyncio
import logging
import time
from typing import List, Dict, Any, Callable, Coroutine
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvaluationTask:
    """병렬 평가 작업"""
    threat: Any
    rule: Dict[str, Any]
    detector: Any

    async def execute(self) -> Dict[str, Any]:
        """
        규칙 평가 실행 (비동기)

        Returns:
            평가 결과 (threat_id, rule_id, matched)
        """
        try:
            result = await asyncio.to_thread(
                self._evaluate_rule_sync,
                self.threat,
                self.rule
            )
            return {
                'threat_id': self.threat.threat_id,
                'rule_id': self.rule.get('rule_id'),
                'matched': result,
                'error': None
            }
        except Exception as e:
            logger.error(f"Evaluation failed for threat {self.threat.threat_id}: {str(e)}")
            return {
                'threat_id': self.threat.threat_id,
                'rule_id': self.rule.get('rule_id'),
                'matched': False,
                'error': str(e)
            }

    @staticmethod
    def _evaluate_rule_sync(threat: Any, rule: Dict[str, Any]) -> bool:
        """규칙 평가 (동기)"""
        return threat.severity >= rule.get('priority', 0)


@dataclass
class ParallelEvaluationResult:
    """병렬 평가 결과"""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    matched_threats: int
    execution_time_ms: float
    throughput_tasks_per_sec: float


class ParallelEvaluator:
    """
    병렬 규칙 평가 엔진 (asyncio 기반)

    특징:
    - asyncio를 사용한 비동기 병렬 처리
    - 대량의 위협/규칙 조합 효율적 평가
    - 작업 배치 처리 (배치 크기 설정 가능)
    - 상세한 성능 메트릭
    """

    def __init__(self, max_concurrent_tasks: int = 10, batch_size: int = 100):
        """
        Args:
            max_concurrent_tasks: 동시 실행 작업 수 (기본 10)
            batch_size: 배치 크기 (기본 100)
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def evaluate_rules_parallel(
        self,
        threats: List[Any],
        rules: List[Dict[str, Any]]
    ) -> ParallelEvaluationResult:
        """
        위협 목록에 대해 규칙을 병렬로 평가

        Args:
            threats: 위협 목록
            rules: 규칙 목록

        Returns:
            ParallelEvaluationResult: 평가 결과
        """
        start_time = time.time()

        if not threats or not rules:
            return ParallelEvaluationResult(
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                matched_threats=0,
                execution_time_ms=0,
                throughput_tasks_per_sec=0
            )

        # 모든 평가 작업 생성
        tasks = []
        for threat in threats:
            for rule in rules:
                task = EvaluationTask(threat=threat, rule=rule, detector=None)
                tasks.append(task.execute())

        logger.info(f"Starting parallel evaluation: {len(tasks)} tasks")

        # 배치 단위로 작업 실행
        completed = 0
        failed = 0
        matched = 0

        for batch_idx in range(0, len(tasks), self.batch_size):
            batch = tasks[batch_idx : batch_idx + self.batch_size]
            logger.debug(f"Processing batch {batch_idx // self.batch_size + 1}: {len(batch)} tasks")

            try:
                results = await asyncio.gather(*batch, return_exceptions=True)

                for result in results:
                    completed += 1
                    if isinstance(result, Exception):
                        failed += 1
                        logger.warning(f"Task failed with exception: {result}")
                    elif isinstance(result, dict):
                        if result.get('error'):
                            failed += 1
                        elif result.get('matched'):
                            matched += 1

            except Exception as e:
                logger.error(f"Batch execution failed: {str(e)}")
                failed += len(batch)

        elapsed_ms = (time.time() - start_time) * 1000
        throughput = (len(tasks) / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0

        result = ParallelEvaluationResult(
            total_tasks=len(tasks),
            completed_tasks=completed,
            failed_tasks=failed,
            matched_threats=matched,
            execution_time_ms=elapsed_ms,
            throughput_tasks_per_sec=throughput
        )

        logger.info(
            f"Parallel evaluation complete: {completed}/{len(tasks)} tasks, "
            f"{matched} matched, {failed} failed, {elapsed_ms:.1f}ms, "
            f"{throughput:.1f} tasks/sec"
        )

        return result

    async def evaluate_threats_with_rules_batch(
        self,
        threats: List[Any],
        rules: List[Dict[str, Any]],
        filter_func: Callable[[Any, Dict[str, Any]], bool] = None
    ) -> List[Dict[str, Any]]:
        """
        위협별 규칙 평가 (필터 함수 지원)

        Args:
            threats: 위협 목록
            rules: 규칙 목록
            filter_func: 커스텀 필터 함수 (기본: severity >= priority)

        Returns:
            일치하는 위협/규칙 쌍 목록
        """
        matched_pairs = []

        async def evaluate_with_filter(threat, rule):
            try:
                # 커스텀 필터 또는 기본 필터 사용
                if filter_func:
                    matched = await asyncio.to_thread(filter_func, threat, rule)
                else:
                    matched = threat.severity >= rule.get('priority', 0)

                if matched:
                    return {
                        'threat_id': threat.threat_id,
                        'threat_severity': threat.severity,
                        'rule_id': rule.get('rule_id'),
                        'rule_priority': rule.get('priority', 0)
                    }
                return None

            except Exception as e:
                logger.error(f"Evaluation error for threat {threat.threat_id}: {str(e)}")
                return None

        # 작업 생성 및 실행
        tasks = [
            evaluate_with_filter(threat, rule)
            for threat in threats
            for rule in rules
        ]

        if not tasks:
            return matched_pairs

        logger.info(f"Evaluating {len(tasks)} threat/rule combinations")

        # 배치 처리
        for batch_idx in range(0, len(tasks), self.batch_size):
            batch = tasks[batch_idx : batch_idx + self.batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, dict) and result is not None:
                    matched_pairs.append(result)

        logger.info(f"Found {len(matched_pairs)} matching threat/rule pairs")
        return matched_pairs

    def run_evaluation_async(
        self,
        threats: List[Any],
        rules: List[Dict[str, Any]]
    ) -> ParallelEvaluationResult:
        """
        비동기 평가를 동기 컨텍스트에서 실행

        Lambda 환경에서 asyncio를 사용하기 위한 헬퍼 메서드

        Args:
            threats: 위협 목록
            rules: 규칙 목록

        Returns:
            ParallelEvaluationResult: 평가 결과
        """
        try:
            # 이미 실행 중인 이벤트 루프가 있으면 사용
            loop = asyncio.get_running_loop()
            # Lambda에서는 usually 새로운 루프가 없으므로 여기서는 실행되지 않음
        except RuntimeError:
            # 새로운 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                self.evaluate_rules_parallel(threats, rules)
            )
            return result
        finally:
            loop.close()

    def set_max_concurrent_tasks(self, max_tasks: int):
        """최대 동시 작업 수 변경"""
        self.max_concurrent_tasks = max_tasks
        self.semaphore = asyncio.Semaphore(max_tasks)
        logger.info(f"Max concurrent tasks set to {max_tasks}")

    def set_batch_size(self, batch_size: int):
        """배치 크기 변경"""
        self.batch_size = batch_size
        logger.info(f"Batch size set to {batch_size}")
