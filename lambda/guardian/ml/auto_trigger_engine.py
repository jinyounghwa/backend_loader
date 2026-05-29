from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta, timezone


class AutoTriggerEngine:
    """ML 예측 결과 → Playbook 자동 실행 판단"""

    def __init__(self):
        """초기화"""
        self.last_execution_time: Dict[str, datetime] = {}

    def should_auto_execute(self, playbook: Dict[str, Any]) -> bool:
        """
        Playbook의 auto_execute 플래그 확인

        Args:
            playbook: Playbook 딕셔너리 (auto_execute 필드 포함)

        Returns:
            bool: auto_execute=True이면 True, 아니면 False
        """
        return playbook.get('auto_execute', False)

    def should_trigger_immediately(
        self, playbook: Dict[str, Any], prediction: Dict[str, Any]
    ) -> bool:
        """
        Playbook이 즉시 실행되어야 하는지 판단

        Args:
            playbook: Playbook 딕셔너리 (신뢰도/심각도 임계값 포함)
            prediction: 원본 위협 예측 (confidence, severity)

        Returns:
            bool: 모든 조건 충족하면 True (auto_execute=True AND 임계값 충족)
        """
        # auto_execute 플래그 확인
        if not self.should_auto_execute(playbook):
            return False

        # 신뢰도 임계값 확인
        confidence = prediction.get('confidence', 0.0)
        confidence_threshold = playbook.get('confidence_threshold', 1.0)
        if confidence < confidence_threshold:
            return False

        # 심각도 임계값 확인
        severity = prediction.get('severity', 0)
        severity_threshold = playbook.get('severity_threshold', 10)
        if severity < severity_threshold:
            return False

        return True

    def separate_playbooks(
        self, recommended_playbooks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Playbook을 자동 실행 vs 수동 승인으로 분류

        Args:
            recommended_playbooks: ResponseMapper의 recommended_playbooks 리스트

        Returns:
            Tuple: (auto_execute_playbooks, manual_approval_playbooks)
        """
        auto_playbooks = []
        manual_playbooks = []

        for playbook in recommended_playbooks:
            if self.should_auto_execute(playbook):
                auto_playbooks.append(playbook)
            else:
                manual_playbooks.append(playbook)

        return auto_playbooks, manual_playbooks

    def create_execution_queue(
        self, auto_playbooks: List[Dict[str, Any]]
    ) -> "ExecutionQueue":
        """
        자동 실행 Playbook으로 실행 큐 생성

        Args:
            auto_playbooks: auto_execute=True인 Playbook 리스트

        Returns:
            ExecutionQueue: 우선순위 순서로 정렬된 실행 큐
        """
        queue = ExecutionQueue()
        for playbook in auto_playbooks:
            queue.enqueue(playbook)
        return queue

    def can_execute_now(self, playbook_id: str) -> bool:
        """
        Playbook을 지금 실행할 수 있는지 확인 (스로틀링)

        Args:
            playbook_id: Playbook ID

        Returns:
            bool: 실행 가능하면 True, 5초 내 실행했으면 False
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        last_exec = self.last_execution_time.get(playbook_id)

        # 처음 실행이거나 5초 이상 지났으면 실행 가능
        if last_exec is None:
            self.last_execution_time[playbook_id] = now
            return True

        # 5초 이내에 실행했으면 스로틀링
        elapsed = (now - last_exec).total_seconds()
        if elapsed < 5.0:
            return False

        # 5초 이상 지났으면 업데이트 후 실행
        self.last_execution_time[playbook_id] = now
        return True

    def reset_throttle(self, playbook_id: str) -> None:
        """
        Playbook의 스로틀링 상태 초기화 (테스트용)

        Args:
            playbook_id: Playbook ID
        """
        self.last_execution_time.pop(playbook_id, None)


class ExecutionQueue:
    """Playbook 실행 대기열 (우선순위 기반)"""

    def __init__(self):
        """초기화"""
        self.queue: List[Dict[str, Any]] = []

    def enqueue(self, playbook: Dict[str, Any]) -> None:
        """
        Playbook을 큐에 추가

        Args:
            playbook: Playbook 딕셔너리
        """
        self.queue.append(playbook)
        # 우선순위(priority)로 정렬 (낮은 숫자가 높은 우선순위)
        self.queue.sort(key=lambda x: (x.get('priority', 10), -x.get('match_score', 0)))

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        큐에서 다음 Playbook 제거 및 반환

        Returns:
            Dict: 다음 실행할 Playbook, 없으면 None
        """
        return self.queue.pop(0) if self.queue else None

    def peek(self) -> Optional[Dict[str, Any]]:
        """
        큐의 다음 Playbook 확인 (제거 없음)

        Returns:
            Dict: 다음 실행할 Playbook, 없으면 None
        """
        return self.queue[0] if self.queue else None

    def is_empty(self) -> bool:
        """
        큐가 비어있는지 확인

        Returns:
            bool: 비어있으면 True
        """
        return len(self.queue) == 0

    def size(self) -> int:
        """
        큐에 남은 Playbook 개수

        Returns:
            int: Playbook 개수
        """
        return len(self.queue)
