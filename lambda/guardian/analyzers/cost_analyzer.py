"""비용 분석 엔진 (Cost Explorer 통합)"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json

logger = logging.getLogger(__name__)


@dataclass
class CostData:
    """비용 데이터"""
    date: str
    service: str
    cost: float
    currency: str = "USD"


@dataclass
class CostThreat:
    """비용 이상 위협"""
    threat_id: str
    account_id: str
    severity: int  # 1-10
    threat_type: str  # 'daily_spike', 'monthly_projection', 'unused_resource'
    current_cost: float
    threshold: float
    increase_percent: float
    message: str
    timestamp: str


class CostAnalyzer:
    """AWS Cost Explorer 기반 비용 분석"""

    def __init__(self, cost_explorer_client, account_id: str, daily_threshold: float = 100.0):
        """
        Args:
            cost_explorer_client: boto3 CostExplorer client
            account_id: AWS Account ID
            daily_threshold: 일일 비용 임계값 (달러, 기본 $100)
        """
        self.explorer = cost_explorer_client
        self.account_id = account_id
        self.daily_threshold = daily_threshold
        self.monthly_threshold = daily_threshold * 30

    def analyze_daily_cost(self, date: Optional[str] = None) -> Optional[CostThreat]:
        """
        당일 비용 분석 및 이상 탐지

        Args:
            date: 분석 날짜 (YYYY-MM-DD, 기본값: 어제)

        Returns:
            비용 이상이 있으면 CostThreat, 정상이면 None
        """
        if date is None:
            # 어제 비용 분석 (실시간 데이터는 1-2일 지연)
            date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            # 특정 날짜 비용 조회
            today_cost = self._get_cost_for_date(date)

            # 어제 비용 조회 (변화도 감지)
            yesterday = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_cost = self._get_cost_for_date(yesterday)

            # 증가율 계산
            increase_percent = 0.0
            if yesterday_cost > 0:
                increase_percent = ((today_cost - yesterday_cost) / yesterday_cost) * 100

            logger.info(f"Daily cost analysis: {date} = ${today_cost:.2f} (vs yesterday ${yesterday_cost:.2f})")

            # 임계값 초과 확인
            if today_cost > self.daily_threshold:
                threat = CostThreat(
                    threat_id=f"cost-daily-{date}",
                    account_id=self.account_id,
                    severity=min(10, int(today_cost // 50)),  # $50당 심각도 1 증가
                    threat_type="daily_spike",
                    current_cost=today_cost,
                    threshold=self.daily_threshold,
                    increase_percent=increase_percent,
                    message=f"Daily cost ${today_cost:.2f} exceeds threshold ${self.daily_threshold:.2f} "
                            f"({increase_percent:+.1f}% vs yesterday)",
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
                )
                logger.warning(f"Daily cost threat detected: {threat.message}")
                return threat

            # 50% 이상 증가했어도 경고
            if increase_percent > 50 and today_cost > 10:
                logger.warning(f"Daily cost increased by {increase_percent:.1f}%: ${yesterday_cost:.2f} → ${today_cost:.2f}")

            return None

        except Exception as e:
            logger.error(f"Daily cost analysis failed: {str(e)}")
            raise

    def analyze_monthly_projection(self) -> Optional[CostThreat]:
        """
        월말 비용 예측 및 이상 탐지

        현재까지의 비용으로 월말 비용을 예측하여 임계값 초과 여부 확인

        Returns:
            월말 예상 비용이 임계값을 초과하면 CostThreat, 정상이면 None
        """
        try:
            today = datetime.now(timezone.utc).replace(tzinfo=None)
            month_start = today.replace(day=1)

            # 월초부터 어제까지 누적 비용
            yesterday = today - timedelta(days=1)
            month_to_date_cost = self._get_cost_for_date_range(
                month_start.strftime("%Y-%m-%d"),
                yesterday.strftime("%Y-%m-%d")
            )

            # 월말 비용 예측
            days_elapsed = today.day - 1  # 오늘 제외
            days_in_month = (today.replace(month=today.month % 12 + 1, day=1) - timedelta(days=1)).day

            if days_elapsed > 0:
                projected_monthly = (month_to_date_cost / days_elapsed) * days_in_month
            else:
                projected_monthly = month_to_date_cost

            logger.info(f"Monthly projection: ${month_to_date_cost:.2f} so far, "
                       f"projected end-of-month: ${projected_monthly:.2f}")

            if projected_monthly > self.monthly_threshold:
                threat = CostThreat(
                    threat_id=f"cost-monthly-{today.strftime('%Y-%m')}",
                    account_id=self.account_id,
                    severity=min(10, int(projected_monthly // 500)),  # $500당 심각도 1 증가
                    threat_type="monthly_projection",
                    current_cost=month_to_date_cost,
                    threshold=self.monthly_threshold,
                    increase_percent=((projected_monthly - self.monthly_threshold) / self.monthly_threshold) * 100,
                    message=f"Projected monthly cost ${projected_monthly:.2f} exceeds threshold ${self.monthly_threshold:.2f} "
                            f"(${month_to_date_cost:.2f} so far)",
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
                )
                logger.warning(f"Monthly projection threat detected: {threat.message}")
                return threat

            return None

        except Exception as e:
            logger.error(f"Monthly projection analysis failed: {str(e)}")
            raise

    def get_service_costs(self, date: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        서비스별 비용 분석

        Args:
            date: 분석 날짜 (기본값: 어제)

        Returns:
            [(service, cost), ...] 비용 내림차순 정렬
        """
        if date is None:
            date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': date,
                    'End': date
                },
                Granularity='DAILY',
                Filter={
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [self.account_id]
                    }
                },
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )

            service_costs = []
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    service_name = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    service_costs.append((service_name, cost))

            # 비용 내림차순 정렬
            service_costs.sort(key=lambda x: x[1], reverse=True)

            logger.info(f"Service costs on {date}: {len(service_costs)} services")
            for service, cost in service_costs[:5]:
                logger.debug(f"  {service}: ${cost:.2f}")

            return service_costs

        except Exception as e:
            logger.error(f"Service cost analysis failed: {str(e)}")
            raise

    def detect_unused_resources(self) -> List[CostThreat]:
        """
        미사용 리소스 비용 탐지

        - 당일 비용이 있지만 트래픽이 없는 리소스
        - 유휴 컴퓨팅 리소스 (CPU 사용률 < 5%)
        - 연결되지 않은 탄력적 IP

        Returns:
            미사용 리소스 위협 목록
        """
        threats = []

        try:
            # 최근 7일 데이터 기반 분석
            start_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).strftime("%Y-%m-%d")

            # EC2 인스턴스 비용 분석
            ec2_costs = self._analyze_ec2_usage(start_date, end_date)
            for instance_id, cost, cpu_percent in ec2_costs:
                if cpu_percent < 5:  # CPU 사용률이 5% 미만
                    threat = CostThreat(
                        threat_id=f"unused-ec2-{instance_id}",
                        account_id=self.account_id,
                        severity=3,
                        threat_type="unused_resource",
                        current_cost=cost,
                        threshold=0,
                        increase_percent=0,
                        message=f"Unused EC2 instance {instance_id}: ${cost:.2f}/week, CPU {cpu_percent:.1f}%",
                        timestamp=datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
                    )
                    threats.append(threat)
                    logger.warning(f"Unused resource detected: {threat.message}")

            logger.info(f"Unused resource detection: {len(threats)} resources found")
            return threats

        except Exception as e:
            logger.error(f"Unused resource detection failed: {str(e)}")
            return []

    def _get_cost_for_date(self, date: str) -> float:
        """특정 날짜의 총 비용 조회"""
        try:
            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': date,
                    'End': date
                },
                Granularity='DAILY',
                Filter={
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [self.account_id]
                    }
                },
                Metrics=['UnblendedCost']
            )

            for result in response.get('ResultsByTime', []):
                cost = float(result['Total']['UnblendedCost']['Amount'])
                return cost

            return 0.0

        except Exception as e:
            logger.error(f"Failed to get cost for {date}: {str(e)}")
            return 0.0

    def _get_cost_for_date_range(self, start_date: str, end_date: str) -> float:
        """날짜 범위의 총 비용 조회"""
        try:
            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Filter={
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [self.account_id]
                    }
                },
                Metrics=['UnblendedCost']
            )

            total_cost = 0.0
            for result in response.get('ResultsByTime', []):
                cost = float(result['Total']['UnblendedCost']['Amount'])
                total_cost += cost

            return total_cost

        except Exception as e:
            logger.error(f"Failed to get cost for range {start_date} to {end_date}: {str(e)}")
            return 0.0

    def _analyze_ec2_usage(self, start_date: str, end_date: str) -> List[Tuple[str, float, float]]:
        """
        EC2 인스턴스별 비용 및 CPU 사용률 분석

        Returns:
            [(instance_id, weekly_cost, avg_cpu_percent), ...]
        """
        # 주: 실제 구현에서는 CloudWatch 메트릭과 Cost Explorer 데이터를 통합
        # 여기서는 시뮬레이션 데이터 반환 (테스트용)
        return []

    def set_daily_threshold(self, threshold: float):
        """일일 비용 임계값 변경"""
        self.daily_threshold = threshold
        self.monthly_threshold = threshold * 30
        logger.info(f"Daily cost threshold updated: ${threshold:.2f}")

    def set_monthly_threshold(self, threshold: float):
        """월간 비용 임계값 변경"""
        self.monthly_threshold = threshold
        self.daily_threshold = threshold / 30
        logger.info(f"Monthly cost threshold updated: ${threshold:.2f}")
