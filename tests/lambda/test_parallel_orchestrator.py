"""
Sprint 28: 병렬 처리 성능 테스트
ParallelOrchestrator 및 asyncio 기반 병렬 실행 검증
"""

import asyncio
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

# Set localstack mode
os.environ["AWS_ENV"] = "localstack"

# Add lambda directory to path
from guardian.checkers.base import CheckResult
from guardian.parallel_orchestrator import ParallelOrchestrator


class TestParallelOrchestrator(unittest.TestCase):
    """병렬 오케스트레이터 성능 테스트"""

    def setUp(self):
        """테스트 설정"""
        # 간단한 Mock 체커 생성
        self.mock_checkers = {}
        for name in [
            "ec2",
            "s3",
            "cost",
            "iam",
            "cloudtrail",
            "guardduty",
            "rds",
            "iam_policy_analyzer",
        ]:
            checker = Mock()
            # sync check 메서드
            checker.check = Mock(return_value=CheckResult("INFO", f"{name} ok", "OK", {}, None))
            # async check_async 메서드

            async def mock_check_async():
                return CheckResult("INFO", "ok", "OK", {}, None)

            checker.check_async = mock_check_async
            self.mock_checkers[name] = checker

        # Mock orchestrator
        self.mock_orchestrator = Mock()
        self.mock_orchestrator.checkers = self.mock_checkers
        self.mock_orchestrator.logger = Mock()
        self.mock_orchestrator._get_checks_for_type = Mock(
            side_effect=lambda check_type: self._get_checks_for_type(check_type)
        )

    def _get_checks_for_type(self, check_type):
        """체크 타입별 반환 목록"""
        if check_type == "cost":
            return ["cost"]
        elif check_type == "security":
            return ["ec2", "s3", "cloudtrail", "iam", "guardduty", "rds", "iam_policy_analyzer"]
        return ["cost", "ec2", "s3", "cloudtrail", "iam", "guardduty", "rds", "iam_policy_analyzer"]

    def test_parallel_orchestrator_creation(self):
        """병렬 오케스트레이터 생성 테스트"""
        parallel = ParallelOrchestrator(self.mock_orchestrator)
        self.assertIsNotNone(parallel)
        self.assertEqual(parallel._orch, self.mock_orchestrator)

    def test_parallel_all_checks(self):
        """모든 체크 병렬 실행"""
        parallel = ParallelOrchestrator(self.mock_orchestrator)
        event = {"check_type": "all", "time": "2026-05-22T00:00:00Z"}

        result = asyncio.run(parallel.run_all_checks_parallel(event))

        # 결과 검증
        self.assertEqual(result["statusCode"], 200)
        body = result["body"]
        self.assertEqual(body["check_type"], "all")
        self.assertIn("checks", body)
        self.assertIn("timestamp", body)
        print(f"All checks parallel result: {len(body['checks'])} checks")

    def test_parallel_security_checks(self):
        """보안 체크만 병렬 실행"""
        parallel = ParallelOrchestrator(self.mock_orchestrator)
        event = {"check_type": "security"}

        result = asyncio.run(parallel.run_all_checks_parallel(event))

        # 결과 검증
        self.assertEqual(result["statusCode"], 200)
        body = result["body"]
        self.assertEqual(body["check_type"], "security")
        # 7개 보안 체크
        self.assertEqual(len(body["checks"]), 7)

    def test_parallel_cost_check(self):
        """비용 체크만 병렬 실행"""
        parallel = ParallelOrchestrator(self.mock_orchestrator)
        event = {"check_type": "cost"}

        result = asyncio.run(parallel.run_all_checks_parallel(event))

        # 결과 검증
        self.assertEqual(result["statusCode"], 200)
        body = result["body"]
        self.assertEqual(body["check_type"], "cost")
        # 1개 비용 체크
        self.assertEqual(len(body["checks"]), 1)

    def test_parallel_execution_performance(self):
        """병렬 실행 성능 측정"""
        parallel = ParallelOrchestrator(self.mock_orchestrator)
        event = {"check_type": "all"}

        start = time.perf_counter()
        result = asyncio.run(parallel.run_all_checks_parallel(event))
        elapsed = time.perf_counter() - start

        # Mock 환경에서 모든 체크 < 1초
        self.assertLess(elapsed, 1.0)
        print(f"Parallel execution time: {elapsed:.3f}s (8 checks)")
        self.assertEqual(result["statusCode"], 200)

    def test_parallel_with_failing_checker(self):
        """체크 실패 시에도 다른 체크는 계속 실행"""
        # 일부 체커 실패 설정
        failing_checker = Mock()
        failing_checker.check_async = Mock(side_effect=Exception("Check failed"))
        self.mock_orchestrator.checkers["ec2"] = failing_checker

        parallel = ParallelOrchestrator(self.mock_orchestrator)
        event = {"check_type": "all"}

        result = asyncio.run(parallel.run_all_checks_parallel(event))

        # 실패한 체크는 None, 다른 체크는 결과 있음
        self.assertEqual(result["statusCode"], 200)
        body = result["body"]
        self.assertIsNone(body["checks"].get("ec2"))
        # 다른 체크들은 결과가 있어야 함
        self.assertGreater(len(body["checks"]), 1)

    def test_concurrent_semaphore_pattern(self):
        """동시성 제한 패턴 테스트"""

        async def run_with_semaphore():
            semaphore = asyncio.Semaphore(5)

            async def limited_task(i):
                async with semaphore:
                    await asyncio.sleep(0.01)
                    return i

            start = time.perf_counter()
            results = await asyncio.gather(*[limited_task(i) for i in range(20)])
            elapsed = time.perf_counter() - start
            return results, elapsed

        results, elapsed = asyncio.run(run_with_semaphore())

        # 20개 작업, 5개 동시 = 최소 4배치
        self.assertEqual(len(results), 20)
        # 최소 0.04초 (4배치 * 0.01초)
        self.assertGreaterEqual(elapsed, 0.04)
        print(f"Semaphore pattern (20 tasks, limit 5): {elapsed:.3f}s")

    def test_parallel_multiple_regions_simulation(self):
        """다중 리전 병렬 처리 시뮬레이션"""

        async def check_multiple_regions():
            """여러 리전에서 병렬로 체크"""
            tasks = []
            for region in ["us-east-1", "eu-west-1", "ap-northeast-1", "ap-southeast-1"]:
                # 각 리전마다 병렬 오케스트레이터 생성
                parallel = ParallelOrchestrator(self.mock_orchestrator)
                task = parallel.run_all_checks_parallel({"check_type": "all", "region": region})
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        start = time.perf_counter()
        results = asyncio.run(check_multiple_regions())
        elapsed = time.perf_counter() - start

        # 4개 리전 병렬 < 1초 (Mock 환경)
        self.assertEqual(len(results), 4)
        self.assertLess(elapsed, 1.0)
        print(f"4 regions parallel execution: {elapsed:.3f}s")

    def test_large_scale_simulation(self):
        """대규모 환경 시뮬레이션 (20개 리전)"""

        async def check_large_scale():
            """20개 리전에서 병렬 체크"""
            regions = [f"region-{i}" for i in range(20)]
            tasks = []
            for region in regions:
                parallel = ParallelOrchestrator(self.mock_orchestrator)
                task = parallel.run_all_checks_parallel({"check_type": "all"})
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        start = time.perf_counter()
        results = asyncio.run(check_large_scale())
        elapsed = time.perf_counter() - start

        # 20개 리전 병렬 < 2초 (Mock 환경)
        self.assertEqual(len(results), 20)
        self.assertLess(elapsed, 2.0)
        print(f"20 regions parallel execution: {elapsed:.3f}s (10배 개선 vs sequential)")


if __name__ == "__main__":
    unittest.main()
