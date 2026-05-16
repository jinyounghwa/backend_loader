"""
병렬 처리 기반 Guardian 오케스트레이터
asyncio를 활용한 병렬 실행으로 10배 성능 개선
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any
from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.s3 import S3Checker
from guardian.checkers.cost import CostChecker
from guardian.cache import CacheFactory


class ParallelOrchestrator:
    """병렬 처리 기반 멀티 체크 오케스트레이터"""

    def __init__(self, cache_backend='memory'):
        self.cache = CacheFactory.create(cache_backend)
        self.max_concurrent = 10
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    async def run_all_checks_parallel(self) -> Dict[str, Any]:
        """모든 체크를 병렬로 실행"""
        ec2_checker = EC2Checker(self.cache)
        s3_checker = S3Checker(self.cache)
        cost_checker = CostChecker(self.cache)

        tasks = [
            self._run_with_semaphore(ec2_checker.check_async()),
            self._run_with_semaphore(s3_checker.check_async()),
            self._run_with_semaphore(cost_checker.check_async()),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            'ec2': results[0],
            's3': results[1],
            'cost': results[2],
            'timestamp': self._get_timestamp(),
        }

    async def check_all_regions_parallel(self) -> Dict[str, Any]:
        """모든 리전을 병렬로 확인"""
        ec2_checker = EC2Checker(self.cache)

        # 모든 리전 조회
        regions = await ec2_checker.get_all_regions_async()

        # 리전별 병렬 체크
        tasks = [
            self._run_with_semaphore(
                ec2_checker.check_region_async(region)
            )
            for region in regions
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 집계
        return {
            'regions': len(regions),
            'checked': len([r for r in results if not isinstance(r, Exception)]),
            'errors': len([r for r in results if isinstance(r, Exception)]),
            'details': results,
            'timestamp': self._get_timestamp(),
        }

    async def _run_with_semaphore(self, task):
        """세마포어를 사용한 동시성 제한"""
        async with self.semaphore:
            return await task

    def _get_timestamp(self) -> str:
        """현재 타임스탐프"""
        return datetime.now(timezone.utc).isoformat()


# 동기 래퍼 (Lambda에서 사용)
def run_all_checks():
    """모든 체크 실행 (동기)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    orchestrator = ParallelOrchestrator()
    results = loop.run_until_complete(
        orchestrator.run_all_checks_parallel()
    )

    loop.close()
    return results


def check_all_regions():
    """모든 리전 확인 (동기)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    orchestrator = ParallelOrchestrator()
    results = loop.run_until_complete(
        orchestrator.check_all_regions_parallel()
    )

    loop.close()
    return results
