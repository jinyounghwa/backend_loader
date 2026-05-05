"""Cost history tracking for anomaly detection"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)


class CostHistoryStorage:

    def __init__(self):
        self.table_name = 'guardian-cost-history'
        self._table = None

    @property
    def table(self):
        if self._table is None:
            try:
                self._table = AWSClientProvider.get_resource('dynamodb').Table(self.table_name)
            except Exception as e:
                logger.error("Could not access cost history table: %s", e)
        return self._table

    def save_daily_cost(self, region: str, cost_data: Dict) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        item = {
            'PK': f'REGION#{region}',
            'SK': f'DATE#{today}',
            'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'cost': float(cost_data.get('today_cost', 0)),
            'monthly_cost': float(cost_data.get('monthly_cost', 0)),
            'increase_percent': float(cost_data.get('increase_percent', 0)),
            'is_anomaly': bool(cost_data.get('is_anomaly', False)),
            'TTL': int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
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
                KeyConditionExpression=Key('PK').eq(f'REGION#{region}'),
                ScanIndexForward=False,
                Limit=days,
            )
            items = response.get('Items', [])
            return sorted(items, key=lambda x: x.get('SK', ''))
        except Exception as e:
            logger.error("Error getting cost history for %s: %s", region, e)
            return []

    def detect_cost_anomaly(self, region: str, today_cost: float) -> Optional[Dict]:
        history = self.get_cost_history(region, days=7)
        if not history or len(history) < 3:
            return None

        costs = [float(item.get('cost', 0)) for item in history[:-1]]
        avg = sum(costs) / len(costs)
        threshold = avg * 1.2

        if today_cost > threshold:
            spike_pct = ((today_cost - avg) / avg) * 100
            daily_impact = today_cost - avg
            return {
                'detected': True,
                'region': region,
                'today_cost': today_cost,
                '7day_avg': avg,
                'threshold': threshold,
                'spike_percent': round(spike_pct, 2),
                'daily_impact': round(daily_impact, 2),
                'confidence': 'high' if spike_pct > 30 else 'medium',
            }

        return None
