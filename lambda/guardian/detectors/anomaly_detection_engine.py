"""Advanced Anomaly Detection Engine"""

import logging
import statistics
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class AnomalyDetectionEngine:
    """Advanced anomaly detection using statistical methods"""

    def __init__(self, cloudwatch_client, cost_history_table, dynamodb_table):
        """
        Args:
            cloudwatch_client: boto3 CloudWatch client
            cost_history_table: DynamoDB table for cost history
            dynamodb_table: DynamoDB table for anomaly storage
        """
        self.cloudwatch = cloudwatch_client
        self.cost_history_table = cost_history_table
        self.table = dynamodb_table

    def detect_usage_anomalies(self, account_id: str, lookback_days: int = 30) -> List[Dict]:
        """
        Detect usage anomalies using 2-sigma statistical method

        Args:
            account_id: AWS Account ID
            lookback_days: Number of days to look back for analysis

        Returns:
            List of detected anomalies
        """
        try:
            anomalies = []
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=lookback_days)

            # Get CPU usage metrics
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )

            datapoints = response.get('Datapoints', [])
            if len(datapoints) < 5:
                logger.warning(f"Insufficient data for anomaly detection: {len(datapoints)} points")
                return []

            # Extract values
            values = [dp.get('Average', 0) for dp in datapoints]

            # Calculate 2-sigma threshold
            mean = statistics.mean(values)
            if len(values) > 1:
                std_dev = statistics.stdev(values)
            else:
                std_dev = 0

            # Detect anomalies (beyond 2 sigma)
            for i, value in enumerate(values):
                if std_dev > 0 and abs(value - mean) > 2 * std_dev:
                    anomalies.append({
                        'account_id': account_id,
                        'type': 'usage_spike',
                        'value': value,
                        'mean': mean,
                        'std_dev': std_dev,
                        'z_score': (value - mean) / std_dev if std_dev > 0 else 0,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'severity': 'high' if abs(value - mean) > 3 * std_dev else 'medium'
                    })

            logger.info(f"Detected {len(anomalies)} usage anomalies for {account_id}")
            return anomalies

        except Exception as e:
            logger.error(f"Failed to detect usage anomalies: {str(e)}")
            return []

    def detect_cost_spikes(self, account_id: str) -> List[Dict]:
        """
        Detect cost spikes (>20% change from previous day)

        Args:
            account_id: AWS Account ID

        Returns:
            List of detected cost spikes
        """
        try:
            spikes = []

            # Get recent cost history
            response = self.cost_history_table.query(
                KeyConditionExpression='account_id = :acc',
                ExpressionAttributeValues={':acc': account_id},
                Limit=30,
                ScanIndexForward=False
            )

            items = response.get('Items', [])
            if len(items) < 2:
                logger.warning(f"Insufficient cost history for {account_id}")
                return []

            # Sort by date
            sorted_items = sorted(items, key=lambda x: x.get('date', ''))

            # Check for spikes (>20% change)
            for i in range(1, len(sorted_items)):
                prev_cost = float(sorted_items[i-1].get('cost', 0))
                curr_cost = float(sorted_items[i].get('cost', 0))

                if prev_cost > 0:
                    change_percent = abs(curr_cost - prev_cost) / prev_cost * 100
                    if change_percent > 20:
                        spikes.append({
                            'account_id': account_id,
                            'previous_cost': prev_cost,
                            'current_cost': curr_cost,
                            'change_percent': change_percent,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'severity': 'critical' if change_percent > 50 else 'high'
                        })

            logger.info(f"Detected {len(spikes)} cost spikes for {account_id}")
            return spikes

        except Exception as e:
            logger.error(f"Failed to detect cost spikes: {str(e)}")
            return []

    def detect_resource_anomalies(self, account_id: str) -> List[Dict]:
        """
        Detect resource anomalies (high error rates, abnormal metrics)

        Args:
            account_id: AWS Account ID

        Returns:
            List of detected resource anomalies
        """
        try:
            anomalies = []
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=1)

            # Check error rate metrics
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='TargetResponseTime',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average', 'Maximum']
            )

            datapoints = response.get('Datapoints', [])

            if datapoints:
                values = [dp.get('Average', 0) for dp in datapoints]
                if len(values) > 1:
                    mean = statistics.mean(values)
                    std_dev = statistics.stdev(values)

                    # Detect anomalies
                    for value in values:
                        if std_dev > 0 and abs(value - mean) > 2 * std_dev:
                            anomalies.append({
                                'account_id': account_id,
                                'type': 'response_time_anomaly',
                                'value': value,
                                'threshold': mean + 2 * std_dev,
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'severity': 'medium'
                            })

            logger.info(f"Detected {len(anomalies)} resource anomalies for {account_id}")
            return anomalies

        except Exception as e:
            logger.error(f"Failed to detect resource anomalies: {str(e)}")
            return []

    def cluster_anomalies(self, account_id: str, anomalies: List[Dict]) -> List[List[Dict]]:
        """
        Cluster related anomalies within 5-minute temporal windows

        Args:
            account_id: AWS Account ID
            anomalies: List of anomalies to cluster

        Returns:
            List of anomaly clusters
        """
        try:
            if not anomalies:
                return []

            # Sort by timestamp
            sorted_anomalies = sorted(
                anomalies,
                key=lambda x: datetime.fromisoformat(x.get('timestamp', datetime.now(timezone.utc).isoformat()))
            )

            clusters = []
            current_cluster = []
            window_minutes = 5

            for anomaly in sorted_anomalies:
                timestamp = datetime.fromisoformat(anomaly.get('timestamp', datetime.now(timezone.utc).isoformat()))

                if not current_cluster:
                    current_cluster.append(anomaly)
                else:
                    cluster_start = datetime.fromisoformat(
                        current_cluster[0].get('timestamp', datetime.now(timezone.utc).isoformat())
                    )
                    time_diff = (timestamp - cluster_start).total_seconds() / 60

                    if time_diff < window_minutes:
                        current_cluster.append(anomaly)
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [anomaly]

            if current_cluster:
                clusters.append(current_cluster)

            logger.info(f"Clustered {len(anomalies)} anomalies into {len(clusters)} clusters for {account_id}")
            return clusters

        except Exception as e:
            logger.error(f"Failed to cluster anomalies: {str(e)}")
            return []

    def calculate_severity_score(self, account_id: str, anomaly: Dict) -> Dict:
        """
        Calculate severity score for an anomaly

        Args:
            account_id: AWS Account ID
            anomaly: Anomaly data with deviation_percent, affected_resources, potential_impact

        Returns:
            Severity score and classification
        """
        try:
            deviation = anomaly.get('deviation_percent', 0)
            resources = anomaly.get('affected_resources', 1)
            impact = anomaly.get('potential_impact', 'low')

            # Impact weight factors
            impact_weight = {
                'high': 10,
                'medium': 5,
                'low': 2
            }

            weight = impact_weight.get(impact, 2)

            # Calculate base score
            base_score = deviation * (weight / 10)

            # Adjust for number of affected resources
            resource_multiplier = min(1 + (resources / 100), 2)
            final_score = base_score * resource_multiplier

            # Determine severity classification
            if final_score > 75:
                severity = 'critical'
            elif final_score > 50:
                severity = 'high'
            elif final_score > 25:
                severity = 'medium'
            else:
                severity = 'low'

            result = {
                'account_id': account_id,
                'base_score': base_score,
                'final_score': final_score,
                'severity': severity,
                'impact': impact,
                'affected_resources': resources,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Store in DynamoDB
            try:
                self.table.put_item(Item=result)
            except Exception as db_error:
                logger.warning(f"Failed to store severity score: {str(db_error)}")

            logger.info(f"Calculated severity score {final_score} ({severity}) for {account_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate severity score: {str(e)}")
            return {'error': str(e)}
