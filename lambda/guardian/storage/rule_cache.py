import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class CacheStatistics:
    """캐시 통계"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    last_refresh_time: Optional[float] = None
    last_refresh_duration_ms: Optional[float] = None

    @property
    def hit_rate(self) -> float:
        """캐시 히트율 (0-100)"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100


class RuleCache:
    """
    규칙 캐싱 시스템 (TTL 기반 메모리 캐시)

    특징:
    - TTL 기반 자동 만료 (기본 5분)
    - 쓰레드 안전성 (Lock 사용)
    - 캐시 통계 추적 (히트율, 미스, 만료)
    - 수동 새로고침 지원
    """

    def __init__(self, rules_repo, ttl_seconds: int = 300):
        """
        Args:
            rules_repo: SecurityRuleRepository 인스턴스
            ttl_seconds: 캐시 TTL (기본 300초 = 5분)
        """
        self.rules_repo = rules_repo
        self.ttl = ttl_seconds
        self.cache = {}
        self.stats = CacheStatistics()
        self.lock = Lock()

    def get_active_rules(self) -> List[Dict[str, Any]]:
        """
        캐시된 활성 규칙 반환

        캐시가 유효하면 캐시에서 반환,
        캐시가 만료되었으면 DB에서 새로 로드

        Returns:
            활성 규칙 목록
        """
        with self.lock:
            # 캐시 유효성 확인
            if self._is_cache_valid():
                self.stats.hits += 1
                logger.debug(f"Cache hit. Hit rate: {self.stats.hit_rate:.1f}%")
                return self.cache.get('active_rules', [])

            # 캐시 미스 또는 만료
            self.stats.misses += 1
            logger.info(f"Cache miss. Refreshing rules from database. Hit rate: {self.stats.hit_rate:.1f}%")

            # DB에서 새로 로드
            rules = self.refresh()
            return rules

    def refresh(self) -> List[Dict[str, Any]]:
        """
        규칙 캐시 새로고침 (lock을 이미 획득한 상태에서 호출됨)

        DB에서 활성 규칙을 로드하여 캐시 갱신

        Returns:
            갱신된 활성 규칙 목록
        """
        refresh_start = time.time()

        try:
            # DB에서 활성 규칙 로드
            rules = self.rules_repo.list_active_rules()

            # 캐시 업데이트
            self.cache['active_rules'] = rules
            self.cache['timestamp'] = time.time()

            refresh_duration_ms = (time.time() - refresh_start) * 1000
            self.stats.last_refresh_time = self.cache['timestamp']
            self.stats.last_refresh_duration_ms = refresh_duration_ms

            logger.info(
                f"Cache refreshed: {len(rules)} rules loaded in {refresh_duration_ms:.1f}ms"
            )

            return rules

        except Exception as e:
            logger.error(f"Cache refresh failed: {str(e)}")
            raise

    def invalidate(self):
        """캐시 강제 무효화"""
        with self.lock:
            if 'active_rules' in self.cache:
                self.stats.evictions += 1
            self.cache.clear()
            logger.info("Cache invalidated")

    def get_statistics(self) -> CacheStatistics:
        """캐시 통계 반환"""
        with self.lock:
            return CacheStatistics(
                hits=self.stats.hits,
                misses=self.stats.misses,
                evictions=self.stats.evictions,
                last_refresh_time=self.stats.last_refresh_time,
                last_refresh_duration_ms=self.stats.last_refresh_duration_ms
            )

    def _is_cache_valid(self) -> bool:
        """캐시 유효성 확인 (만료 여부)"""
        if 'active_rules' not in self.cache or 'timestamp' not in self.cache:
            return False

        elapsed = time.time() - self.cache['timestamp']
        is_valid = elapsed < self.ttl

        if not is_valid:
            logger.debug(f"Cache expired: {elapsed:.1f}s > {self.ttl}s")

        return is_valid

    def set_ttl(self, ttl_seconds: int):
        """TTL 변경"""
        with self.lock:
            old_ttl = self.ttl
            self.ttl = ttl_seconds
            logger.info(f"Cache TTL changed: {old_ttl}s -> {ttl_seconds}s")

    def get_cache_age_ms(self) -> Optional[float]:
        """캐시 나이 (밀리초)"""
        with self.lock:
            if 'timestamp' not in self.cache:
                return None
            return (time.time() - self.cache['timestamp']) * 1000

    def get_cache_size(self) -> int:
        """캐시 크기 (규칙 수)"""
        with self.lock:
            return len(self.cache.get('active_rules', []))
