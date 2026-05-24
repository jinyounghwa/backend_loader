"""예산 제어 및 알림 시스템"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class BudgetAlert:
    """예산 알림"""
    account_id: str
    threshold_percentage: int
    severity: str  # 'warning', 'high', 'critical', 'stop'
    current_spend: float
    budget_limit: float
    message: str
    timestamp: str


class BudgetController:
    """AWS 예산 제어 및 알림 시스템"""

    def __init__(self, table):
        """
        Args:
            table: DynamoDB table for budget storage
        """
        self.table = table

    def set_monthly_budget(self, account_id: str, amount: float) -> None:
        """
        월간 예산 설정

        Args:
            account_id: AWS Account ID
            amount: 월간 예산 (USD)
        """
        try:
            item = {
                'account_id': account_id,
                'monthly_budget': amount,
                'set_date': datetime.now(timezone.utc).isoformat(),
                'alerts_enabled': True,
                'auto_remediation': False
            }
            self.table.put_item(Item=item)
            logger.info(f"Monthly budget set for {account_id}: ${amount}")
        except Exception as e:
            logger.error(f"Error setting budget: {str(e)}")

    def get_monthly_budget(self, account_id: str) -> Optional[float]:
        """
        월간 예산 조회

        Args:
            account_id: AWS Account ID

        Returns:
            월간 예산 (USD)
        """
        try:
            response = self.table.get_item(Key={'account_id': account_id})
            item = response.get('Item')
            if item:
                return item.get('monthly_budget')
            return None
        except Exception as e:
            logger.error(f"Error retrieving budget: {str(e)}")
            return None

    def get_remaining_budget(self, account_id: str, current_spend: float) -> Dict:
        """
        남은 예산 조회

        Args:
            account_id: AWS Account ID
            current_spend: 현재까지의 지출

        Returns:
            예산 현황 정보
        """
        try:
            budget = self.get_monthly_budget(account_id)
            if not budget:
                return {}

            remaining = budget - current_spend
            percentage_used = (current_spend / budget * 100) if budget > 0 else 0

            return {
                'budget': budget,
                'spent': current_spend,
                'remaining': remaining,
                'percentage_used': round(percentage_used, 2),
                'burn_rate': self._calculate_burn_rate(account_id, current_spend),
                'days_until_limit': self._calculate_days_until_limit(account_id, current_spend, budget)
            }
        except Exception as e:
            logger.error(f"Error calculating remaining budget: {str(e)}")
            return {}

    def check_budget_alert(self, account_id: str, current_spend: float) -> Optional[BudgetAlert]:
        """
        예산 알림 확인 (기본 80% 임계값)

        Args:
            account_id: AWS Account ID
            current_spend: 현재 지출

        Returns:
            알림 정보 또는 None
        """
        budget = self.get_monthly_budget(account_id)
        if not budget:
            return None

        percentage = (current_spend / budget * 100) if budget > 0 else 0

        if percentage >= 100:
            severity = 'critical'
            message = f"Budget exceeded! Spent ${current_spend:.2f} of ${budget:.2f}"
        elif percentage >= 80:
            severity = 'high'
            message = f"Budget 80% reached: ${current_spend:.2f} of ${budget:.2f}"
        elif percentage >= 50:
            severity = 'warning'
            message = f"Budget 50% reached: ${current_spend:.2f} of ${budget:.2f}"
        else:
            return None

        return BudgetAlert(
            account_id=account_id,
            threshold_percentage=int(percentage),
            severity=severity,
            current_spend=current_spend,
            budget_limit=budget,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def check_budget_alert_at_threshold(self, current_spend: float, budget: float, threshold: int) -> bool:
        """
        특정 임계값에서의 예산 알림 확인

        Args:
            current_spend: 현재 지출
            budget: 예산 한도
            threshold: 임계값 (%)

        Returns:
            알림 발생 여부
        """
        if budget <= 0:
            return False

        percentage = (current_spend / budget * 100)
        return percentage >= threshold

    def set_alert_thresholds(self, account_id: str, thresholds: Dict) -> None:
        """
        알림 임계값 설정

        Args:
            account_id: AWS Account ID
            thresholds: {50: 'warning', 75: 'high', 90: 'critical', 100: 'stop'}
        """
        try:
            item = {
                'account_id': account_id,
                'alert_thresholds': thresholds,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            self.table.put_item(Item=item)
            logger.info(f"Alert thresholds updated for {account_id}")
        except Exception as e:
            logger.error(f"Error setting alert thresholds: {str(e)}")

    def forecast_month_end(self, spent_so_far: float, current_day: int, days_in_month: int = 30) -> Dict:
        """
        월말 비용 예측

        Args:
            spent_so_far: 현재까지의 지출
            current_day: 현재 날짜 (일)
            days_in_month: 월의 총 일수

        Returns:
            예상 월말 지출
        """
        if current_day <= 0:
            return {'projected_total': 0, 'daily_average': 0, 'days_remaining': days_in_month}

        daily_average = spent_so_far / current_day
        projected_total = daily_average * days_in_month
        days_remaining = days_in_month - current_day

        return {
            'projected_total': round(projected_total, 2),
            'daily_average': round(daily_average, 2),
            'days_elapsed': current_day,
            'days_remaining': days_remaining
        }

    def calculate_remaining_budget(self, budget: float, spent: float) -> float:
        """
        남은 예산 계산

        Args:
            budget: 총 예산
            spent: 지출액

        Returns:
            남은 예산
        """
        return max(0, budget - spent)

    def set_auto_remediation(self, account_id: str, enabled: bool) -> None:
        """
        자동 대응 활성화/비활성화

        Args:
            account_id: AWS Account ID
            enabled: 활성화 여부
        """
        try:
            item = {
                'account_id': account_id,
                'auto_remediation': enabled,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            self.table.put_item(Item=item)
            logger.info(f"Auto-remediation {'enabled' if enabled else 'disabled'} for {account_id}")
        except Exception as e:
            logger.error(f"Error setting auto-remediation: {str(e)}")

    def get_auto_remediation_status(self, account_id: str) -> bool:
        """
        자동 대응 상태 조회

        Args:
            account_id: AWS Account ID

        Returns:
            자동 대응 활성화 여부
        """
        try:
            response = self.table.get_item(Key={'account_id': account_id})
            item = response.get('Item')
            if item:
                return item.get('auto_remediation', False)
            return False
        except Exception as e:
            logger.error(f"Error getting auto-remediation status: {str(e)}")
            return False

    def trigger_auto_remediation(self, account_id: str, current_spend: float, budget: float) -> bool:
        """
        자동 대응 실행

        Args:
            account_id: AWS Account ID
            current_spend: 현재 지출
            budget: 예산 한도

        Returns:
            대응 실행 여부
        """
        if not self.get_auto_remediation_status(account_id):
            return False

        percentage = (current_spend / budget * 100) if budget > 0 else 0

        if percentage > 100:
            logger.warning(f"Budget exceeded for {account_id}. Triggering auto-remediation.")
            # 실제 구현: EC2/RDS 종료, 스냅샷 삭제 등
            return True

        return False

    def _calculate_burn_rate(self, account_id: str, current_spend: float) -> float:
        """
        일일 비용 소진 속도 계산 ($/day)

        Args:
            account_id: AWS Account ID
            current_spend: 현재 지출

        Returns:
            일일 소진 속도 ($/day)
        """
        # 시뮬레이션: 30일 기준 일일 평균
        return round(current_spend / 30, 2)

    def _calculate_days_until_limit(self, account_id: str, current_spend: float, budget: float) -> float:
        """
        예산 한도까지 남은 일수 계산

        Args:
            account_id: AWS Account ID
            current_spend: 현재 지출
            budget: 예산 한도

        Returns:
            남은 일수
        """
        if current_spend <= 0 or budget <= current_spend:
            return 0

        daily_rate = current_spend / 30  # 30일 기준
        if daily_rate <= 0:
            return float('inf')

        days_remaining = (budget - current_spend) / daily_rate
        return round(max(0, days_remaining), 1)
