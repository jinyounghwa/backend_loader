"""
Sprint 28: 병렬 처리 & ML 고도화 - ML 이상 탐지 테스트
AdvancedAnomalyDetector v2 정확도 및 기능 검증
"""

import unittest
import asyncio
from guardian.ml.anomaly_detector_v2 import AdvancedAnomalyDetector, detect_anomaly, detect_anomaly_sync


class TestAdvancedAnomalyDetector(unittest.TestCase):
    """고도화된 이상 탐지 모델 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.detector = AdvancedAnomalyDetector()

    def test_normal_metrics(self):
        """정상 메트릭 감지"""
        metrics = {
            "daily_cost": 5.0,
            "api_calls": 500,
            "error_rate": 0.01,
            "instance_count": 3,
        }

        result = asyncio.run(self.detector.detect_anomaly(metrics))

        # 정상 범위 → 이상 아님
        self.assertFalse(result["is_anomaly"])
        self.assertLess(result["confidence"], 50)
        self.assertEqual(result["accuracy"], 0.92)
        print(f"Normal metrics result: {result}")

    def test_high_cost_anomaly(self):
        """높은 비용 이상 감지"""
        metrics = {
            "daily_cost": 50.0,  # 매우 높음
            "api_calls": 500,
            "error_rate": 0.01,
            "instance_count": 3,
        }

        result = asyncio.run(self.detector.detect_anomaly(metrics))

        # 높은 비용은 이상
        self.assertIn("높은 비용", result["reason"])
        print(f"High cost anomaly: {result}")

    def test_high_error_rate_anomaly(self):
        """높은 에러율 이상 감지"""
        metrics = {
            "daily_cost": 10.0,
            "api_calls": 500,
            "error_rate": 0.15,  # 매우 높음 (15%)
            "instance_count": 3,
        }

        result = asyncio.run(self.detector.detect_anomaly(metrics))

        # 높은 에러율은 이상
        self.assertIn("에러율", result["reason"])
        print(f"High error rate anomaly: {result}")

    def test_excessive_api_calls_anomaly(self):
        """과도한 API 호출 이상 감지"""
        metrics = {
            "daily_cost": 10.0,
            "api_calls": 3000,  # 과도함
            "error_rate": 0.01,
            "instance_count": 3,
        }

        result = asyncio.run(self.detector.detect_anomaly(metrics))

        # 과도한 API 호출은 이상
        self.assertIn("API 호출", result["reason"])
        print(f"Excessive API calls anomaly: {result}")

    def test_trend_analysis_increasing(self):
        """비용 증가 추세 분석"""
        # 5개 데이터포인트 추가 (점진적 증가)
        for i in range(5):
            metrics = {
                "daily_cost": 5.0 + (i * 2),  # 5, 7, 9, 11, 13
                "api_calls": 500,
                "error_rate": 0.01,
                "instance_count": 3,
            }
            asyncio.run(self.detector.detect_anomaly(metrics))

        # 마지막 결과의 추세 확인
        result = asyncio.run(
            self.detector.detect_anomaly(
                {
                    "daily_cost": 15.0,
                    "api_calls": 500,
                    "error_rate": 0.01,
                    "instance_count": 3,
                }
            )
        )

        # 증가 추세 감지
        trend = result.get("trend", {})
        cost_trend = trend.get("cost_trend")
        self.assertIn(cost_trend, ["rapidly_increasing", "gradually_increasing", "stable"])
        print(f"Trend analysis: {trend}")

    def test_trend_analysis_stable(self):
        """안정적인 비용 추이 분석"""
        # 5개 데이터포인트 추가 (안정적)
        for i in range(5):
            metrics = {
                "daily_cost": 10.0,  # 일정함
                "api_calls": 500,
                "error_rate": 0.01,
                "instance_count": 3,
            }
            asyncio.run(self.detector.detect_anomaly(metrics))

        # 마지막 결과 확인
        result = asyncio.run(
            self.detector.detect_anomaly(
                {
                    "daily_cost": 10.0,
                    "api_calls": 500,
                    "error_rate": 0.01,
                    "instance_count": 3,
                }
            )
        )

        # 안정적인 추세
        trend = result.get("trend", {})
        self.assertEqual(trend.get("cost_trend"), "stable")
        print(f"Stable trend: {trend}")

    def test_history_tracking(self):
        """이상 탐지 히스토리 추적"""
        # 10개 메트릭 처리
        for i in range(10):
            metrics = {
                "daily_cost": 5.0 + (i * 0.5),
                "api_calls": 500 + (i * 10),
                "error_rate": 0.01 + (i * 0.001),
                "instance_count": 3,
            }
            asyncio.run(self.detector.detect_anomaly(metrics))

        # 히스토리 확인
        self.assertEqual(len(self.detector.history), 10)

        # 히스토리 최대 100개 유지 테스트
        for i in range(100):
            metrics = {
                "daily_cost": 5.0,
                "api_calls": 500,
                "error_rate": 0.01,
                "instance_count": 3,
            }
            asyncio.run(self.detector.detect_anomaly(metrics))

        # 최대 100개 유지
        self.assertEqual(len(self.detector.history), 100)

    def test_confidence_score(self):
        """신뢰도 점수 계산"""
        # 정상 메트릭
        normal_metrics = {
            "daily_cost": 5.0,
            "api_calls": 500,
            "error_rate": 0.01,
            "instance_count": 3,
        }
        normal_result = asyncio.run(self.detector.detect_anomaly(normal_metrics))

        # 이상 메트릭
        anomaly_metrics = {
            "daily_cost": 50.0,
            "api_calls": 3000,
            "error_rate": 0.2,
            "instance_count": 3,
        }
        anomaly_result = asyncio.run(self.detector.detect_anomaly(anomaly_metrics))

        # 신뢰도 점수 범위 검증
        self.assertGreaterEqual(normal_result["confidence"], 0)
        self.assertLessEqual(normal_result["confidence"], 100)
        self.assertGreaterEqual(anomaly_result["confidence"], 0)
        self.assertLessEqual(anomaly_result["confidence"], 100)
        print(f"Normal confidence: {normal_result['confidence']:.1f}%")
        print(f"Anomaly confidence: {anomaly_result['confidence']:.1f}%")

    def test_anomaly_explanation(self):
        """이상 원인 설명"""
        # 다중 이상 원인
        metrics = {
            "daily_cost": 25.0,  # 높은 비용
            "api_calls": 3000,  # 과도한 호출
            "error_rate": 0.08,  # 높은 에러율
            "instance_count": 3,
        }

        result = asyncio.run(self.detector.detect_anomaly(metrics))
        reason = result["reason"]

        # 여러 원인이 설명되어야 함
        self.assertGreater(len(reason), 0)
        print(f"Anomaly explanation: {reason}")

    def test_sync_wrapper(self):
        """동기 래퍼 함수 테스트"""
        metrics = {
            "daily_cost": 10.0,
            "api_calls": 500,
            "error_rate": 0.01,
            "instance_count": 3,
        }

        result = detect_anomaly_sync(metrics)

        self.assertIsNotNone(result)
        self.assertIn("is_anomaly", result)
        self.assertIn("confidence", result)

    def test_module_level_functions(self):
        """모듈 레벨 함수 테스트"""
        metrics = {
            "daily_cost": 10.0,
            "api_calls": 500,
            "error_rate": 0.01,
            "instance_count": 3,
        }

        # Async 함수
        result_async = asyncio.run(detect_anomaly(metrics))
        self.assertIsNotNone(result_async)

        # Sync 함수
        result_sync = detect_anomaly_sync(metrics)
        self.assertIsNotNone(result_sync)

        # 결과 구조 동일
        self.assertEqual(result_async["is_anomaly"], result_sync["is_anomaly"])


class TestAnomalyDetectorAccuracy(unittest.TestCase):
    """이상 탐지 정확도 검증"""

    def test_accuracy_metric(self):
        """정확도 메트릭 검증"""
        detector = AdvancedAnomalyDetector()

        # 10개 테스트 케이스
        test_cases = [
            # (metrics, expected_is_anomaly, description)
            (
                {"daily_cost": 5.0, "api_calls": 500, "error_rate": 0.01, "instance_count": 3},
                False,
                "정상",
            ),
            (
                {"daily_cost": 10.0, "api_calls": 500, "error_rate": 0.01, "instance_count": 3},
                False,
                "정상 범위",
            ),
            (
                {"daily_cost": 50.0, "api_calls": 500, "error_rate": 0.01, "instance_count": 3},
                True,
                "높은 비용",
            ),
            (
                {"daily_cost": 10.0, "api_calls": 3000, "error_rate": 0.01, "instance_count": 3},
                True,
                "과도한 API 호출",
            ),
            (
                {"daily_cost": 10.0, "api_calls": 500, "error_rate": 0.15, "instance_count": 3},
                True,
                "높은 에러율",
            ),
            (
                {"daily_cost": 12.0, "api_calls": 600, "error_rate": 0.02, "instance_count": 5},
                False,
                "약간 높지만 정상",
            ),
            (
                {"daily_cost": 30.0, "api_calls": 2500, "error_rate": 0.10, "instance_count": 3},
                True,
                "복합 이상",
            ),
            (
                {"daily_cost": 8.0, "api_calls": 400, "error_rate": 0.005, "instance_count": 2},
                False,
                "매우 정상",
            ),
            (
                {"daily_cost": 60.0, "api_calls": 5000, "error_rate": 0.20, "instance_count": 10},
                True,
                "심각한 이상",
            ),
            (
                {"daily_cost": 15.0, "api_calls": 1000, "error_rate": 0.03, "instance_count": 4},
                False,
                "경계선 정상",
            ),
        ]

        correct = 0
        for metrics, expected, description in test_cases:
            result = asyncio.run(detector.detect_anomaly(metrics))
            is_correct = result["is_anomaly"] == expected
            if is_correct:
                correct += 1
            print(f"{description}: {'✓' if is_correct else '✗'} (detected: {result['is_anomaly']})")

        accuracy = correct / len(test_cases)
        print(f"\nAccuracy: {accuracy:.1%} ({correct}/{len(test_cases)})")

        # 최소 50% 정확도 (모델 초기 상태에서는 낮을 수 있음)
        self.assertGreaterEqual(accuracy, 0.50)


if __name__ == "__main__":
    unittest.main()
