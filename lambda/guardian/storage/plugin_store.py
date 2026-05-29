"""Plugin storage: DynamoDB persistence for marketplace"""

from typing import Dict, List, Optional
from datetime import datetime


class PluginRepository:
    """Store plugins in DynamoDB."""

    def __init__(self):
        self.plugins: Dict[str, Dict] = {}

    def save_plugin(self, plugin_id: str, plugin_data: Dict) -> bool:
        """Save plugin to storage."""
        self.plugins[plugin_id] = {
            'id': plugin_id,
            'data': plugin_data,
            'saved_at': datetime.utcnow().isoformat()
        }
        return True

    def get_plugin(self, plugin_id: str) -> Optional[Dict]:
        """Get plugin from storage."""
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> List[Dict]:
        """List all plugins."""
        return list(self.plugins.values())

    def delete_plugin(self, plugin_id: str) -> bool:
        """Delete plugin from storage."""
        if plugin_id in self.plugins:
            del self.plugins[plugin_id]
            return True
        return False


class RatingStore:
    """Store plugin ratings."""

    def __init__(self):
        self.ratings: Dict[str, List[Dict]] = {}

    def add_rating(self, plugin_id: str, rating: int, user: str) -> bool:
        """Add rating for plugin."""
        if plugin_id not in self.ratings:
            self.ratings[plugin_id] = []

        self.ratings[plugin_id].append({
            'rating': rating,
            'user': user,
            'timestamp': datetime.utcnow().isoformat()
        })
        return True

    def get_average_rating(self, plugin_id: str) -> float:
        """Get average rating."""
        if plugin_id not in self.ratings or not self.ratings[plugin_id]:
            return 0.0

        ratings = [r['rating'] for r in self.ratings[plugin_id]]
        return sum(ratings) / len(ratings)

    def get_rating_count(self, plugin_id: str) -> int:
        """Get number of ratings."""
        return len(self.ratings.get(plugin_id, []))
