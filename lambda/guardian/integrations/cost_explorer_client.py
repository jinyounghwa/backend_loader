"""Real AWS Cost Explorer API client for cost analysis."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError

from guardian.config import Config

logger = logging.getLogger(__name__)


class CostExplorerClient:
    """AWS Cost Explorer client for real cost queries."""

    def __init__(self, clients: Optional[Dict[str, Any]] = None):
        """Initialize Cost Explorer client.
        
        Args:
            clients: Dict of pre-configured boto3 clients (for testing)
        """
        self.clients = clients or {}
        self._ce_client = self.clients.get("ce")

    @property
    def ce_client(self):
        """Lazy Cost Explorer client."""
        if self._ce_client is None:
            self._ce_client = boto3.client("ce", **Config.get_boto3_kwargs())
        return self._ce_client

    def get_daily_cost(self, date: str) -> float:
        """Get cost for a specific date.
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            Daily cost in USD
        """
        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': date,
                    'End': (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d'),
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
            )
            
            if response['ResultsByTime']:
                cost_str = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
                return float(cost_str)
            return 0.0
        except ClientError as e:
            logger.error(f"Failed to get daily cost: {e}")
            return 0.0

    def get_monthly_cost(self, year: int, month: int) -> float:
        """Get cost for a specific month.
        
        Args:
            year: Year (YYYY)
            month: Month (1-12)
            
        Returns:
            Monthly cost in USD
        """
        try:
            start = f"{year:04d}-{month:02d}-01"
            end_date = datetime(year, month, 1) + timedelta(days=32)
            end_date = end_date.replace(day=1)
            end = end_date.strftime('%Y-%m-%d')
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={'Start': start, 'End': end},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
            )
            
            if response['ResultsByTime']:
                cost_str = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
                return float(cost_str)
            return 0.0
        except ClientError as e:
            logger.error(f"Failed to get monthly cost: {e}")
            return 0.0

    def get_cost_by_service(self, days: int = 7) -> Dict[str, float]:
        """Get cost breakdown by service for last N days.
        
        Args:
            days: Number of days to include
            
        Returns:
            Dict mapping service name to cost
        """
        try:
            end = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={'Start': start, 'End': end},
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            )
            
            service_costs = {}
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    service_costs[service] = service_costs.get(service, 0) + cost
            
            return service_costs
        except ClientError as e:
            logger.error(f"Failed to get service costs: {e}")
            return {}

    def get_cost_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get cost trend for last N days.
        
        Returns:
            List of daily cost records
        """
        try:
            end = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={'Start': start, 'End': end},
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
            )
            
            trend = []
            for result in response['ResultsByTime']:
                cost = float(result['Total']['UnblendedCost']['Amount'])
                trend.append({
                    'date': result['TimePeriod']['Start'],
                    'cost': cost,
                })
            return trend
        except ClientError as e:
            logger.error(f"Failed to get cost trend: {e}")
            return []
