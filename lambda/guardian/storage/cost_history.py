"""Cost history tracking for anomaly detection"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from guardian.storage.dynamodb import DynamoDBStorage


class CostHistoryStorage:
    """Track daily costs per region for anomaly detection."""

    def __init__(self):
        self.dynamodb = DynamoDBStorage()
        self.table_name = 'guardian-cost-history'

    def save_daily_cost(self, region: str, cost_data: Dict) -> None:
        """Save daily cost snapshot."""
        today = datetime.utcnow().date().isoformat()
        item = {
            'PK': f'REGION#{region}',
            'SK': f'DATE#{today}',
            'timestamp': int(datetime.utcnow().timestamp()),
            'cost': float(cost_data.get('today_cost', 0)),
            'monthly_cost': float(cost_data.get('monthly_cost', 0)),
            'increase_percent': float(cost_data.get('increase_percent', 0)),
            'is_anomaly': bool(cost_data.get('is_anomaly', False)),
            'TTL': int((datetime.utcnow() + timedelta(days=90)).timestamp()),
        }
        self.dynamodb.put_item(self.table_name, item)

    def get_cost_history(self, region: str, days: int = 7) -> List[Dict]:
        """Get last N days of cost data."""
        try:
            response = self.dynamodb.query(
                self.table_name,
                'PK',
                f'REGION#{region}',
                limit=days,
                scan_forward=False,
            )
            items = response.get('Items', [])
            return sorted(items, key=lambda x: x.get('SK', ''))
        except Exception:
            return []

    def detect_cost_anomaly(self, region: str, today_cost: float) -> Optional[Dict]:
        """Detect cost spike using 7-day rolling average."""
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
