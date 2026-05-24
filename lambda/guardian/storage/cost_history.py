"""Cost history tracking for anomaly detection"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Cost history record"""
    account_id: str
    date: str
    daily_cost: float
    service_costs: Dict[str, float]
    timestamp: str


class CostHistoryStorage:

    def __init__(self):
        self.table_name = "guardian-cost-history"
        self._table = None

    @property
    def table(self):
        if self._table is None:
            try:
                self._table = AWSClientProvider.get_resource("dynamodb").Table(self.table_name)
            except Exception as e:
                logger.error("Could not access cost history table: %s", e)
        return self._table

    def save_daily_cost(self, region: str, cost_data: Dict) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        item = {
            "PK": f"REGION#{region}",
            "SK": f"DATE#{today}",
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "cost": float(cost_data.get("today_cost", 0)),
            "monthly_cost": float(cost_data.get("monthly_cost", 0)),
            "increase_percent": float(cost_data.get("increase_percent", 0)),
            "is_anomaly": bool(cost_data.get("is_anomaly", False)),
            "TTL": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
        }
        try:
            if self.table:
                self.table.put_item(Item=item)
        except Exception as e:
            logger.error("Error saving daily cost for %s: %s", region, e)

    def get_cost_history(self, region: str, days: int = 7) -> List[Dict]:
        try:
            if not self.table:
                return []
            from boto3.dynamodb.conditions import Key

            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(f"REGION#{region}"),
                ScanIndexForward=False,
                Limit=days,
            )
            items = response.get("Items", [])
            return sorted(items, key=lambda x: x.get("SK", ""))
        except Exception as e:
            logger.error("Error getting cost history for %s: %s", region, e)
            return []

    def detect_cost_anomaly(self, region: str, today_cost: float) -> Optional[Dict]:
        history = self.get_cost_history(region, days=7)
        if not history or len(history) < 3:
            return None

        costs = [float(item.get("cost", 0)) for item in history[:-1]]
        avg = sum(costs) / len(costs)
        threshold = avg * 1.2

        if today_cost > threshold:
            spike_pct = ((today_cost - avg) / avg) * 100
            daily_impact = today_cost - avg
            return {
                "detected": True,
                "region": region,
                "today_cost": today_cost,
                "7day_avg": avg,
                "threshold": threshold,
                "spike_percent": round(spike_pct, 2),
                "daily_impact": round(daily_impact, 2),
                "confidence": "high" if spike_pct > 30 else "medium",
            }

        return None


class CostHistoryRepository:
    """Repository for managing cost history records"""

    def __init__(self, table):
        self.table = table

    def save_daily_cost(self, account_id: str, date: str, daily_cost: float, service_costs: Dict[str, float]) -> None:
        """Save daily cost record"""
        item = {
            'account_id': account_id,
            'date': date,
            'daily_cost': daily_cost,
            'service_costs': service_costs,
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
        try:
            self.table.put_item(Item=item)
            logger.info(f"Saved daily cost for {account_id} on {date}: ${daily_cost}")
        except Exception as e:
            logger.error(f"Error saving daily cost: {str(e)}")

    def get_daily_cost(self, account_id: str, date: str) -> Optional[Dict]:
        """Get daily cost record for specific date"""
        try:
            response = self.table.get_item(
                Key={'account_id': account_id, 'date': date}
            )
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error getting daily cost: {str(e)}")
            return None

    def get_daily_trend(self, account_id: str, days: int = 7) -> List[Dict]:
        """Get daily cost trend for specified number of days"""
        try:
            response = self.table.query(
                KeyConditionExpression='account_id = :acc',
                ExpressionAttributeValues={':acc': account_id},
                Limit=days,
                ScanIndexForward=False
            )
            items = response.get('Items', [])
            return sorted(items, key=lambda x: x['date'])
        except Exception as e:
            logger.error(f"Error getting daily trend: {str(e)}")
            return []

    def get_weekly_average(self, account_id: str, days: int = 7) -> float:
        """Calculate weekly average cost"""
        try:
            trend = self.get_daily_trend(account_id, days)
            if not trend:
                return 0.0
            total = sum(item['daily_cost'] for item in trend)
            return total / len(trend)
        except Exception as e:
            logger.error(f"Error calculating weekly average: {str(e)}")
            return 0.0

    def detect_cost_anomalies(self, account_id: str, threshold_percent: float = 100) -> List[Dict]:
        """Detect cost spikes exceeding threshold percentage"""
        try:
            trend = self.get_daily_trend(account_id, days=30)
            if len(trend) < 2:
                return []

            spikes = []
            baseline = sum(item['daily_cost'] for item in trend[:-1]) / (len(trend) - 1)

            for item in trend[-1:]:
                spike_percent = ((item['daily_cost'] - baseline) / baseline * 100) if baseline > 0 else 0
                if spike_percent > threshold_percent:
                    spikes.append({
                        'date': item['date'],
                        'daily_cost': item['daily_cost'],
                        'baseline': baseline,
                        'spike_percent': spike_percent
                    })

            return spikes
        except Exception as e:
            logger.error(f"Error detecting cost anomalies: {str(e)}")
            return []

    def detect_sustained_high_cost(self, account_id: str, days: int = 3, threshold: float = 100) -> Optional[Dict]:
        """Detect sustained high cost period"""
        try:
            trend = self.get_daily_trend(account_id, days=30)
            if not trend:
                return None

            high_cost_count = 0
            high_cost_total = 0.0

            for item in trend[-days:]:
                if item['daily_cost'] > threshold:
                    high_cost_count += 1
                    high_cost_total += item['daily_cost']

            if high_cost_count >= days:
                return {
                    'duration_days': high_cost_count,
                    'avg_cost': high_cost_total / high_cost_count,
                    'threshold': threshold
                }

            return None
        except Exception as e:
            logger.error(f"Error detecting sustained high cost: {str(e)}")
            return None

    def get_service_breakdown(self, account_id: str, date: str) -> Dict[str, float]:
        """Get service cost breakdown for specific date"""
        try:
            response = self.table.query(
                KeyConditionExpression='account_id = :acc AND #d = :date',
                ExpressionAttributeNames={'#d': 'date'},
                ExpressionAttributeValues={':acc': account_id, ':date': date}
            )
            items = response.get('Items', [])
            if not items:
                return {}
            return items[0].get('service_costs', {})
        except Exception as e:
            logger.error(f"Error getting service breakdown: {str(e)}")
            return {}

    def project_monthly_cost(self, account_id: str, current_day: int = 5) -> Optional[Dict]:
        """Project monthly cost based on current trend"""
        try:
            trend = self.get_daily_trend(account_id, days=current_day)
            if not trend:
                return None

            daily_average = sum(item['daily_cost'] for item in trend) / len(trend)
            days_in_month = 30
            projected_total = daily_average * days_in_month

            return {
                'projected_total': projected_total,
                'daily_average': daily_average,
                'days_elapsed': current_day,
                'days_remaining': days_in_month - current_day
            }
        except Exception as e:
            logger.error(f"Error projecting monthly cost: {str(e)}")
            return None
