"""Dependency resolution for plugins using topological sort"""

from typing import Dict, List, Set


class DependencyGraph:
    """Graph representation of plugin dependencies."""

    def __init__(self):
        self.graph: Dict[str, List[str]] = {}

    def add_edge(self, from_plugin: str, to_plugin: str) -> None:
        """Add dependency edge."""
        if from_plugin not in self.graph:
            self.graph[from_plugin] = []
        self.graph[from_plugin].append(to_plugin)

    def add_node(self, plugin: str) -> None:
        """Add plugin node."""
        if plugin not in self.graph:
            self.graph[plugin] = []


class DependencyResolver:
    """Resolve plugin dependencies using topological sort."""

    def resolve(self, plugins: Dict[str, Dict]) -> List[str]:
        """Resolve dependencies and return install order."""
        # Build dependency graph
        graph = DependencyGraph()
        for plugin_name in plugins:
            graph.add_node(plugin_name)

        for plugin_name, plugin_info in plugins.items():
            deps = plugin_info.get('dependencies', [])
            for dep in deps:
                # Extract plugin name from dependency string (e.g., "plugin-c>=1.0")
                dep_name = dep.split('>=')[0].split('==')[0]
                if dep_name in plugins:
                    graph.add_edge(plugin_name, dep_name)

        # Topological sort
        visited: Set[str] = set()
        order: List[str] = []

        def visit(node: str) -> bool:
            if node in visited:
                return True

            visited.add(node)

            for dep in graph.graph.get(node, []):
                if not visit(dep):
                    return False

            order.append(node)
            return True

        for plugin in plugins:
            if not visit(plugin):
                return []

        return order

    def detect_cycles(self, plugins: Dict[str, Dict]) -> List[List[str]]:
        """Detect circular dependencies."""
        cycles = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            deps = plugins.get(node, {}).get('dependencies', [])
            for dep in deps:
                dep_name = dep.split('>=')[0]
                if dep_name not in visited:
                    if dfs(dep_name, path):
                        return True
                elif dep_name in rec_stack:
                    cycles.append(path[path.index(dep_name):] + [dep_name])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for plugin in plugins:
            if plugin not in visited:
                dfs(plugin, [])

        return cycles
