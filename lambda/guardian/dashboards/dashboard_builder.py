"""Custom dashboard builder for AWS Guardian."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
import json


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class DashboardBuilder:
    """Build custom dashboards."""

    def __init__(self):
        self.dashboards: Dict[str, Dict[str, Any]] = {}
        self.versions: Dict[str, List[Dict[str, Any]]] = {}

    def create(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dashboard."""
        dashboard_id = f"dash_{uuid.uuid4().hex[:8]}"

        dashboard = {
            'dashboard_id': dashboard_id,
            'name': config.get('name', 'Untitled'),
            'widgets': config.get('widgets', []),
            'layout': config.get('layout', '2x2'),
            'refresh_interval': config.get('refresh_interval', 60),
            'status': 'active',
            'created_at': now_utc().isoformat(),
            'created_by': config.get('created_by', 'system')
        }

        self.dashboards[dashboard_id] = dashboard
        version_copy = dashboard.copy()
        version_copy['version'] = 0
        self.versions[dashboard_id] = [version_copy]

        return dashboard

    def update_dashboard(self, dashboard_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update dashboard configuration."""
        if dashboard_id not in self.dashboards:
            return {'status': 'not_found', 'dashboard_id': dashboard_id}

        self.dashboards[dashboard_id].update(updates)
        self.dashboards[dashboard_id]['updated_at'] = now_utc().isoformat()

        version_copy = self.dashboards[dashboard_id].copy()
        version_copy['version'] = len(self.versions[dashboard_id])
        self.versions[dashboard_id].append(version_copy)

        return {
            'status': 'updated',
            'dashboard_id': dashboard_id,
            'name': self.dashboards[dashboard_id]['name']
        }

    def delete_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """Delete dashboard."""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            del self.versions[dashboard_id]
            return {'status': 'deleted', 'dashboard_id': dashboard_id}

        return {'status': 'not_found', 'dashboard_id': dashboard_id}

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get dashboard by ID."""
        return self.dashboards.get(dashboard_id)

    def export_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """Export dashboard configuration."""
        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            return {}

        return {
            'name': dashboard['name'],
            'config': {
                'widgets': dashboard['widgets'],
                'layout': dashboard['layout'],
                'refresh_interval': dashboard['refresh_interval']
            },
            'metadata': {
                'created_at': dashboard['created_at'],
                'version': len(self.versions[dashboard_id])
            }
        }

    def import_dashboard(self, import_config: Dict[str, Any]) -> Dict[str, Any]:
        """Import dashboard configuration."""
        return self.create({
            'name': import_config.get('name', 'Imported'),
            'widgets': import_config.get('config', {}).get('widgets', []),
            'layout': import_config.get('config', {}).get('layout', '2x2'),
            'refresh_interval': import_config.get('config', {}).get('refresh_interval', 60)
        })

    def get_versions(self, dashboard_id: str) -> List[Dict[str, Any]]:
        """Get dashboard version history."""
        return self.versions.get(dashboard_id, [])


class WidgetLibrary:
    """Dashboard widget library."""

    WIDGETS = {
        'threat_list': {
            'name': 'Threat List',
            'description': 'Display active threats',
            'config_schema': {'columns': ['severity', 'source', 'timestamp']}
        },
        'cost_chart': {
            'name': 'Cost Chart',
            'description': 'Daily cost trends',
            'config_schema': {'chart_type': 'line', 'period': 30}
        },
        'resource_gauge': {
            'name': 'Resource Usage',
            'description': 'Current resource utilization',
            'config_schema': {'show_percentage': True}
        },
        'compliance_status': {
            'name': 'Compliance Status',
            'description': 'Compliance score by framework',
            'config_schema': {'frameworks': ['PCI_DSS', 'HIPAA', 'SOC2']}
        },
        'incident_timeline': {
            'name': 'Incident Timeline',
            'description': 'Timeline of incidents and responses',
            'config_schema': {'hours_back': 24}
        },
        'ip_reputation': {
            'name': 'IP Reputation',
            'description': 'Top malicious IPs',
            'config_schema': {'top_n': 10}
        }
    }

    def list_widgets(self) -> List[Dict[str, Any]]:
        """List available widgets."""
        return [
            {'name': widget['name'], 'id': widget_id, 'description': widget['description']}
            for widget_id, widget in self.WIDGETS.items()
        ]

    def get_widget(self, widget_id: str) -> Optional[Dict[str, Any]]:
        """Get widget details."""
        widget = self.WIDGETS.get(widget_id)
        if widget:
            return {
                'id': widget_id,
                'name': widget['name'],
                'description': widget['description'],
                'config_schema': widget['config_schema']
            }
        return None

    def create_custom_widget(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom widget from template."""
        widget_id = f"widget_{uuid.uuid4().hex[:8]}"

        return {
            'widget_id': widget_id,
            'name': config.get('name'),
            'type': config.get('type'),
            'config': config.get('config', {}),
            'created_at': now_utc().isoformat()
        }


class DashboardLayout:
    """Dashboard layout management."""

    def apply_template(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply layout template."""
        template = config.get('template', '2x2')
        rows, cols = map(int, template.split('x'))

        return {
            'layout_id': f"layout_{uuid.uuid4().hex[:8]}",
            'template': template,
            'grid_rows': rows,
            'grid_cols': cols,
            'widgets': config.get('widgets', []),
            'created_at': now_utc().isoformat()
        }

    def position_widgets(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Position widgets on dashboard."""
        widgets = config.get('widgets', [])

        positions = []
        for i, widget in enumerate(widgets):
            positions.append({
                'widget': widget,
                'position': f"({widget.get('row', 0)}, {widget.get('col', 0)})"
            })

        return positions

    def create_responsive(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create responsive layout for different screen sizes."""
        return {
            'layout_id': f"responsive_{uuid.uuid4().hex[:8]}",
            'dashboard_id': config.get('dashboard_id'),
            'breakpoints': config.get('breakpoints', {}),
            'created_at': now_utc().isoformat()
        }


class DashboardSharing:
    """Dashboard sharing and permissions."""

    def __init__(self):
        self.permissions: Dict[str, Dict[str, str]] = {}

    def share_dashboard(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Share dashboard with users."""
        dashboard_id = config.get('dashboard_id')
        users = config.get('users', [])
        permission = config.get('permission', 'VIEW')

        if dashboard_id not in self.permissions:
            self.permissions[dashboard_id] = {}

        for user in users:
            self.permissions[dashboard_id][user] = permission

        return {
            'status': 'shared',
            'dashboard_id': dashboard_id,
            'shared_count': len(users),
            'permission': permission
        }

    def set_permissions(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Set granular permissions."""
        dashboard_id = config.get('dashboard_id')
        perms = config.get('permissions', {})

        self.permissions[dashboard_id] = perms

        return {
            'status': 'updated',
            'dashboard_id': dashboard_id,
            'permissions': perms
        }

    def make_public(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Make dashboard publicly shareable."""
        dashboard_id = config.get('dashboard_id')
        share_link = f"https://dashboard.example.com/public/{dashboard_id}"

        self.permissions[dashboard_id] = {'public': 'VIEW'}

        return {
            'status': 'public',
            'dashboard_id': dashboard_id,
            'share_link': share_link,
            'allow_comments': config.get('allow_comments', False)
        }
