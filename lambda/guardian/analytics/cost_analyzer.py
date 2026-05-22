"""
비용 분석기 - 월별 추세, 이상 탐지, 예측 분석
"""

import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Any
from guardian.ml.anomaly_detector_v2 import AdvancedAnomalyDetector


class CostAnalyzer:
    """비용 데이터 분석 및 예측"""

    def __init__(self):
        self.detector = AdvancedAnomalyDetector()
        self.history: List[Dict[str, Any]] = []

    async def generate_monthly_report(
        self,
        account_id: str,
        daily_costs: List[float],
        month: str
    ) -> Dict[str, Any]:
        """
        월별 비용 추이 분석 리포트 생성

        Args:
            account_id: AWS 계정 ID
            daily_costs: 일별 비용 배열 (30일)
            month: YYYY-MM 형식
        """
        if not daily_costs:
            return self._empty_report(month)

        total_cost = sum(daily_costs)
        daily_average = total_cost / len(daily_costs)

        # 트렌드 분석
        trend = self._analyze_trend(daily_costs)

        # 이상 탐지
        anomalies = await self._detect_cost_anomalies(daily_costs)

        # 카테고리별 분석 (시뮬레이션)
        breakdown = self._get_category_breakdown(daily_costs)

        # 예측
        forecast = self._forecast_next_month(daily_costs)

        return {
            "month": month,
            "account_id": account_id,
            "total_cost": round(total_cost, 2),
            "daily_average": round(daily_average, 2),
            "daily_min": round(min(daily_costs), 2),
            "daily_max": round(max(daily_costs), 2),
            "trend": trend,
            "anomalies": anomalies,
            "breakdown": breakdown,
            "forecast_next_month": forecast,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _detect_cost_anomalies(
        self,
        daily_costs: List[float]
    ) -> List[Dict[str, Any]]:
        """비용 이상 감지"""
        anomalies = []
        avg = sum(daily_costs) / len(daily_costs)
        std = np.std(daily_costs)

        for i, cost in enumerate(daily_costs):
            # 평균 + 2 표준편차 이상 = 이상
            if cost > avg + 2 * std:
                anomalies.append({
                    "day": i + 1,
                    "cost": round(cost, 2),
                    "expected": round(avg, 2),
                    "deviation": round(cost - avg, 2),
                    "severity": "high" if cost > avg + 3 * std else "medium",
                })

        return anomalies

    def _analyze_trend(self, daily_costs: List[float]) -> Dict[str, Any]:
        """비용 추이 분석"""
        if len(daily_costs) < 5:
            return {"trend": "insufficient_data", "slope": 0}

        x = np.arange(len(daily_costs)).reshape(-1, 1)
        y = np.array(daily_costs)

        try:
            coefficients = np.polyfit(x.flatten(), y, 1)
            slope = coefficients[0]

            if slope > 1.0:
                trend_name = "rapidly_increasing"
            elif slope > 0.3:
                trend_name = "gradually_increasing"
            elif slope < -0.3:
                trend_name = "decreasing"
            else:
                trend_name = "stable"

            # 추세선 피팅
            trend_values = [coefficients[0] * i + coefficients[1] for i in range(len(daily_costs))]

            return {
                "trend": trend_name,
                "slope": round(slope, 2),
                "daily_change": round(slope, 2),
                "confidence": "high" if len(daily_costs) >= 20 else "medium",
                "trend_line": [round(v, 2) for v in trend_values],
            }
        except Exception as e:
            return {"trend": "error", "error": str(e), "slope": 0}

    def _get_category_breakdown(self, daily_costs: List[float]) -> Dict[str, Any]:
        """카테고리별 비용 분석 (시뮬레이션)"""
        total = sum(daily_costs)

        # 시뮬레이션 데이터 (실제로는 AWS Cost Explorer에서 가져옴)
        breakdown = {
            "EC2": round(total * 0.35, 2),
            "S3": round(total * 0.20, 2),
            "RDS": round(total * 0.15, 2),
            "Lambda": round(total * 0.10, 2),
            "Other": round(total * 0.20, 2),
        }

        # 비율 계산
        percentages = {k: round((v / total) * 100, 1) for k, v in breakdown.items()}

        return {
            "by_service": breakdown,
            "percentages": percentages,
            "top_service": max(breakdown, key=breakdown.get),
        }

    def _forecast_next_month(self, daily_costs: List[float]) -> Dict[str, Any]:
        """다음 달 비용 예측"""
        if len(daily_costs) < 7:
            return {
                "forecast": round(sum(daily_costs), 2),
                "lower_bound": round(sum(daily_costs) * 0.9, 2),
                "upper_bound": round(sum(daily_costs) * 1.1, 2),
                "confidence": "low",
            }

        # 선형 회귀를 통한 예측
        avg = sum(daily_costs) / len(daily_costs)

        # 추세 계산
        x = np.arange(len(daily_costs))
        y = np.array(daily_costs)
        coefficients = np.polyfit(x, y, 1)

        # 다음 달 예측 (30일)
        predicted_daily = coefficients[0] * len(daily_costs) + coefficients[1]

        # 음수 방지
        predicted_daily = max(predicted_daily, avg * 0.8)

        forecast_total = predicted_daily * 30

        return {
            "forecast": round(forecast_total, 2),
            "daily_average": round(predicted_daily, 2),
            "lower_bound": round(forecast_total * 0.85, 2),
            "upper_bound": round(forecast_total * 1.15, 2),
            "confidence": "medium",
            "basis": "linear_regression",
        }

    def _empty_report(self, month: str) -> Dict[str, Any]:
        """빈 리포트"""
        return {
            "month": month,
            "total_cost": 0,
            "daily_average": 0,
            "trend": "no_data",
            "anomalies": [],
            "breakdown": {},
            "forecast_next_month": {"forecast": 0},
        }


# 전역 분석기 인스턴스
_analyzer = CostAnalyzer()


async def generate_monthly_report(
    account_id: str,
    daily_costs: List[float],
    month: str
) -> Dict[str, Any]:
    """월별 리포트 생성 (async)"""
    return await _analyzer.generate_monthly_report(account_id, daily_costs, month)


def generate_monthly_report_sync(
    account_id: str,
    daily_costs: List[float],
    month: str
) -> Dict[str, Any]:
    """월별 리포트 생성 (sync)"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(
        _analyzer.generate_monthly_report(account_id, daily_costs, month)
    )
    loop.close()
    return result
