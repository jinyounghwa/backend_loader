"""다중계정 비용 통합 및 분석"""

import logging
import csv
import json
import io
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class MultiAccountCostAggregator:
    """다중 AWS 계정 비용 통합 및 분석"""

    def __init__(self, cost_explorer_client):
        """
        Args:
            cost_explorer_client: boto3 CostExplorer client
        """
        self.explorer = cost_explorer_client

    def aggregate_costs(self, account_ids: List[str], date_range: Tuple[str, str]) -> Dict:
        """
        여러 계정의 비용을 통합하여 조회

        Args:
            account_ids: AWS Account ID 목록
            date_range: (start_date, end_date) 튜플

        Returns:
            통합 비용 정보
        """
        try:
            start_date, end_date = date_range
            all_costs = {}
            total_cost = 0.0
            by_service = {}

            for account_id in account_ids:
                cost_data = self._get_account_costs(account_id, start_date, end_date)
                all_costs[account_id] = cost_data

                account_total = cost_data.get('total', 0.0)
                total_cost += account_total

                # 서비스별 통합
                for service, cost in cost_data.get('services', {}).items():
                    by_service[service] = by_service.get(service, 0.0) + cost

            return {
                'accounts': all_costs,
                'total': total_cost,
                'by_service': by_service,
                'date_range': date_range,
                'account_count': len(account_ids)
            }

        except Exception as e:
            logger.error(f"Cost aggregation failed: {str(e)}")
            return {}

    def get_cost_breakdown_by_account(self, date: str) -> Dict:
        """
        특정 날짜의 계정별 비용 분석

        Args:
            date: 분석 날짜 (YYYY-MM-DD)

        Returns:
            계정별 비용 분석
        """
        try:
            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': date,
                    'End': date
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'LINKED_ACCOUNT'
                    }
                ]
            )

            breakdown = {}
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    account_id = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    breakdown[account_id] = cost

            return breakdown

        except Exception as e:
            logger.error(f"Account breakdown analysis failed: {str(e)}")
            return {}

    def compare_account_costs(self, account_id1: str, account_id2: str, days: int = 30) -> Dict:
        """
        두 계정의 비용 비교 분석

        Args:
            account_id1: 첫 번째 계정 ID
            account_id2: 두 번째 계정 ID
            days: 비교 기간 (일)

        Returns:
            비교 분석 결과
        """
        try:
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days)

            cost1 = self._get_account_total_cost(account_id1, start_date.isoformat(), end_date.isoformat())
            cost2 = self._get_account_total_cost(account_id2, start_date.isoformat(), end_date.isoformat())

            difference = cost2 - cost1
            percentage_change = (difference / cost1 * 100) if cost1 > 0 else 0

            return {
                'account_1': {
                    'id': account_id1,
                    'total_cost': cost1
                },
                'account_2': {
                    'id': account_id2,
                    'total_cost': cost2
                },
                'difference': difference,
                'percentage_change': round(percentage_change, 2),
                'higher_account': account_id2 if cost2 > cost1 else account_id1,
                'comparison_period_days': days
            }

        except Exception as e:
            logger.error(f"Account comparison failed: {str(e)}")
            return {}

    def identify_cost_outliers(self, account_ids: List[str]) -> List[Dict]:
        """
        평균에서 벗어난 계정 탐지

        Args:
            account_ids: AWS Account ID 목록

        Returns:
            이상 계정 목록
        """
        try:
            costs = {}
            for account_id in account_ids:
                cost = self._get_account_total_cost(
                    account_id,
                    (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat(),
                    datetime.now(timezone.utc).date().isoformat()
                )
                costs[account_id] = cost

            if len(costs) < 2:
                return []

            cost_values = list(costs.values())
            cost_mean = mean(cost_values)
            cost_stdev = stdev(cost_values) if len(cost_values) > 1 else 0

            outliers = []
            threshold = 2  # 2 표준편차

            for account_id, cost in costs.items():
                deviation = abs(cost - cost_mean)
                if cost_stdev > 0 and deviation > threshold * cost_stdev:
                    outliers.append({
                        'account_id': account_id,
                        'cost': cost,
                        'mean': cost_mean,
                        'deviation': deviation,
                        'deviation_factor': round(deviation / cost_stdev, 2)
                    })

            logger.info(f"Found {len(outliers)} cost outliers")
            return outliers

        except Exception as e:
            logger.error(f"Outlier detection failed: {str(e)}")
            return []

    def get_organization_trends(self, days: int = 90) -> List[Dict]:
        """
        조직 전체 비용 추이

        Args:
            days: 분석 기간 (일)

        Returns:
            일일 비용 추이
        """
        try:
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days)

            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.isoformat(),
                    'End': end_date.isoformat()
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )

            trends = []
            for result in response.get('ResultsByTime', []):
                date = result['TimePeriod']['Start']
                cost = float(result['Total']['UnblendedCost']['Amount'])
                trends.append({
                    'date': date,
                    'cost': cost
                })

            # 성장률 계산
            for i in range(1, len(trends)):
                prev_cost = trends[i-1]['cost']
                curr_cost = trends[i]['cost']
                growth_rate = ((curr_cost - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0
                trends[i]['daily_growth_percent'] = round(growth_rate, 2)

            logger.info(f"Generated {len(trends)} days of organizational trends")
            return trends

        except Exception as e:
            logger.error(f"Trend analysis failed: {str(e)}")
            return []

    def export_cost_report(self, account_ids: List[str], format: str = 'csv') -> bytes:
        """
        비용 보고서 생성 및 내보내기

        Args:
            account_ids: AWS Account ID 목록
            format: 'csv' 또는 'json'

        Returns:
            보고서 데이터 (bytes)
        """
        try:
            report_data = self.aggregate_costs(
                account_ids,
                (
                    (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat(),
                    datetime.now(timezone.utc).date().isoformat()
                )
            )

            if format == 'csv':
                return self._generate_csv_report(report_data)
            elif format == 'json':
                return self._generate_json_report(report_data)
            else:
                return b''

        except Exception as e:
            logger.error(f"Report export failed: {str(e)}")
            return b''

    def _get_account_costs(self, account_id: str, start_date: str, end_date: str) -> Dict:
        """계정 비용 조회"""
        try:
            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                Filter={
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [account_id]
                    }
                }
            )

            total_cost = 0.0
            for result in response.get('ResultsByTime', []):
                total_cost += float(result['Total']['UnblendedCost']['Amount'])

            return {
                'account_id': account_id,
                'total': total_cost,
                'services': {}  # 실제 구현에서는 서비스별 분석
            }

        except Exception as e:
            logger.error(f"Failed to get costs for {account_id}: {str(e)}")
            return {}

    def _get_account_total_cost(self, account_id: str, start_date: str, end_date: str) -> float:
        """계정 총 비용 조회"""
        try:
            response = self.explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                Filter={
                    'Dimensions': {
                        'Key': 'LINKED_ACCOUNT',
                        'Values': [account_id]
                    }
                }
            )

            total = 0.0
            for result in response.get('ResultsByTime', []):
                total += float(result['Total']['UnblendedCost']['Amount'])

            return total

        except Exception as e:
            logger.error(f"Failed to calculate total cost for {account_id}: {str(e)}")
            return 0.0

    def _generate_csv_report(self, report_data: Dict) -> bytes:
        """CSV 형식 보고서 생성"""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['Account ID', 'Total Cost', 'Account Count'])
        for account_id, data in report_data.get('accounts', {}).items():
            writer.writerow([account_id, data.get('total', 0.0), 1])

        writer.writerow([])
        writer.writerow(['Total Organization Cost', report_data.get('total', 0.0)])

        return output.getvalue().encode('utf-8')

    def _generate_json_report(self, report_data: Dict) -> bytes:
        """JSON 형식 보고서 생성"""
        return json.dumps(report_data, indent=2, default=str).encode('utf-8')
