"""
우선순위 기반 알림 큐 시스템
CRITICAL → HIGH → MEDIUM → LOW 순서로 처리
"""

from typing import Dict, List, Any, Tuple
import heapq
from datetime import datetime, timezone


class PriorityNotificationQueue:
    """우선순위 기반 알림 큐"""

    PRIORITY_MAP = {
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "LOW": 4
    }

    def __init__(self, max_batch_size: int = 50):
        """
        Args:
            max_batch_size: 최대 배치 크기
        """
        self.queue: List[Tuple[int, int, Dict[str, Any]]] = []
        self.max_batch_size = max_batch_size
        self.total_enqueued = 0
        self.total_dequeued = 0
        self.sequence = 0  # 같은 우선순위에서 FIFO 순서 보장

    def enqueue(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """
        알림을 우선순위에 따라 큐에 추가

        Args:
            notification: 알림 데이터

        Returns:
            큐 상태
        """
        severity = notification.get("severity", "LOW")
        priority = self.PRIORITY_MAP.get(severity, 4)

        heapq.heappush(self.queue, (priority, self.sequence, notification))
        self.sequence += 1
        self.total_enqueued += 1

        return {
            "status": "enqueued",
            "priority": priority,
            "severity": severity,
            "queue_size": len(self.queue)
        }

    def dequeue(self) -> Dict[str, Any] | None:
        """
        우선순위가 가장 높은 알림 추출

        Returns:
            알림 데이터 또는 None
        """
        if not self.queue:
            return None

        _, _, notification = heapq.heappop(self.queue)
        self.total_dequeued += 1
        return notification

    def dequeue_batch(self, size: int | None = None) -> List[Dict[str, Any]]:
        """
        우선순위 순으로 배치 추출

        Args:
            size: 추출 개수 (기본: max_batch_size)

        Returns:
            알림 리스트
        """
        batch_size = size or self.max_batch_size
        batch = []

        for _ in range(min(batch_size, len(self.queue))):
            notification = self.dequeue()
            if notification:
                batch.append(notification)

        return batch

    def peek(self) -> Dict[str, Any] | None:
        """
        큐의 최상위 알림 조회 (제거하지 않음)

        Returns:
            알림 데이터 또는 None
        """
        if not self.queue:
            return None

        return self.queue[0][2]

    def size(self) -> int:
        """큐 크기"""
        return len(self.queue)

    def clear(self) -> None:
        """큐 비우기"""
        self.queue.clear()

    def get_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """
        특정 심각도의 알림 조회

        Args:
            severity: 심각도

        Returns:
            알림 리스트
        """
        target_priority = self.PRIORITY_MAP.get(severity, 4)
        return [
            notif for priority, _, notif in self.queue
            if priority == target_priority
        ]

    def get_stats(self) -> Dict[str, Any]:
        """큐 통계"""
        size_by_severity = {severity: 0 for severity in self.PRIORITY_MAP.keys()}

        for priority, _, notif in self.queue:
            severity = notif.get("severity", "LOW")
            size_by_severity[severity] += 1

        return {
            "total_queued": self.total_enqueued,
            "total_dequeued": self.total_dequeued,
            "current_queue_size": len(self.queue),
            "by_severity": size_by_severity,
            "max_batch_size": self.max_batch_size
        }


# 글로벌 우선순위 큐 인스턴스
_priority_queue = PriorityNotificationQueue(max_batch_size=50)


def enqueue_notification(notification: Dict[str, Any]) -> Dict[str, Any]:
    """알림 큐 추가 (sync)"""
    return _priority_queue.enqueue(notification)


def dequeue_notification() -> Dict[str, Any] | None:
    """알림 큐에서 추출 (sync)"""
    return _priority_queue.dequeue()


def dequeue_batch(size: int | None = None) -> List[Dict[str, Any]]:
    """알림 배치 추출 (sync)"""
    return _priority_queue.dequeue_batch(size)


def peek_notification() -> Dict[str, Any] | None:
    """최상위 알림 조회 (sync)"""
    return _priority_queue.peek()


def get_queue_size() -> int:
    """큐 크기 조회 (sync)"""
    return _priority_queue.size()


def clear_queue() -> None:
    """큐 비우기 (sync)"""
    _priority_queue.clear()


def get_queue_stats() -> Dict[str, Any]:
    """큐 통계 조회 (sync)"""
    return _priority_queue.get_stats()
