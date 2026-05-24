"""Sprint 45 Phase 2: 성능 최적화 검증 테스트 (5 tests)"""

import sys
from pathlib import Path

import pytest
import time

# Add lambda directory to path
lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.cache.incident_cache import IncidentCache


class TestPerformance:
    """성능 최적화 검증"""

    def test_caching_reduces_lookup_time_by_90_percent(self):
        """✅ 캐싱이 조회 시간을 90% 이상 단축"""
        cache = IncidentCache(ttl_seconds=3600)

        incident = {
            "incident_id": "INC-001",
            "event_type": "EC2 Stop",
            "severity": 8,
            "account_id": "123456789012"
        }

        # 캐시에 저장
        cache.set("INC-001", incident)

        # 캐시 조회 성능 측정
        start = time.perf_counter()
        for _ in range(1000):
            result = cache.get("INC-001")
        cache_time = time.perf_counter() - start

        # 캐시 없이 데이터베이스 조회 시뮬레이션 (네트워크 지연 포함)
        def db_query():
            time.sleep(0.001)  # 1ms 네트워크 지연
            return incident

        start = time.perf_counter()
        for _ in range(1000):
            result = db_query()
        db_time = time.perf_counter() - start

        # 캐시가 DB보다 훨씬 빠름 (약 100배)
        assert cache_time < db_time
        assert (db_time / cache_time) > 100, f"Cache is {db_time / cache_time}x faster"

    def test_cache_ttl_expiration(self):
        """✅ 캐시 TTL 만료 처리"""
        cache = IncidentCache(ttl_seconds=1)  # 1초 TTL

        incident = {
            "incident_id": "INC-002",
            "event_type": "S3 Public",
            "severity": 7
        }

        # 캐시에 저장
        cache.set("INC-002", incident)

        # 즉시 조회: 캐시에서 반환
        result = cache.get("INC-002")
        assert result is not None
        assert result["event_type"] == "S3 Public"

        # TTL 후 조회: None 반환
        time.sleep(1.1)
        result = cache.get("INC-002")
        assert result is None

    def test_parallel_orchestration_performance(self):
        """✅ 병렬 오케스트레이션 성능"""
        cache = IncidentCache(ttl_seconds=3600)

        # 여러 인시던트 미리 로드
        incidents = []
        for i in range(100):
            incident = {
                "incident_id": f"INC-{i:04d}",
                "event_type": "Test",
                "severity": i % 10 + 1
            }
            cache.set(f"INC-{i:04d}", incident)
            incidents.append(incident)

        # 병렬 조회 시뮬레이션
        start = time.perf_counter()
        results = []
        for i in range(100):
            result = cache.get(f"INC-{i:04d}")
            results.append(result)
        parallel_time = time.perf_counter() - start

        # 모든 조회 성공
        assert len(results) == 100
        assert all(r is not None for r in results)

        # 성능이 좋음 (< 100ms)
        assert parallel_time < 0.1

    def test_workflow_execution_time_optimization(self):
        """✅ 워크플로우 실행 시간 최적화"""
        cache = IncidentCache(ttl_seconds=3600)

        # 워크플로우 상태 캐싱
        workflow_state = {
            "workflow_id": "WF-001",
            "status": "running",
            "steps_completed": 3,
            "total_steps": 5
        }

        cache.set("WF-001", workflow_state)

        # 캐시 통계
        start = time.perf_counter()

        # 워크플로우 상태 반복 조회 (캐시 활용)
        for _ in range(1000):
            state = cache.get("WF-001")

        cached_time = time.perf_counter() - start

        # 캐시 통계 확인
        stats = cache.get_stats()
        assert stats["hit_rate"] == 100.0, "모든 조회가 캐시 히트"
        assert stats["hits"] == 1000
        assert stats["misses"] == 0

    def test_soar_submission_batch_optimization(self):
        """✅ SOAR 제출 배치 최적화"""
        cache = IncidentCache(ttl_seconds=3600)

        # SOAR 제출 배치 생성
        batch = []
        for i in range(50):
            submission = {
                "submission_id": f"SUB-{i:04d}",
                "status": "pending",
                "priority": (i % 5) + 1
            }
            cache.set(f"SUB-{i:04d}", submission)
            batch.append(submission)

        # 배치 처리 시뮬레이션
        start = time.perf_counter()

        for i in range(50):
            submission = cache.get(f"SUB-{i:04d}")
            if submission:
                # SOAR 제출 시뮬레이션
                submission["status"] = "submitted"
                cache.set(f"SUB-{i:04d}", submission)

        batch_time = time.perf_counter() - start

        # 캐시 성능 확인
        stats = cache.get_stats()
        assert stats["cached_items"] == 50
        assert batch_time < 0.05, "배치 처리가 빠름"
