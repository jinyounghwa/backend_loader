"""Pattern Recognition for identifying recurring behaviors in time-series."""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PatternRecognizer:
    """Recognizes patterns in time-series data."""

    def __init__(self):
        """Initialize pattern recognizer."""
        self.patterns = {}
        self.pattern_history = defaultdict(list)

    def identify_patterns(self, data_points: List[Tuple[float, str]], pattern_window: int = 3) -> List[Dict[str, Any]]:
        """
        Identify recurring patterns in data.

        Args:
            data_points: List of (value, timestamp) tuples
            pattern_window: Size of pattern window

        Returns:
            List of identified patterns
        """
        if len(data_points) < pattern_window * 2:
            return []

        values = [float(v) for v, _ in data_points]
        patterns = []

        # Extract pattern windows
        pattern_windows = []
        for i in range(len(values) - pattern_window + 1):
            window = tuple(values[i : i + pattern_window])
            pattern_windows.append(window)

        # Count pattern occurrences
        pattern_counter = Counter(pattern_windows)

        # Identify recurring patterns (appear at least 2 times)
        for pattern, count in pattern_counter.items():
            if count >= 2:
                occurrence_rate = count / len(pattern_windows)
                patterns.append(
                    {
                        "pattern": list(pattern),
                        "occurrences": count,
                        "occurrence_rate": round(occurrence_rate, 2),
                        "pattern_type": self._classify_pattern(pattern),
                    }
                )

        return sorted(patterns, key=lambda x: x["occurrences"], reverse=True)

    def _classify_pattern(self, pattern: Tuple[float, ...]) -> str:
        """Classify pattern type."""
        values = list(pattern)

        if len(values) < 2:
            return "SINGLE"

        # Check for constant pattern
        if len(set(values)) == 1:
            return "CONSTANT"

        # Check for increasing pattern
        if all(values[i] <= values[i + 1] for i in range(len(values) - 1)):
            return "INCREASING"

        # Check for decreasing pattern
        if all(values[i] >= values[i + 1] for i in range(len(values) - 1)):
            return "DECREASING"

        # Check for cyclic pattern
        if self._is_cyclic(values):
            return "CYCLIC"

        return "IRREGULAR"

    def _is_cyclic(self, values: List[float]) -> bool:
        """Check if pattern is cyclic (oscillating)."""
        if len(values) < 3:
            return False

        direction_changes = 0
        for i in range(len(values) - 1):
            if (values[i + 1] - values[i]) * (values[i] - (values[i - 1] if i > 0 else values[i])) < 0:
                direction_changes += 1

        return direction_changes >= len(values) // 2

    def detect_anomalous_pattern(
        self, current_pattern: List[float], normal_patterns: List[List[float]], threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Detect if current pattern is anomalous compared to normal patterns.

        Returns:
            Dict with is_anomalous, similarity_score, most_similar_pattern
        """
        if not normal_patterns:
            return {"is_anomalous": False, "similarity_score": 1.0, "most_similar_pattern": None}

        similarities = []
        for normal_pattern in normal_patterns:
            similarity = self._calculate_pattern_similarity(current_pattern, normal_pattern)
            similarities.append((similarity, normal_pattern))

        # Get best match
        best_similarity = max(similarities, key=lambda x: x[0])[0]
        most_similar = max(similarities, key=lambda x: x[0])[1]

        is_anomalous = best_similarity < (1.0 - threshold)

        return {
            "is_anomalous": is_anomalous,
            "similarity_score": round(best_similarity, 2),
            "most_similar_pattern": most_similar,
            "anomaly_severity": "HIGH" if best_similarity < 0.5 else "MEDIUM" if best_similarity < 0.7 else "LOW",
        }

    def _calculate_pattern_similarity(self, pattern1: List[float], pattern2: List[float]) -> float:
        """Calculate similarity between two patterns (0-1, where 1 is identical)."""
        if len(pattern1) != len(pattern2):
            return 0.0

        if len(pattern1) == 0:
            return 1.0

        # Normalize both patterns to 0-1 range
        min1, max1 = min(pattern1), max(pattern1)
        min2, max2 = min(pattern2), max(pattern2)

        if max1 == min1 or max2 == min2:
            return 1.0 if all(pattern1[i] == pattern2[i] for i in range(len(pattern1))) else 0.0

        norm1 = [(v - min1) / (max1 - min1) for v in pattern1]
        norm2 = [(v - min2) / (max2 - min2) for v in pattern2]

        # Calculate Euclidean distance
        distance = sum((norm1[i] - norm2[i]) ** 2 for i in range(len(norm1))) ** 0.5
        similarity = max(0.0, 1.0 - (distance / len(norm1)))

        return round(similarity, 2)

    def find_repeating_interval(self, data_points: List[Tuple[float, str]]) -> Optional[Dict[str, Any]]:
        """
        Find if there's a repeating interval in the data.

        Returns:
            Dict with interval, confidence, or None if not found
        """
        if len(data_points) < 10:
            return None

        timestamps = [ts for _, ts in data_points]
        values = [float(v) for v, _ in data_points]

        # Calculate time intervals between data points
        intervals = []
        for i in range(1, len(timestamps)):
            try:
                t1 = datetime.fromisoformat(timestamps[i - 1].replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(timestamps[i].replace("Z", "+00:00"))
                interval = (t2 - t1).total_seconds()
                intervals.append(interval)
            except Exception as e:
                logger.warning(f"Error parsing timestamp: {e}")
                continue

        if not intervals:
            return None

        # Find most common interval
        interval_counter = Counter(intervals)
        most_common_interval = interval_counter.most_common(1)[0]

        interval_seconds = most_common_interval[0]
        occurrence_count = most_common_interval[1]
        occurrence_rate = occurrence_count / len(intervals)

        # Convert to human-readable format
        if interval_seconds < 60:
            interval_str = f"{int(interval_seconds)}s"
        elif interval_seconds < 3600:
            interval_str = f"{int(interval_seconds / 60)}m"
        else:
            interval_str = f"{int(interval_seconds / 3600)}h"

        return {
            "interval_seconds": int(interval_seconds),
            "interval_human": interval_str,
            "occurrence_rate": round(occurrence_rate, 2),
            "occurrences": occurrence_count,
            "total_intervals": len(intervals),
            "confidence": round(occurrence_rate, 2),
        }

    def get_pattern_statistics(self, data_points: List[Tuple[float, str]]) -> Dict[str, Any]:
        """Get comprehensive pattern statistics."""
        values = [float(v) for v, _ in data_points]

        patterns = self.identify_patterns(data_points)
        repeating_interval = self.find_repeating_interval(data_points)

        return {
            "total_data_points": len(data_points),
            "unique_patterns": len(patterns),
            "most_common_pattern": patterns[0] if patterns else None,
            "repeating_interval": repeating_interval,
            "patterns": patterns,
        }
