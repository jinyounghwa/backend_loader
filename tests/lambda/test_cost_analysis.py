"""
Sprint 29: 비용 분석 & 최적화 제안 테스트
CostAnalyzer 및 OptimizationSuggester 검증
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path

os.environ["AWS_ENV"] = "localstack"

lambda_dir = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))

from guardian.analytics.cost_analyzer import (
    CostAnalyzer,
    generate_monthly_report,
    generate_monthly_report_sync,
)
from guardian.analytics.optimization_suggester import (
    OptimizationSuggester,
    suggest_optimizations,
    suggest_optimizations_sync,
)


class TestCostAnalyzer(unittest.TestCase):
    """비용 분석 테스트"""

    def setUp(self):
        self.analyzer = CostAnalyzer()

    def test_monthly_report_generation(self):
        """월별 리포트 생성"""
        # 30일 비용 데이터
        daily_costs = [10.0 + i * 0.1 for i in range(30)]

        result = asyncio.run(
            self.analyzer.generate_monthly_report("123456789", daily_costs, "2026-05")
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["month"], "2026-05")
        self.assertGreater(result["total_cost"], 0)
        self.assertGreater(result["daily_average"], 0)
        self.assertIn("trend", result)
        self.assertIn("breakdown", result)
        self.assertIn("forecast_next_month", result)

    def test_trend_analysis_increasing(self):
        """증가 추세 분석"""
        daily_costs = [5.0 + i * 0.5 for i in range(30)]  # 점진적 증가

        result = asyncio.run(
            self.analyzer.generate_monthly_report("123456789", daily_costs, "2026-05")
        )

        trend = result["trend"]
        self.assertIn(trend["trend"], ["gradually_increasing", "rapidly_increasing"])
        self.assertGreater(trend["slope"], 0)

    def test_trend_analysis_stable(self):
        """안정적 추세 분석"""
        daily_costs = [10.0] * 30  # 일정한 비용

        result = asyncio.run(
            self.analyzer.generate_monthly_report("123456789", daily_costs, "2026-05")
        )

        trend = result["trend"]
        self.assertIn(trend["trend"], ["stable"])
        self.assertLess(abs(trend["slope"]), 0.3)

    def test_anomaly_detection(self):
        """비용 이상 감지"""
        daily_costs = [10.0] * 25 + [50.0, 55.0, 52.0, 11.0, 12.0]  # 마지막 주 급증

        result = asyncio.run(
            self.analyzer.generate_monthly_report("123456789", daily_costs, "2026-05")
        )

        anomalies = result["anomalies"]
        # 50달러 이상의 이상 감지
        self.assertGreater(len(anomalies), 0)
        for anomaly in anomalies:
            self.assertGreater(anomaly["cost"], 30)  # 평균보다 훨씬 높음

    def test_category_breakdown(self):
        """카테고리별 분석"""
        daily_costs = [10.0] * 30

        result = asyncio.run(
            self.analyzer.generate_monthly_report("123456789", daily_costs, "2026-05")
        )

        breakdown = result["breakdown"]
        self.assertIn("by_service", breakdown)
        self.assertIn("percentages", breakdown)
        self.assertIn("top_service", breakdown)

        # 전체 합계 = 월별 비용
        total_breakdown = sum(breakdown["by_service"].values())
        self.assertAlmostEqual(total_breakdown, result["total_cost"], places=1)

    def test_forecast_next_month(self):
        """다음 달 예측"""
        daily_costs = [10.0] * 30

        result = asyncio.run(
            self.analyzer.generate_monthly_report("123456789", daily_costs, "2026-05")
        )

        forecast = result["forecast_next_month"]
        self.assertGreater(forecast["forecast"], 0)
        self.assertIn("lower_bound", forecast)
        self.assertIn("upper_bound", forecast)
        self.assertLess(forecast["lower_bound"], forecast["forecast"])
        self.assertGreater(forecast["upper_bound"], forecast["forecast"])

    def test_sync_wrapper(self):
        """동기 래퍼"""
        daily_costs = [10.0] * 30

        result = generate_monthly_report_sync("123456789", daily_costs, "2026-05")

        self.assertIsNotNone(result)
        self.assertEqual(result["month"], "2026-05")

    def test_module_level_function(self):
        """모듈 레벨 함수"""
        daily_costs = [10.0] * 30

        result = asyncio.run(generate_monthly_report("123456789", daily_costs, "2026-05"))

        self.assertIsNotNone(result)
        self.assertGreater(result["total_cost"], 0)

    def test_empty_daily_costs(self):
        """빈 비용 데이터"""
        result = asyncio.run(self.analyzer.generate_monthly_report("123456789", [], "2026-05"))

        self.assertEqual(result["total_cost"], 0)
        self.assertEqual(result["trend"], "no_data")

    def test_small_dataset(self):
        """작은 데이터셋"""
        daily_costs = [10.0, 12.0, 11.0]  # 3일

        result = asyncio.run(
            self.analyzer.generate_monthly_report("123456789", daily_costs, "2026-05")
        )

        self.assertEqual(result["trend"]["trend"], "insufficient_data")
        forecast = result["forecast_next_month"]
        self.assertIn(forecast["confidence"], ["low", "medium"])


class TestOptimizationSuggester(unittest.TestCase):
    """최적화 제안 테스트"""

    def setUp(self):
        self.suggester = OptimizationSuggester()

    def test_suggest_optimizations_no_findings(self):
        """빈 findings"""
        findings = {}

        result = asyncio.run(self.suggester.suggest_optimizations(findings))

        self.assertEqual(len(result), 0)

    def test_find_unused_ec2(self):
        """미사용 EC2 식별"""
        findings = {
            "ec2": True,
            "instances": [
                {
                    "instance_id": "i-123",
                    "instance_type": "t3.medium",
                    "cpu_utilization": 2.0,
                    "monthly_cost": 50.0,
                },
                {
                    "instance_id": "i-456",
                    "instance_type": "m5.large",
                    "cpu_utilization": 80.0,
                    "monthly_cost": 100.0,
                },
            ],
        }

        result = asyncio.run(self.suggester.suggest_optimizations(findings))

        # 미사용 인스턴스 제안 확인
        unused_suggestions = [s for s in result if s["type"] == "terminate_unused"]
        self.assertGreater(len(unused_suggestions), 0)

    def test_suggest_reserved_instances(self):
        """Reserved Instance 추천"""
        findings = {
            "ec2": True,
            "instances": [
                {
                    "instance_id": "i-1",
                    "instance_type": "t3.medium",
                    "cpu_utilization": 50.0,
                    "monthly_cost": 50.0,
                },
                {
                    "instance_id": "i-2",
                    "instance_type": "t3.medium",
                    "cpu_utilization": 60.0,
                    "monthly_cost": 50.0,
                },
            ],
        }

        result = asyncio.run(self.suggester.suggest_optimizations(findings))

        # RI 추천 확인
        ri_suggestions = [s for s in result if s["type"] == "purchase_reserved_instance"]
        self.assertGreater(len(ri_suggestions), 0)

    def test_optimization_summary(self):
        """최적화 요약"""
        findings = {
            "ec2": True,
            "instances": [
                {
                    "instance_id": "i-123",
                    "instance_type": "t3.medium",
                    "cpu_utilization": 2.0,
                    "monthly_cost": 50.0,
                },
            ],
        }

        suggestions = asyncio.run(self.suggester.suggest_optimizations(findings))
        summary = self.suggester.get_summary(suggestions)

        self.assertIn("total_potential_savings", summary)
        self.assertIn("count", summary)
        self.assertIn("by_priority", summary)
        self.assertGreater(summary["annual_savings"], 0)

    def test_sync_wrapper(self):
        """동기 래퍼"""
        findings = {
            "ec2": True,
            "instances": [
                {
                    "instance_id": "i-123",
                    "instance_type": "t3.medium",
                    "cpu_utilization": 2.0,
                    "monthly_cost": 50.0,
                }
            ],
        }

        result = suggest_optimizations_sync(findings)

        self.assertIsInstance(result, list)

    def test_module_level_function(self):
        """모듈 레벨 함수"""
        findings = {"ec2": True, "instances": []}

        result = asyncio.run(suggest_optimizations(findings))

        self.assertIsInstance(result, list)

    def test_priority_sorting(self):
        """우선순위 정렬"""
        findings = {
            "ec2": True,
            "instances": [
                {
                    "instance_id": f"i-{i}",
                    "instance_type": "t3.medium",
                    "cpu_utilization": 2.0,
                    "monthly_cost": 50.0 + (i * 10),
                }
                for i in range(3)
            ],
        }

        suggestions = asyncio.run(self.suggester.suggest_optimizations(findings))

        # 절감액이 높은 순서인지 확인
        if len(suggestions) > 1:
            for i in range(len(suggestions) - 1):
                self.assertGreaterEqual(
                    suggestions[i]["potential_savings"],
                    suggestions[i + 1]["potential_savings"],
                )


if __name__ == "__main__":
    unittest.main()
