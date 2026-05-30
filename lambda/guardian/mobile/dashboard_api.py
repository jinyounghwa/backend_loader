"""Mobile dashboard API endpoints."""

from typing import Dict, List, Any, Optional
from datetime import datetime


class MobileDashboardAPI:
    """API for mobile dashboard."""

    def __init__(self):
        self.is_cached = False
        self.cache: Dict[str, Any] = {}

    def get_summary(self) -> Dict[str, Any]:
        """Get dashboard summary for mobile."""
        return {
            'threats': {
                'critical': 1,
                'high': 3,
                'medium': 5,
                'low': 10
            },
            'cost_today': 42.50,
            'cost_trend': '+5.2%',
            'ec2_count': 12,
            's3_count': 8,
            'iam_users': 5,
            'last_updated': datetime.utcnow().isoformat()
        }

    def get_threats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent threats."""
        threats = [
            {
                'id': f'threat_{i}',
                'type': 'EC2_UNAUTHORIZED' if i % 2 == 0 else 'S3_PUBLIC',
                'severity': 'CRITICAL' if i == 0 else 'HIGH' if i < 3 else 'MEDIUM',
                'resource': f'i-{12345 + i}' if i % 2 == 0 else f'bucket-{i}',
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'open' if i < 5 else 'resolved'
            }
            for i in range(limit)
        ]

        return threats[:limit]

    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get cost breakdown by service."""
        return {
            'total_today': 42.50,
            'total_month': 1250.75,
            'by_service': {
                'EC2': 28.50,
                'S3': 8.25,
                'RDS': 5.75,
                'Lambda': 0.00
            },
            'by_region': {
                'us-east-1': 25.00,
                'us-west-2': 12.50,
                'eu-west-1': 5.00
            },
            'forecast_month': 1380.00
        }

    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource status."""
        return {
            'running_instances': 12,
            'stopped_instances': 3,
            'public_buckets': 2,
            'private_buckets': 6,
            'security_groups': 5,
            'iam_users': 5,
            'root_account_usage': 0,
            'mfa_enabled_users': 4
        }

    def enable_offline_mode(self) -> None:
        """Enable offline cache mode."""
        self.cache = {
            'summary': self.get_summary(),
            'threats': self.get_threats(),
            'costs': self.get_cost_breakdown(),
            'status': self.get_resource_status()
        }
        self.is_cached = True

    def get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache."""
        if self.is_cached and key in self.cache:
            return self.cache[key]
        return None
