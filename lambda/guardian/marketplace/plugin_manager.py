"""Plugin marketplace manager: Registration, installation, versioning"""

from typing import Dict, List, Optional
from datetime import datetime


class PluginRegistry:
    """Manage plugin registry."""

    def __init__(self):
        self.plugins: Dict[str, Dict] = {}

    def register(self, plugin: Dict) -> bool:
        """Register plugin in marketplace."""
        plugin_name = plugin.get('name')
        if not plugin_name:
            return False

        self.plugins[plugin_name] = {
            'name': plugin_name,
            'version': plugin.get('version', '1.0.0'),
            'author': plugin.get('author'),
            'description': plugin.get('description'),
            'dependencies': plugin.get('dependencies', []),
            'downloads': 0,
            'rating': 0.0,
            'registered_at': datetime.utcnow().isoformat()
        }
        return True

    def get_plugin(self, name: str) -> Optional[Dict]:
        """Get plugin by name."""
        return self.plugins.get(name)

    def list_plugins(self) -> List[Dict]:
        """List all plugins."""
        return list(self.plugins.values())

    def search(self, query: str) -> List[Dict]:
        """Search plugins by name/description."""
        results = []
        for plugin in self.plugins.values():
            if (query.lower() in plugin['name'].lower() or
                query.lower() in plugin['description'].lower()):
                results.append(plugin)
        return results


class PluginInstaller:
    """Install and manage plugins."""

    def __init__(self):
        self.installed_plugins: Dict[str, str] = {}

    def install(self, plugin_name: str, version: str) -> bool:
        """Install plugin."""
        if not plugin_name:
            return False

        self.installed_plugins[plugin_name] = version
        return True

    def uninstall(self, plugin_name: str) -> bool:
        """Uninstall plugin."""
        if plugin_name in self.installed_plugins:
            del self.installed_plugins[plugin_name]
            return True
        return False

    def get_installed(self) -> Dict[str, str]:
        """Get installed plugins."""
        return self.installed_plugins.copy()


class VersionManager:
    """Manage plugin versions."""

    def __init__(self):
        self.versions: Dict[str, List[Dict]] = {}

    def save_version(self, plugin_name: str, version: str, content: Dict) -> bool:
        """Save plugin version."""
        if plugin_name not in self.versions:
            self.versions[plugin_name] = []

        self.versions[plugin_name].append({
            'version': version,
            'content': content,
            'created_at': datetime.utcnow().isoformat()
        })
        return True

    def get_version(self, plugin_name: str, version: str) -> Optional[Dict]:
        """Get specific version."""
        if plugin_name not in self.versions:
            return None

        for v in self.versions[plugin_name]:
            if v['version'] == version:
                return v
        return None

    def list_versions(self, plugin_name: str) -> List[Dict]:
        """List all versions."""
        return self.versions.get(plugin_name, [])
