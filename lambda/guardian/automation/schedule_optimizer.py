"""Schedule-based cost optimization."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ScheduleOptimizer:
    """Optimize costs through scheduled actions."""

    def __init__(self):
        """Initialize schedule optimizer."""
        self.schedules = {}

    def create_schedule(
        self,
        schedule_id: str,
        resource_id: str,
        action: str,
        cron_expression: str,
    ) -> bool:
        """Create a scheduled action.
        
        Args:
            schedule_id: Unique schedule ID
            resource_id: AWS resource ID
            action: Action to perform (start/stop)
            cron_expression: Cron expression for scheduling
            
        Returns:
            True if created
        """
        try:
            self.schedules[schedule_id] = {
                'resource_id': resource_id,
                'action': action,
                'cron': cron_expression,
                'is_active': True,
            }
            logger.info(f"Created schedule {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create schedule: {e}")
            return False

    def get_current_time_period(self) -> str:
        """Get current time period for scheduling.
        
        Returns:
            Period name (e.g., 'business_hours', 'off_hours', 'weekend')
        """
        now = datetime.now(timezone.utc)
        hour = now.hour
        weekday = now.weekday()

        if weekday >= 5:  # Saturday or Sunday
            return 'weekend'
        elif 9 <= hour < 17:  # 9am-5pm
            return 'business_hours'
        else:
            return 'off_hours'

    def should_stop_instance(self, instance: Dict[str, Any]) -> bool:
        """Determine if instance should be stopped now.
        
        Args:
            instance: Instance details
            
        Returns:
            True if should stop
        """
        period = self.get_current_time_period()

        # Don't stop during business hours unless tagged for always-off
        if period == 'business_hours':
            tags = instance.get('tags', {})
            return tags.get('Schedule') == 'AlwaysOff'

        # Stop during off-hours unless tagged for always-on
        tags = instance.get('tags', {})
        if tags.get('Schedule') == 'AlwaysOn':
            return False

        return period != 'business_hours'

    def should_start_instance(self, instance: Dict[str, Any]) -> bool:
        """Determine if instance should be started now.
        
        Args:
            instance: Instance details
            
        Returns:
            True if should start
        """
        period = self.get_current_time_period()

        # Start during business hours unless tagged for always-off
        if period == 'business_hours':
            tags = instance.get('tags', {})
            if tags.get('Schedule') == 'AlwaysOff':
                return False
            return True

        return False

    def estimate_monthly_savings(
        self, instances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Estimate monthly savings from schedule optimization.
        
        Args:
            instances: List of instances
            
        Returns:
            Savings estimate
        """
        # Assume instances cost $0.50/hour to run
        hourly_cost_per_instance = 0.50

        # Off-hours per month (estimate 8 hours/day * 20 business days)
        off_hours_per_month = 8 * 20  # 160 hours

        total_instances = len(instances)
        total_savings = total_instances * off_hours_per_month * hourly_cost_per_instance

        return {
            'estimated_monthly_savings': total_savings,
            'instances_optimized': total_instances,
            'hours_saved_per_month': off_hours_per_month,
        }
