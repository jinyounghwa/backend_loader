"""Sprint 69 Phase 4: Community Plugin Marketplace (13 tests)"""

import pytest


class TestPluginRegistry:
    """Test plugin registration."""

    def test_register_plugin(self):
        """✅ Register plugin in marketplace."""
        from guardian.marketplace.plugin_manager import PluginRegistry

        registry = PluginRegistry()
        plugin = {
            'name': 'cost-anomaly-detector',
            'version': '1.0.0',
            'author': 'john@example.com',
            'description': 'Detect cost anomalies',
            'dependencies': ['guardian-core>=2.0']
        }

        result = registry.register(plugin)

        assert result is True
        assert registry.get_plugin('cost-anomaly-detector') is not None

    def test_list_plugins(self):
        """✅ List all plugins."""
        from guardian.marketplace.plugin_manager import PluginRegistry

        registry = PluginRegistry()
        registry.register({'name': 'plugin-a', 'version': '1.0.0'})
        registry.register({'name': 'plugin-b', 'version': '2.0.0'})

        plugins = registry.list_plugins()

        assert len(plugins) == 2

    def test_search_plugins(self):
        """✅ Search plugins by name/description."""
        from guardian.marketplace.plugin_manager import PluginRegistry

        registry = PluginRegistry()
        registry.register({
            'name': 'cost-optimizer',
            'description': 'Optimize AWS costs'
        })
        registry.register({
            'name': 'security-checker',
            'description': 'Check security'
        })

        results = registry.search('cost')

        assert len(results) == 1
        assert results[0]['name'] == 'cost-optimizer'


class TestPluginInstallation:
    """Test plugin installation."""

    def test_install_plugin(self):
        """✅ Install plugin."""
        from guardian.marketplace.plugin_manager import PluginInstaller

        installer = PluginInstaller()
        result = installer.install('my-plugin', '1.0.0')

        assert result is True
        assert installer.get_installed()['my-plugin'] == '1.0.0'

    def test_uninstall_plugin(self):
        """✅ Uninstall plugin."""
        from guardian.marketplace.plugin_manager import PluginInstaller

        installer = PluginInstaller()
        installer.install('my-plugin', '1.0.0')
        result = installer.uninstall('my-plugin')

        assert result is True
        assert 'my-plugin' not in installer.get_installed()

    def test_list_installed_plugins(self):
        """✅ List installed plugins."""
        from guardian.marketplace.plugin_manager import PluginInstaller

        installer = PluginInstaller()
        installer.install('plugin-a', '1.0.0')
        installer.install('plugin-b', '2.0.0')

        installed = installer.get_installed()

        assert len(installed) == 2


class TestVersionManagement:
    """Test plugin versioning."""

    def test_save_version(self):
        """✅ Save plugin version."""
        from guardian.marketplace.plugin_manager import VersionManager

        manager = VersionManager()
        result = manager.save_version('my-plugin', '1.0.0', {'code': 'print("v1")'})

        assert result is True

    def test_list_versions(self):
        """✅ List all versions of plugin."""
        from guardian.marketplace.plugin_manager import VersionManager

        manager = VersionManager()
        manager.save_version('my-plugin', '1.0.0', {})
        manager.save_version('my-plugin', '1.1.0', {})

        versions = manager.list_versions('my-plugin')

        assert len(versions) == 2

    def test_get_specific_version(self):
        """✅ Get specific plugin version."""
        from guardian.marketplace.plugin_manager import VersionManager

        manager = VersionManager()
        manager.save_version('my-plugin', '1.0.0', {'code': 'v1'})
        manager.save_version('my-plugin', '1.1.0', {'code': 'v2'})

        version = manager.get_version('my-plugin', '1.0.0')

        assert version is not None
        assert version['version'] == '1.0.0'


class TestDependencyResolution:
    """Test plugin dependency resolution."""

    def test_resolve_dependencies(self):
        """✅ Resolve plugin dependencies."""
        from guardian.marketplace.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        plugins = {
            'plugin-a': {'dependencies': ['plugin-b', 'plugin-c']},
            'plugin-b': {'dependencies': ['plugin-c']},
            'plugin-c': {'dependencies': []}
        }

        order = resolver.resolve(plugins)

        # topological sort: no dependencies first
        assert len(order) == 3
        assert order[0] == 'plugin-c'  # no deps
        assert order[1] == 'plugin-b'  # depends on c
        assert order[2] == 'plugin-a'  # depends on b, c

    def test_detect_circular_dependencies(self):
        """✅ Detect circular dependencies."""
        from guardian.marketplace.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        plugins = {
            'plugin-a': {'dependencies': ['plugin-b']},
            'plugin-b': {'dependencies': ['plugin-a']}
        }

        cycles = resolver.detect_cycles(plugins)

        assert len(cycles) > 0

    def test_resolve_complex_dependency_chain(self):
        """✅ Resolve complex multi-level dependencies."""
        from guardian.marketplace.dependency_resolver import DependencyResolver

        resolver = DependencyResolver()
        plugins = {
            'plugin-a': {'dependencies': ['plugin-b', 'plugin-c']},
            'plugin-b': {'dependencies': ['plugin-d']},
            'plugin-c': {'dependencies': ['plugin-d']},
            'plugin-d': {'dependencies': []}
        }

        order = resolver.resolve(plugins)

        # plugin-d has no dependencies, so it comes first
        assert len(order) == 4
        assert order[0] == 'plugin-d'
        assert order.index('plugin-d') < order.index('plugin-b')
        assert order.index('plugin-d') < order.index('plugin-c')
        assert order.index('plugin-b') < order.index('plugin-a')
        assert order.index('plugin-c') < order.index('plugin-a')


class TestMarketplaceRatings:
    """Test plugin rating system."""

    def test_add_rating(self):
        """✅ Add rating to plugin."""
        from guardian.storage.plugin_store import RatingStore

        store = RatingStore()
        result = store.add_rating('plugin-1', 5, 'user@example.com')

        assert result is True

    def test_calculate_average_rating(self):
        """✅ Calculate average plugin rating."""
        from guardian.storage.plugin_store import RatingStore

        store = RatingStore()
        store.add_rating('plugin-1', 5, 'user1@example.com')
        store.add_rating('plugin-1', 3, 'user2@example.com')

        avg = store.get_average_rating('plugin-1')

        assert avg == 4.0

    def test_rating_count(self):
        """✅ Get number of ratings."""
        from guardian.storage.plugin_store import RatingStore

        store = RatingStore()
        store.add_rating('plugin-1', 5, 'user1@example.com')
        store.add_rating('plugin-1', 4, 'user2@example.com')

        count = store.get_rating_count('plugin-1')

        assert count == 2
