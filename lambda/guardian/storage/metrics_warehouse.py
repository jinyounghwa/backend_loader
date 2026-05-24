"""Metrics Data Warehouse"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class MetricsWarehouse:
    """Store and retrieve time-series metrics"""

    def __init__(self, dynamodb_table, cloudwatch_client):
        self.table = dynamodb_table
        self.cloudwatch = cloudwatch_client

    def store_metric(self, metric: Dict) -> Dict:
        """Store metric in warehouse"""
        try:
            metric_record = {
                'metric_id': f"{metric.get('metric_name')}-{datetime.now(timezone.utc).timestamp()}",
                'metric_name': metric.get('metric_name'),
                'value': metric.get('value'),
                'timestamp': metric.get('timestamp', datetime.now(timezone.utc).isoformat()),
                'dimensions': metric.get('dimensions', {}),
                'stored_at': datetime.now(timezone.utc).isoformat()
            }

            self.table.put_item(Item=metric_record)
            logger.debug(f"Stored metric {metric.get('metric_name')}")
            return metric_record
        except Exception as e:
            logger.error(f"Failed to store metric: {str(e)}")
            return {'error': str(e)}

    def get_timeseries_data(self, metric_name: str, days: int = 7) -> List[Dict]:
        """Get time-series data for metric"""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

            response = self.table.scan(
                FilterExpression='metric_name = :name AND #ts > :cutoff',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':name': metric_name,
                    ':cutoff': cutoff
                }
            )

            items = response.get('Items', [])
            items.sort(key=lambda x: x.get('timestamp', ''))
            logger.debug(f"Retrieved {len(items)} timeseries points for {metric_name}")
            return items
        except Exception as e:
            logger.error(f"Failed to get timeseries data: {str(e)}")
            return []

    def aggregate_metrics_by_dimension(self, metric_name: str, dimension: str) -> Dict:
        """Aggregate metrics by dimension"""
        try:
            timeseries = self.get_timeseries_data(metric_name)

            aggregation = {}
            for item in timeseries:
                dim_value = item.get('dimensions', {}).get(dimension)
                if dim_value:
                    if dim_value not in aggregation:
                        aggregation[dim_value] = []
                    aggregation[dim_value].append(item.get('value', 0))

            return aggregation
        except Exception as e:
            logger.error(f"Failed to aggregate metrics: {str(e)}")
            return {}

    def query_metrics(self, filter_criteria: Dict) -> List[Dict]:
        """Query metrics with filters"""
        try:
            metric_name = filter_criteria.get('metric_name')
            account_id = filter_criteria.get('account_id')

            response = self.table.scan()
            items = response.get('Items', [])

            if metric_name:
                items = [i for i in items if i.get('metric_name') == metric_name]

            if account_id:
                items = [i for i in items if i.get('dimensions', {}).get('account_id') == account_id]

            logger.debug(f"Queried metrics: found {len(items)} items")
            return items
        except Exception as e:
            logger.error(f"Failed to query metrics: {str(e)}")
            return []
