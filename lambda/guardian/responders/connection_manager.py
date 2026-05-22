"""
WebSocket 연결 생명주기 관리
하트비트, TTL 관리, 연결 정보 추적
"""

from typing import Dict, List, Any
from datetime import datetime, timezone


class ConnectionManager:
    """WebSocket 연결 생명주기 관리"""

    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: 연결 TTL (초, 기본 5분)
        """
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
        self.total_connections = 0
        self.total_disconnections = 0

    async def add_connection(
        self,
        conn_id: str,
        user_id: str,
        metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        연결 추가

        Args:
            conn_id: 연결 ID
            user_id: 사용자 ID
            metadata: 추가 메타데이터

        Returns:
            연결 정보
        """
        now = datetime.now(timezone.utc)

        self.connections[conn_id] = {
            "conn_id": conn_id,
            "user_id": user_id,
            "created_at": now,
            "last_heartbeat": now,
            "heartbeat_count": 0,
            "message_count": 0,
            "metadata": metadata or {}
        }
        self.total_connections += 1

        return {
            "status": "added",
            "conn_id": conn_id,
            "user_id": user_id,
            "created_at": now.isoformat()
        }

    async def remove_connection(self, conn_id: str) -> Dict[str, Any]:
        """
        연결 제거

        Args:
            conn_id: 연결 ID

        Returns:
            제거 결과
        """
        if conn_id not in self.connections:
            return {"status": "not_found", "conn_id": conn_id}

        conn = self.connections[conn_id]
        duration = (datetime.now(timezone.utc) - conn["created_at"]).total_seconds()

        del self.connections[conn_id]
        self.total_disconnections += 1

        return {
            "status": "removed",
            "conn_id": conn_id,
            "user_id": conn["user_id"],
            "duration_seconds": duration,
            "heartbeat_count": conn["heartbeat_count"],
            "message_count": conn["message_count"]
        }

    async def heartbeat(self, conn_id: str) -> Dict[str, Any]:
        """
        하트비트 갱신

        Args:
            conn_id: 연결 ID

        Returns:
            하트비트 결과
        """
        if conn_id not in self.connections:
            return {"status": "failed", "error": "Connection not found"}

        now = datetime.now(timezone.utc)
        self.connections[conn_id]["last_heartbeat"] = now
        self.connections[conn_id]["heartbeat_count"] += 1

        return {
            "status": "ok",
            "conn_id": conn_id,
            "last_heartbeat": now.isoformat(),
            "heartbeat_count": self.connections[conn_id]["heartbeat_count"]
        }

    async def increment_message_count(self, conn_id: str) -> int:
        """
        메시지 카운트 증가

        Args:
            conn_id: 연결 ID

        Returns:
            새로운 메시지 카운트
        """
        if conn_id in self.connections:
            self.connections[conn_id]["message_count"] += 1
            return self.connections[conn_id]["message_count"]
        return 0

    async def cleanup_stale_connections(self) -> List[str]:
        """
        TTL 만료된 연결 정리

        Returns:
            정리된 연결 ID 리스트
        """
        now = datetime.now(timezone.utc)
        stale = []

        for conn_id, meta in list(self.connections.items()):
            age = (now - meta["last_heartbeat"]).total_seconds()
            if age > self.ttl:
                stale.append(conn_id)
                await self.remove_connection(conn_id)

        return stale

    def is_connection_alive(self, conn_id: str) -> bool:
        """
        연결이 살아있는지 확인

        Args:
            conn_id: 연결 ID

        Returns:
            연결 상태
        """
        if conn_id not in self.connections:
            return False

        now = datetime.now(timezone.utc)
        meta = self.connections[conn_id]
        age = (now - meta["last_heartbeat"]).total_seconds()

        return age <= self.ttl

    def get_connection_info(self, conn_id: str) -> Dict[str, Any] | None:
        """
        연결 정보 조회

        Args:
            conn_id: 연결 ID

        Returns:
            연결 정보 또는 None
        """
        if conn_id not in self.connections:
            return None

        conn = self.connections[conn_id]
        now = datetime.now(timezone.utc)
        age = (now - conn["last_heartbeat"]).total_seconds()

        return {
            "conn_id": conn_id,
            "user_id": conn["user_id"],
            "created_at": conn["created_at"].isoformat(),
            "last_heartbeat": conn["last_heartbeat"].isoformat(),
            "age_seconds": age,
            "is_alive": age <= self.ttl,
            "heartbeat_count": conn["heartbeat_count"],
            "message_count": conn["message_count"],
            "metadata": conn["metadata"]
        }

    def get_all_connections(self) -> List[Dict[str, Any]]:
        """
        모든 활성 연결 조회

        Returns:
            연결 정보 리스트
        """
        result = []
        for conn_id in self.connections.keys():
            info = self.get_connection_info(conn_id)
            if info:
                result.append(info)
        return result

    def get_connections_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        특정 사용자의 연결 조회

        Args:
            user_id: 사용자 ID

        Returns:
            연결 정보 리스트
        """
        result = []
        for conn_id, meta in self.connections.items():
            if meta["user_id"] == user_id:
                info = self.get_connection_info(conn_id)
                if info:
                    result.append(info)
        return result

    def get_stats(self) -> Dict[str, Any]:
        """연결 통계"""
        now = datetime.now(timezone.utc)
        ages = []

        for meta in self.connections.values():
            age = (now - meta["last_heartbeat"]).total_seconds()
            ages.append(age)

        avg_age = sum(ages) / len(ages) if ages else 0
        max_age = max(ages) if ages else 0

        return {
            "total_added": self.total_connections,
            "total_removed": self.total_disconnections,
            "current_active": len(self.connections),
            "avg_connection_age_seconds": round(avg_age, 1),
            "max_connection_age_seconds": round(max_age, 1),
            "ttl_seconds": self.ttl
        }


# 글로벌 연결 관리자 인스턴스
_connection_manager = ConnectionManager(ttl_seconds=300)


async def add_connection(
    conn_id: str,
    user_id: str,
    metadata: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """연결 추가 (async)"""
    return await _connection_manager.add_connection(conn_id, user_id, metadata)


async def remove_connection(conn_id: str) -> Dict[str, Any]:
    """연결 제거 (async)"""
    return await _connection_manager.remove_connection(conn_id)


async def heartbeat(conn_id: str) -> Dict[str, Any]:
    """하트비트 갱신 (async)"""
    return await _connection_manager.heartbeat(conn_id)


async def cleanup_stale_connections() -> List[str]:
    """스테일 연결 정리 (async)"""
    return await _connection_manager.cleanup_stale_connections()


def get_connection_info(conn_id: str) -> Dict[str, Any] | None:
    """연결 정보 조회 (sync)"""
    return _connection_manager.get_connection_info(conn_id)


def get_all_connections() -> List[Dict[str, Any]]:
    """모든 연결 조회 (sync)"""
    return _connection_manager.get_all_connections()


def get_connections_by_user(user_id: str) -> List[Dict[str, Any]]:
    """사용자별 연결 조회 (sync)"""
    return _connection_manager.get_connections_by_user(user_id)


def get_connection_stats() -> Dict[str, Any]:
    """연결 통계 조회 (sync)"""
    return _connection_manager.get_stats()
