"""Incident caching for performance optimization"""

import time
from typing import Optional, Dict, Any


class IncidentCache:
    """조회 성능 향상을 위한 인시던트 캐시"""

    def __init__(self, ttl_seconds: int = 3600):
        """
        캐시 초기화

        Args:
            ttl_seconds: Time-to-live in seconds (기본값: 1시간)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def get(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """
        캐시에서 인시던트 조회

        Args:
            incident_id: 인시던트 ID

        Returns:
            캐시된 인시던트 또는 None
        """
        if incident_id in self.cache:
            entry = self.cache[incident_id]
            current_time = time.time()

            # TTL 확인
            if current_time - entry["timestamp"] < self.ttl:
                self.stats["hits"] += 1
                return entry["data"]
            else:
                # 만료된 항목 삭제
                del self.cache[incident_id]
                self.stats["evictions"] += 1

        self.stats["misses"] += 1
        return None

    def set(self, incident_id: str, incident: Dict[str, Any]) -> None:
        """
        캐시에 인시던트 저장

        Args:
            incident_id: 인시던트 ID
            incident: 인시던트 데이터
        """
        self.cache[incident_id] = {
            "data": incident,
            "timestamp": time.time()
        }

    def delete(self, incident_id: str) -> bool:
        """
        캐시에서 인시던트 삭제

        Args:
            incident_id: 인시던트 ID

        Returns:
            삭제 성공 여부
        """
        if incident_id in self.cache:
            del self.cache[incident_id]
            return True
        return False

    def clear(self) -> None:
        """전체 캐시 초기화"""
        self.cache.clear()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 반환

        Returns:
            캐시 통계 (hits, misses, evictions, hit_rate)
        """
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total * 100 if total > 0 else 0
        )

        return {
            **self.stats,
            "hit_rate": hit_rate,
            "cached_items": len(self.cache)
        }

    def cleanup_expired(self) -> int:
        """
        만료된 항목 정리

        Returns:
            정리된 항목 수
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry["timestamp"] >= self.ttl
        ]

        for key in expired_keys:
            del self.cache[key]
            self.stats["evictions"] += 1

        return len(expired_keys)
