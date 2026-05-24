"""Performance Optimization Engine"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Query performance optimization and recommendations"""

    def __init__(self, cloudwatch_client, dynamodb_table):
        """
        Args:
            cloudwatch_client: boto3 CloudWatch client
            dynamodb_table: DynamoDB table for optimization logs
        """
        self.cloudwatch = cloudwatch_client
        self.table = dynamodb_table
        self.optimization_history = []

    def optimize_query(self, metrics: Dict) -> Dict:
        """
        Analyze query metrics and provide optimization recommendations

        Args:
            metrics: Query metrics (execution_time, data_scanned, result_count)

        Returns:
            Optimization recommendations
        """
        try:
            execution_time = metrics.get('execution_time', 0)
            data_scanned = metrics.get('data_scanned', 0)
            result_count = metrics.get('result_count', 0)

            recommendations = []
            efficiency_score = 100

            # Check execution time
            if execution_time > 5000:
                recommendations.append({
                    'issue': 'Slow query execution',
                    'time_ms': execution_time,
                    'suggestion': 'Add indexes or optimize query logic',
                    'priority': 'high'
                })
                efficiency_score -= 30

            # Check data scanned vs results
            if data_scanned > 0 and result_count > 0:
                efficiency_ratio = result_count / data_scanned
                if efficiency_ratio < 0.1:
                    recommendations.append({
                        'issue': 'Poor query selectivity',
                        'efficiency_ratio': efficiency_ratio,
                        'suggestion': 'Add filtering conditions earlier in query',
                        'priority': 'medium'
                    })
                    efficiency_score -= 20

            # Check result count
            if result_count > 10000:
                recommendations.append({
                    'issue': 'Large result set',
                    'result_count': result_count,
                    'suggestion': 'Implement pagination or add filters',
                    'priority': 'medium'
                })
                efficiency_score -= 15

            # Ensure efficiency score is within bounds
            efficiency_score = max(0, min(100, efficiency_score))

            result = {
                'status': 'optimized' if len(recommendations) == 0 else 'needs_optimization',
                'efficiency_score': efficiency_score,
                'recommendations': recommendations,
                'metrics_analyzed': {
                    'execution_time_ms': execution_time,
                    'data_scanned': data_scanned,
                    'result_count': result_count
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Store optimization log
            try:
                self.table.put_item(Item={
                    'optimization_id': f"{datetime.now(timezone.utc).timestamp()}",
                    'efficiency_score': efficiency_score,
                    'recommendations_count': len(recommendations),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as db_error:
                logger.warning(f"Failed to store optimization log: {str(db_error)}")

            logger.info(f"Query optimization complete: score={efficiency_score}, recommendations={len(recommendations)}")
            return result

        except Exception as e:
            logger.error(f"Failed to optimize query: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def calculate_cache_hit_rate(self, hits: int, misses: int) -> float:
        """
        Calculate cache effectiveness

        Args:
            hits: Number of cache hits
            misses: Number of cache misses

        Returns:
            Hit rate as percentage (0-100)
        """
        try:
            total = hits + misses
            if total == 0:
                return 0.0

            hit_rate = (hits / total) * 100
            logger.info(f"Cache hit rate: {hit_rate:.2f}% ({hits} hits, {misses} misses)")
            return hit_rate

        except Exception as e:
            logger.error(f"Failed to calculate cache hit rate: {str(e)}")
            return 0.0

    def estimate_performance_gain(self, current_time: float, optimized_time: float) -> Dict:
        """
        Estimate performance improvement from optimization

        Args:
            current_time: Current query execution time (ms)
            optimized_time: Expected optimized execution time (ms)

        Returns:
            Performance improvement metrics
        """
        try:
            if current_time <= 0:
                return {'error': 'Invalid current time'}

            time_saved = current_time - optimized_time
            improvement_percent = (time_saved / current_time) * 100

            return {
                'current_time_ms': current_time,
                'optimized_time_ms': optimized_time,
                'time_saved_ms': time_saved,
                'improvement_percent': improvement_percent,
                'status': 'significant' if improvement_percent > 30 else 'moderate' if improvement_percent > 10 else 'minimal'
            }

        except Exception as e:
            logger.error(f"Failed to estimate performance gain: {str(e)}")
            return {'error': str(e)}

    def get_optimization_recommendations(self, query_type: str, account_id: str) -> List[Dict]:
        """
        Get optimization recommendations based on query type

        Args:
            query_type: Type of query (cost, resource, anomaly, etc.)
            account_id: AWS Account ID

        Returns:
            List of recommendations
        """
        try:
            recommendations = []

            # Query-type specific recommendations
            if query_type == 'cost':
                recommendations.append({
                    'type': 'caching',
                    'suggestion': 'Cache daily cost queries for 1 hour',
                    'potential_gain': '80-90% reduction in query time',
                    'priority': 'high'
                })
                recommendations.append({
                    'type': 'aggregation',
                    'suggestion': 'Aggregate costs by day before detailed analysis',
                    'potential_gain': '40-50% data reduction',
                    'priority': 'medium'
                })

            elif query_type == 'resource':
                recommendations.append({
                    'type': 'indexing',
                    'suggestion': 'Create index on account_id and resource_type',
                    'potential_gain': '60-70% query speedup',
                    'priority': 'high'
                })
                recommendations.append({
                    'type': 'partitioning',
                    'suggestion': 'Partition resource table by account_id',
                    'potential_gain': '50-60% improvement',
                    'priority': 'medium'
                })

            elif query_type == 'anomaly':
                recommendations.append({
                    'type': 'caching',
                    'suggestion': 'Cache anomaly detection results for 30 minutes',
                    'potential_gain': '70-80% reduction',
                    'priority': 'high'
                })
                recommendations.append({
                    'type': 'sampling',
                    'suggestion': 'Use statistical sampling for large datasets',
                    'potential_gain': '50-60% speedup',
                    'priority': 'medium'
                })

            logger.info(f"Generated {len(recommendations)} optimization recommendations for {query_type}")
            return recommendations

        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {str(e)}")
            return []
