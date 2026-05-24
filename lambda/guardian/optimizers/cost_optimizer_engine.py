"""Cost Optimization Engine for Right-Sizing and Savings"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CostOptimizerEngine:
    """Analyze resources and generate cost optimization recommendations"""

    def __init__(self, cloudwatch_client):
        """
        Args:
            cloudwatch_client: CloudWatch API client for metrics
        """
        self.cloudwatch = cloudwatch_client

    def analyze_resource_utilization(self, resources: List[Dict]) -> Dict:
        """
        Analyze resource utilization metrics

        Args:
            resources: List of resources with utilization metrics

        Returns:
            Analysis with idle/underutilized resources
        """
        try:
            analysis = {
                'total_resources': len(resources),
                'idle_resources': [],
                'underutilized_resources': [],
                'optimal_resources': [],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            for resource in resources:
                cpu = resource.get('cpu_utilization', 0)
                memory = resource.get('memory_utilization', 0)
                network = resource.get('network_in', 0) + resource.get('network_out', 0)

                # Classify resource utilization
                if cpu < 5 and memory < 10 and network < 100:
                    analysis['idle_resources'].append(resource)
                elif cpu < 20 or memory < 30:
                    analysis['underutilized_resources'].append(resource)
                else:
                    analysis['optimal_resources'].append(resource)

            logger.info(f"Analyzed {len(resources)} resources: {len(analysis['idle_resources'])} idle, "
                       f"{len(analysis['underutilized_resources'])} underutilized")
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze utilization: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def generate_rightsizing_recommendations(self, resource: Dict) -> List[Dict]:
        """
        Generate right-sizing recommendations for resource

        Args:
            resource: Resource with current specs and utilization

        Returns:
            List of sizing recommendations
        """
        try:
            recommendations = []

            cpu = resource.get('cpu_utilization', 0)
            memory = resource.get('memory_utilization', 0)
            resource_type = resource.get('resource_type', '')
            instance_type = resource.get('instance_type', '')
            current_cost = resource.get('monthly_cost', 0)

            # Check for downsize opportunities
            if cpu < 20 and memory < 30:
                recommendation = {
                    'recommendation_type': 'right_size_down',
                    'reason': 'Underutilized: CPU < 20%, Memory < 30%',
                    'suggested_action': f'Downsize from {instance_type} to smaller instance',
                    'estimated_monthly_savings': current_cost * 0.5,
                    'confidence': 0.85
                }
                recommendations.append(recommendation)

            # Check for consolidation opportunities
            if cpu < 10 and memory < 15:
                recommendation = {
                    'recommendation_type': 'consolidate',
                    'reason': 'Severely underutilized: CPU < 10%, Memory < 15%',
                    'suggested_action': 'Consider consolidating to fewer instances',
                    'estimated_monthly_savings': current_cost * 0.7,
                    'confidence': 0.9
                }
                recommendations.append(recommendation)

            logger.info(f"Generated {len(recommendations)} recommendations for {resource.get('resource_id')}")
            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            return []

    def estimate_annual_savings(self, optimizations: List[Dict]) -> float:
        """
        Estimate total annual savings from optimizations

        Args:
            optimizations: List of optimization records

        Returns:
            Total annual savings amount
        """
        try:
            total_monthly_savings = 0.0

            for optimization in optimizations:
                monthly_savings = optimization.get('monthly_savings', 0)
                total_monthly_savings += monthly_savings

            annual_savings = total_monthly_savings * 12

            logger.info(f"Estimated annual savings: ${annual_savings:.2f}")
            return annual_savings

        except Exception as e:
            logger.error(f"Failed to estimate savings: {str(e)}")
            return 0.0

    def track_optimization_impact(self, optimization: Dict) -> Dict:
        """
        Track impact of implemented optimization

        Args:
            optimization: Optimization with before/after metrics

        Returns:
            Impact tracking record
        """
        try:
            impact = {
                'optimization_id': optimization.get('optimization_id'),
                'resource_id': optimization.get('resource_id'),
                'status': optimization.get('status', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Calculate savings if before/after costs available
            pre_cost = optimization.get('pre_optimization_cost', 0)
            post_cost = optimization.get('post_optimization_cost', 0)

            if pre_cost > 0:
                monthly_savings = pre_cost - post_cost
                impact['monthly_savings'] = monthly_savings
                impact['annual_savings'] = monthly_savings * 12
                impact['savings_percentage'] = (monthly_savings / pre_cost * 100)

            logger.info(f"Tracked optimization {optimization.get('optimization_id')}: "
                       f"${impact.get('monthly_savings', 0):.2f}/month savings")
            return impact

        except Exception as e:
            logger.error(f"Failed to track impact: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def calculate_roi_for_optimization(self, optimization: Dict) -> Dict:
        """
        Calculate ROI for optimization

        Args:
            optimization: Optimization with cost and savings

        Returns:
            ROI calculation result
        """
        try:
            implementation_cost = optimization.get('implementation_cost', 0)
            annual_savings = optimization.get('annual_savings', 0)

            if implementation_cost <= 0:
                roi = 0
            else:
                roi = (annual_savings - implementation_cost) / implementation_cost * 100

            result = {
                'implementation_cost': implementation_cost,
                'annual_savings': annual_savings,
                'roi_percentage': round(roi, 2),
                'payback_months': (implementation_cost / (annual_savings / 12)) if annual_savings > 0 else 0,
                'status': 'good_roi' if roi > 100 else 'moderate_roi' if roi > 50 else 'low_roi'
            }

            logger.info(f"Calculated ROI: {roi:.2f}%")
            return result

        except Exception as e:
            logger.error(f"Failed to calculate ROI: {str(e)}")
            return {'error': str(e), 'status': 'failed'}
