"""Custom dashboard tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestDashboardBuilder:
    """Test custom dashboard creation."""

    def test_create_custom_dashboard(self):
        """✅ Create custom dashboard."""
        from guardian.dashboards.dashboard_builder import DashboardBuilder

        builder = DashboardBuilder()

        dashboard = builder.create({
            'name': 'Security Team Dashboard',
            'widgets': ['threats', 'costs', 'resources'],
            'layout': '2x2'
        })

        assert 'dashboard_id' in dashboard
        assert dashboard['name'] == 'Security Team Dashboard'
        assert 'created_at' in dashboard
        assert dashboard['status'] == 'active'

    def test_create_dashboard_with_custom_widgets(self):
        """✅ Create dashboard with custom widget configuration."""
        from guardian.dashboards.dashboard_builder import DashboardBuilder

        builder = DashboardBuilder()

        dashboard = builder.create({
            'name': 'Ops Dashboard',
            'widgets': [
                {'type': 'threat_list', 'position': 0},
                {'type': 'cost_chart', 'position': 1},
                {'type': 'resource_gauge', 'position': 2}
            ],
            'refresh_interval': 60
        })

        assert dashboard['dashboard_id']
        assert dashboard['refresh_interval'] == 60

    def test_update_dashboard(self):
        """✅ Update dashboard configuration."""
        from guardian.dashboards.dashboard_builder import DashboardBuilder

        builder = DashboardBuilder()

        # Create dashboard
        dashboard = builder.create({
            'name': 'Original Dashboard',
            'widgets': ['threats']
        })
        dashboard_id = dashboard['dashboard_id']

        # Update dashboard
        updated = builder.update_dashboard(dashboard_id, {
            'name': 'Updated Dashboard',
            'widgets': ['threats', 'costs']
        })

        assert updated['status'] == 'updated'
        assert updated['name'] == 'Updated Dashboard'

    def test_delete_dashboard(self):
        """✅ Delete dashboard."""
        from guardian.dashboards.dashboard_builder import DashboardBuilder

        builder = DashboardBuilder()

        dashboard = builder.create({
            'name': 'Temp Dashboard',
            'widgets': ['threats']
        })
        dashboard_id = dashboard['dashboard_id']

        result = builder.delete_dashboard(dashboard_id)

        assert result['status'] == 'deleted'
        assert builder.get_dashboard(dashboard_id) is None


class TestWidgetLibrary:
    """Test dashboard widget library."""

    def test_list_available_widgets(self):
        """✅ List available widgets."""
        from guardian.dashboards.dashboard_builder import WidgetLibrary

        library = WidgetLibrary()

        widgets = library.list_widgets()

        assert isinstance(widgets, list)
        assert len(widgets) >= 5
        assert all('name' in w for w in widgets)

    def test_get_widget_details(self):
        """✅ Get widget details and configuration."""
        from guardian.dashboards.dashboard_builder import WidgetLibrary

        library = WidgetLibrary()

        widget = library.get_widget('threat_list')

        assert widget is not None
        assert 'name' in widget
        assert 'description' in widget
        assert 'config_schema' in widget

    def test_custom_widget_creation(self):
        """✅ Create custom widget from template."""
        from guardian.dashboards.dashboard_builder import WidgetLibrary

        library = WidgetLibrary()

        custom_widget = library.create_custom_widget({
            'name': 'Custom Threat Widget',
            'type': 'threat_list',
            'config': {'columns': ['severity', 'source']}
        })

        assert 'widget_id' in custom_widget
        assert custom_widget['name'] == 'Custom Threat Widget'


class TestDashboardLayout:
    """Test dashboard layout management."""

    def test_apply_layout_template(self):
        """✅ Apply layout template to dashboard."""
        from guardian.dashboards.dashboard_builder import DashboardLayout

        layout = DashboardLayout()

        dashboard_layout = layout.apply_template({
            'dashboard_id': 'dash_123',
            'template': '2x2',
            'widgets': ['threats', 'costs', 'resources', 'compliance']
        })

        assert 'layout_id' in dashboard_layout
        assert dashboard_layout['grid_rows'] == 2
        assert dashboard_layout['grid_cols'] == 2

    def test_custom_widget_positioning(self):
        """✅ Position widgets on dashboard."""
        from guardian.dashboards.dashboard_builder import DashboardLayout

        layout = DashboardLayout()

        positions = layout.position_widgets({
            'dashboard_id': 'dash_123',
            'widgets': [
                {'type': 'threat_list', 'row': 0, 'col': 0},
                {'type': 'cost_chart', 'row': 0, 'col': 1},
                {'type': 'resources', 'row': 1, 'col': 0}
            ]
        })

        assert len(positions) == 3
        assert all('position' in p for p in positions)

    def test_responsive_layout(self):
        """✅ Responsive layout for different screen sizes."""
        from guardian.dashboards.dashboard_builder import DashboardLayout

        layout = DashboardLayout()

        responsive = layout.create_responsive({
            'dashboard_id': 'dash_123',
            'breakpoints': {
                'mobile': '1x2',
                'tablet': '2x2',
                'desktop': '3x3'
            }
        })

        assert 'breakpoints' in responsive
        assert 'mobile' in responsive['breakpoints']


class TestDashboardSharing:
    """Test dashboard sharing and permissions."""

    def test_share_dashboard_with_users(self):
        """✅ Share dashboard with team members."""
        from guardian.dashboards.dashboard_builder import DashboardSharing

        sharing = DashboardSharing()

        result = sharing.share_dashboard({
            'dashboard_id': 'dash_123',
            'users': ['user1@example.com', 'user2@example.com'],
            'permission': 'VIEW'
        })

        assert result['status'] == 'shared'
        assert result['shared_count'] == 2

    def test_set_dashboard_permissions(self):
        """✅ Set granular dashboard permissions."""
        from guardian.dashboards.dashboard_builder import DashboardSharing

        sharing = DashboardSharing()

        perms = sharing.set_permissions({
            'dashboard_id': 'dash_123',
            'permissions': {
                'user1@example.com': 'EDIT',
                'user2@example.com': 'VIEW',
                'group@example.com': 'VIEW'
            }
        })

        assert perms['status'] == 'updated'
        assert len(perms['permissions']) == 3

    def test_make_dashboard_public(self):
        """✅ Make dashboard publicly shareable."""
        from guardian.dashboards.dashboard_builder import DashboardSharing

        sharing = DashboardSharing()

        result = sharing.make_public({
            'dashboard_id': 'dash_123',
            'allow_comments': True
        })

        assert result['status'] == 'public'
        assert 'share_link' in result


class TestDashboardIntegration:
    """End-to-end dashboard workflows."""

    def test_complete_dashboard_workflow(self):
        """✅ Complete dashboard creation and sharing workflow."""
        from guardian.dashboards.dashboard_builder import (
            DashboardBuilder,
            DashboardSharing,
            DashboardLayout
        )

        builder = DashboardBuilder()
        sharing = DashboardSharing()
        layout = DashboardLayout()

        # Step 1: Create dashboard
        dashboard = builder.create({
            'name': 'Team Dashboard',
            'widgets': ['threats', 'costs', 'compliance']
        })

        dashboard_id = dashboard['dashboard_id']

        # Step 2: Apply layout
        layout_result = layout.apply_template({
            'dashboard_id': dashboard_id,
            'template': '3x1'
        })

        assert layout_result['layout_id']

        # Step 3: Share dashboard
        share_result = sharing.share_dashboard({
            'dashboard_id': dashboard_id,
            'users': ['team@example.com'],
            'permission': 'EDIT'
        })

        assert share_result['status'] == 'shared'

    def test_dashboard_with_dynamic_data(self):
        """✅ Dashboard updates with real-time data."""
        from guardian.dashboards.dashboard_builder import DashboardBuilder

        builder = DashboardBuilder()

        dashboard = builder.create({
            'name': 'Live Dashboard',
            'widgets': ['threats', 'costs'],
            'refresh_interval': 30
        })

        assert dashboard['refresh_interval'] == 30
        assert dashboard['status'] == 'active'

    def test_dashboard_export(self):
        """✅ Export dashboard configuration."""
        from guardian.dashboards.dashboard_builder import DashboardBuilder

        builder = DashboardBuilder()

        dashboard = builder.create({
            'name': 'Export Dashboard',
            'widgets': ['threats', 'costs']
        })

        exported = builder.export_dashboard(dashboard['dashboard_id'])

        assert 'config' in exported
        assert 'metadata' in exported
        assert exported['name'] == 'Export Dashboard'

    def test_dashboard_import(self):
        """✅ Import dashboard configuration."""
        from guardian.dashboards.dashboard_builder import DashboardBuilder

        builder = DashboardBuilder()

        # Export first
        dashboard = builder.create({
            'name': 'Original',
            'widgets': ['threats']
        })
        exported = builder.export_dashboard(dashboard['dashboard_id'])

        # Import as new
        imported = builder.import_dashboard({
            'name': 'Imported Dashboard',
            'config': exported['config']
        })

        assert imported['dashboard_id']
        assert imported['name'] == 'Imported Dashboard'

    def test_dashboard_versioning(self):
        """✅ Track dashboard configuration versions."""
        from guardian.dashboards.dashboard_builder import DashboardBuilder

        builder = DashboardBuilder()

        dashboard = builder.create({
            'name': 'Versioned Dashboard',
            'widgets': ['threats']
        })

        # Update dashboard
        builder.update_dashboard(dashboard['dashboard_id'], {
            'widgets': ['threats', 'costs']
        })

        # Get versions
        versions = builder.get_versions(dashboard['dashboard_id'])

        assert len(versions) >= 1
        assert all('version' in v for v in versions)

    def test_dashboard_collaboration(self):
        """✅ Multiple users editing same dashboard."""
        from guardian.dashboards.dashboard_builder import (
            DashboardBuilder,
            DashboardSharing
        )

        builder = DashboardBuilder()
        sharing = DashboardSharing()

        dashboard = builder.create({
            'name': 'Collab Dashboard',
            'widgets': ['threats']
        })

        # Share with edit permission
        sharing.set_permissions({
            'dashboard_id': dashboard['dashboard_id'],
            'permissions': {
                'user1@example.com': 'EDIT',
                'user2@example.com': 'EDIT'
            }
        })

        # Both users can update
        updated = builder.update_dashboard(
            dashboard['dashboard_id'],
            {'widgets': ['threats', 'costs']}
        )

        assert updated['status'] == 'updated'
