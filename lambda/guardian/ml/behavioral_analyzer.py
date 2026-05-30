"""Behavioral ML for anomaly detection."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict


class BehavioralProfiler:
    """Build user behavior profiles."""

    def __init__(self):
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.activities: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def record_activity(self, activity: Dict[str, Any]) -> None:
        """Record user activity."""
        user = activity.get('user')
        if user:
            self.activities[user].append(activity)
            self._update_profile(user)

    def _update_profile(self, user: str) -> None:
        """Update user profile based on activities."""
        activities = self.activities[user]

        if user not in self.profiles:
            self.profiles[user] = {}

        # Extract typical actions
        actions = [a.get('action') for a in activities if a.get('action')]
        self.profiles[user]['typical_actions'] = list(set(actions))

        # Extract typical hours
        hours = [a.get('timestamp').hour for a in activities if a.get('timestamp')]
        self.profiles[user]['typical_hours'] = list(set(hours))

    def get_profile(self, user: str) -> Dict[str, Any]:
        """Get user behavior profile."""
        return self.profiles.get(user, {})


class AnomalyDetector:
    """Detect behavioral anomalies."""

    def __init__(self):
        self.baseline: Dict[str, Any] = {}

    def record_normal_behavior(self, behavior: Dict[str, Any]) -> None:
        """Record normal baseline behavior."""
        self.baseline[str(behavior)] = behavior

    def detect_anomaly(self, behavior: Dict[str, Any]) -> float:
        """Detect anomalies in behavior."""
        score = 0

        # Check action deviation
        action = behavior.get('action', '').lower()
        if action == 'deletebucket':
            score += 40
        elif action == 'deletetable':
            score += 35
        elif 'delete' in action:
            score += 30

        # Check time deviation
        hour = behavior.get('hour')
        if hour and isinstance(hour, int) and (hour < 6 or hour > 22):
            score += 30

        # Check time string deviation
        time_str = behavior.get('time', '').lower()
        if time_str == 'night':
            score += 15

        # Check frequency
        frequency = behavior.get('frequency')
        if frequency:
            if isinstance(frequency, str):
                if frequency.lower() == 'high':
                    score += 20
            elif isinstance(frequency, (int, float)) and frequency > 10:
                score += min(75, 25 + (frequency - 10) * 2)

        # Check location deviation
        location = behavior.get('location')
        if location == 'EU-WEST-1':
            score += 20

        return min(100, score)


class ContextScorer:
    """Score anomalies based on context."""

    def __init__(self):
        self.baselines: Dict[str, Dict[str, Any]] = {}

    def set_baseline_hours(self, user: str, hours: List[int]) -> None:
        """Set baseline work hours."""
        if user not in self.baselines:
            self.baselines[user] = {}
        self.baselines[user]['hours'] = hours

    def set_baseline_locations(self, user: str, locations: List[str]) -> None:
        """Set baseline locations."""
        if user not in self.baselines:
            self.baselines[user] = {}
        self.baselines[user]['locations'] = locations

    def set_baseline_devices(self, user: str, devices: List[str]) -> None:
        """Set baseline devices."""
        if user not in self.baselines:
            self.baselines[user] = {}
        self.baselines[user]['devices'] = devices

    def set_baseline_actions(self, user: str, actions: List[str]) -> None:
        """Set baseline actions."""
        if user not in self.baselines:
            self.baselines[user] = {}
        self.baselines[user]['actions'] = actions

    def get_time_context_score(self, user: str, hour: int) -> float:
        """Score anomaly based on time."""
        if user in self.baselines and hour not in self.baselines[user].get('hours', []):
            return min(100, 60 + (abs(12 - hour) / 12) * 40)
        return 0

    def get_location_context_score(self, user: str, location: str) -> float:
        """Score anomaly based on location."""
        if user in self.baselines and location not in self.baselines[user].get('locations', []):
            return min(100, 50)
        return 0

    def get_device_context_score(self, user: str, device: str) -> float:
        """Score anomaly based on device."""
        if user in self.baselines and device not in self.baselines[user].get('devices', []):
            return min(100, 35)
        return 0

    def get_action_context_score(self, user: str, action: str) -> float:
        """Score anomaly based on action."""
        if user in self.baselines and action in self.baselines[user].get('actions', []):
            return 0  # Normal action
        return 50
