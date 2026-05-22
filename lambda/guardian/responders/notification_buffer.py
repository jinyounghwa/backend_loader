"""
알림 배칭 및 버퍼 관리 시스템
동일 이벤트를 배칭 윈도우 내에서 병합하여 알림 폭증 방지
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List


class NotificationBuffer:
    """동일 이벤트 병합 및 배칭"""

    def __init__(self, batch_window: int = 10):
        """
        Args:
            batch_window: 배칭 윈도우 (초)
        """
        self.batch_window = batch_window
        self.buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.pending_flushes: Dict[str, asyncio.Task] = {}
        self.total_batches = 0
        self.total_events = 0
        self.total_merged = 0

    def _get_event_key(self, event: Dict[str, Any]) -> str:
        """
        이벤트 고유키 생성
        check_type과 severity 조합으로 같은 종류의 이벤트 식별
        """
        check_type = event.get("check_type", "unknown")
        severity = event.get("severity", "unknown")
        return f"{check_type}:{severity}"

    async def add_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        이벤트 버퍼에 추가

        Args:
            event: 추가할 이벤트

        Returns:
            처리 결과
        """
        key = self._get_event_key(event)
        self.buffer[key].append(event)
        self.total_events += 1

        # 이미 flush 예약된 경우 스킵
        if key in self.pending_flushes:
            return {
                "status": "buffered",
                "key": key,
                "buffered_count": len(self.buffer[key]),
                "action": "merged_with_pending_batch",
            }

        # batch_window 후 flush 예약
        task = asyncio.create_task(self._flush_after_delay(key))
        self.pending_flushes[key] = task

        return {
            "status": "buffered",
            "key": key,
            "buffered_count": 1,
            "action": "new_batch_scheduled",
        }

    async def _flush_after_delay(self, key: str) -> None:
        """배칭 윈도우 후 알림 전송"""
        await asyncio.sleep(self.batch_window)
        await self.flush_key(key)

    async def flush_key(self, key: str) -> Dict[str, Any]:
        """
        특정 키의 버퍼 비우기

        Args:
            key: 버퍼 키

        Returns:
            flush 결과
        """
        if key not in self.buffer or not self.buffer[key]:
            return {"status": "empty", "key": key}

        events = self.buffer[key]
        count = len(events)

        # 합성 메시지
        message = self._create_batched_message(events, count)
        self.total_batches += 1
        if count > 1:
            self.total_merged += count - 1

        # 정리
        del self.buffer[key]
        if key in self.pending_flushes:
            del self.pending_flushes[key]

        return {"status": "flushed", "key": key, "message_count": count, "message": message}

    def _create_batched_message(self, events: List[Dict[str, Any]], count: int) -> Dict[str, Any]:
        """
        여러 이벤트를 하나의 메시지로 병합

        Args:
            events: 이벤트 리스트
            count: 이벤트 개수

        Returns:
            병합된 메시지
        """
        if count == 1:
            return events[0]

        return {
            "type": "batched_events",
            "count": count,
            "check_type": events[0].get("check_type"),
            "severity": events[0].get("severity"),
            "first_event_time": events[0].get("timestamp", datetime.now(timezone.utc).isoformat()),
            "last_event_time": events[-1].get("timestamp", datetime.now(timezone.utc).isoformat()),
            "summary": f"{count}개의 동일한 {events[0].get('severity')} 이벤트 감지",
            "events": events,
            "merged_at": datetime.now(timezone.utc).isoformat(),
        }

    async def force_flush_all(self) -> List[Dict[str, Any]]:
        """
        모든 버퍼 강제 비우기

        Returns:
            flush된 메시지 리스트
        """
        keys = list(self.buffer.keys())
        results = []

        for key in keys:
            result = await self.flush_key(key)
            if result["status"] == "flushed":
                results.append(result["message"])

        return results

    def get_buffer_stats(self) -> Dict[str, Any]:
        """버퍼 통계"""
        return {
            "total_events_processed": self.total_events,
            "total_batches_sent": self.total_batches,
            "total_events_merged": self.total_merged,
            "merge_efficiency": (
                round((self.total_merged / self.total_events * 100), 1)
                if self.total_events > 0
                else 0
            ),
            "current_pending_keys": len(self.buffer),
            "current_pending_events": sum(len(v) for v in self.buffer.values()),
        }

    def get_buffer_contents(self) -> Dict[str, List[Dict[str, Any]]]:
        """현재 버퍼 내용 조회"""
        return dict(self.buffer)


# 글로벌 버퍼 인스턴스
_notification_buffer = NotificationBuffer(batch_window=10)


async def add_notification_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """알림 이벤트 추가 (async)"""
    return await _notification_buffer.add_event(event)


async def force_flush_notifications() -> List[Dict[str, Any]]:
    """모든 대기 중인 알림 즉시 전송 (async)"""
    return await _notification_buffer.force_flush_all()


def get_buffer_stats() -> Dict[str, Any]:
    """버퍼 통계 조회 (sync)"""
    return _notification_buffer.get_buffer_stats()


def get_buffer_contents() -> Dict[str, List[Dict[str, Any]]]:
    """버퍼 내용 조회 (sync)"""
    return _notification_buffer.get_buffer_contents()
