"""Performance metrics collection and reporting

Utilities for collecting, analyzing, and reporting Lambda performance metrics.
"""

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List


class PerformanceMetrics:
    """Collect and analyze Lambda performance metrics"""

    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []
        self.start_time: float = 0
        self.end_time: float = 0

    def start_timing(self):
        """Start timing measurement"""
        self.start_time = time.time()

    def end_timing(self) -> float:
        """End timing measurement and return duration"""
        self.end_time = time.time()
        return self.end_time - self.start_time

    def record(
        self,
        name: str,
        duration_ms: float,
        checker: str = "unknown",
        region: str = "ap-northeast-1",
        status: str = "success",
        details: Dict[str, Any] = None,
    ):
        """Record a single metric"""
        metric = {
            "name": name,
            "duration_ms": duration_ms,
            "checker": checker,
            "region": region,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }
        self.metrics.append(metric)

    def add_cold_start(self, duration_ms: float):
        """Record cold start measurement"""
        self.record("cold_start", duration_ms, status="baseline")

    def add_warm_invocation(self, duration_ms: float):
        """Record warm invocation measurement"""
        self.record("warm_invocation", duration_ms)

    def add_multi_region(self, regions: int, duration_ms: float):
        """Record multi-region invocation measurement"""
        self.record(
            "multi_region",
            duration_ms,
            details={"region_count": regions},
        )

    def add_checker_execution(
        self, checker: str, duration_ms: float, region: str = "ap-northeast-1"
    ):
        """Record individual checker execution time"""
        self.record(
            f"checker_{checker}",
            duration_ms,
            checker=checker,
            region=region,
        )

    def get_statistics(self, metric_name: str = None) -> Dict[str, float]:
        """Get statistics for a metric"""
        if metric_name:
            values = [
                m["duration_ms"]
                for m in self.metrics
                if m["name"] == metric_name or m["name"].endswith(f"_{metric_name}")
            ]
        else:
            values = [m["duration_ms"] for m in self.metrics]

        if not values:
            return {}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
        }

    def print_summary(self):
        """Print performance summary"""
        print("\n=== Lambda Performance Baseline ===\n")

        # Cold start
        cold_starts = [m["duration_ms"] for m in self.metrics if m["name"] == "cold_start"]
        if cold_starts:
            print(f"Cold Start: {cold_starts[0]:.1f}ms")

        # Warm invocation
        warm_stats = self.get_statistics("warm_invocation")
        if warm_stats:
            print(
                f"Warm Invocation: {warm_stats['mean']:.1f}ms (avg) "
                f"[min: {warm_stats['min']:.1f}ms, max: {warm_stats['max']:.1f}ms]"
            )

        # Multi-region
        multi_stats = self.get_statistics("multi_region")
        if multi_stats:
            print(f"Multi-Region (4x): {multi_stats['mean']:.1f}ms (avg)")

        # Per-checker
        checkers = set()
        for m in self.metrics:
            if m["name"].startswith("checker_"):
                checker = m["name"].replace("checker_", "")
                checkers.add(checker)

        if checkers:
            print("\nPer-Checker Baseline:")
            for checker in sorted(checkers):
                stats = self.get_statistics(checker)
                if stats:
                    print(f"  {checker}: {stats['mean']:.1f}ms " f"(n={int(stats['count'])})")

        print()

    def to_json(self) -> str:
        """Export metrics to JSON"""
        return json.dumps(self.metrics, indent=2, default=str)

    def save_baseline(self, filepath: str = "docs/PERFORMANCE_BASELINE_v1.1.md"):
        """Save baseline report to markdown file"""
        report = self._generate_baseline_report()
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(report)

    def _generate_baseline_report(self) -> str:
        """Generate baseline report markdown"""
        cold_starts = [m["duration_ms"] for m in self.metrics if m["name"] == "cold_start"]
        warm_stats = self.get_statistics("warm_invocation")
        multi_stats = self.get_statistics("multi_region")

        cold_start_val = f"{cold_starts[0]:.1f}ms (first invocation with SAM container startup)" if cold_starts else "Not measured"
        cold_start_target = "N/A"
        cold_start_status = "N/A"
        if cold_starts:
            cold_start_target = f"{cold_starts[0]:.0f}ms"
            cold_start_status = "✅ PASS" if cold_starts[0] < 2500 else "❌ FAIL"

        lines = [
            "# Lambda Performance Baseline (v1.1)\n",
            "**Generated**: " + datetime.now(timezone.utc).isoformat() + "\n",
            "**Total Measurements**: " + str(len(self.metrics)) + "\n",
            "\n## Cold Start\n",
            f"- **Time**: {cold_start_val}",
            "\n- **Target (v1.1)**: < 2500ms (includes SAM startup)",
            f"\n- **Status**: {cold_start_status}\n",
            "\n## Warm Invocation (Subsequent Calls)\n",
            (
                f"- **Average**: {warm_stats['mean']:.1f}ms"
                if warm_stats
                else "- **Average**: Not measured"
            ),
            (
                f"\n- **Range**: {warm_stats['min']:.1f}ms - {warm_stats['max']:.1f}ms"
                if warm_stats
                else ""
            ),
            "\n- **Target (v1.1)**: < 500ms",
            f"\n- **Status**: {'✅ PASS' if warm_stats and warm_stats['mean'] < 500 else 'N/A'}\n",
            "\n## Multi-Region (4 Regions Sequential)\n",
            (
                f"- **Average**: {multi_stats['mean']:.1f}ms"
                if multi_stats
                else "- **Average**: Not measured"
            ),
            "\n- **Target (v1.1)**: < 15000ms",
            f"\n- **Status**: {'✅ PASS' if multi_stats and multi_stats['mean'] < 15000 else 'N/A'}\n",
            "\n## Per-Checker Performance\n",
            "| Checker | Avg (ms) | Min (ms) | Max (ms) | Count |\n",
            "|---------|----------|----------|----------|-------|\n",
        ]

        checkers = set()
        for m in self.metrics:
            if m["name"].startswith("checker_"):
                checker = m["name"].replace("checker_", "")
                checkers.add(checker)

        for checker in sorted(checkers):
            stats = self.get_statistics(checker)
            if stats:
                lines.append(
                    f"| {checker} | {stats['mean']:.1f} | {stats['min']:.1f} | "
                    f"{stats['max']:.1f} | {int(stats['count'])} |\n"
                )

        lines.extend(
            [
                "\n## Performance Targets (v1.1)\n",
                "| Metric | Target | Current | Status |\n",
                "|--------|--------|---------|--------|\n",
                f"| Cold Start | < 2500ms | {cold_start_target} | "
                f"{'✅' if cold_starts and cold_starts[0] < 2500 else 'N/A'} |\n",
                (
                    f"| Warm Invocation | < 500ms | {warm_stats['mean']:.0f}ms | "
                    f"{'✅' if warm_stats['mean'] < 500 else '❌'} |\n"
                    if warm_stats
                    else ""
                ),
                (
                    f"| Multi-Region | < 15000ms | {multi_stats['mean']:.0f}ms | "
                    f"{'✅' if multi_stats['mean'] < 15000 else '❌'} |\n"
                    if multi_stats
                    else ""
                ),
                "\n## Raw Metrics\n",
                "```json\n",
                self.to_json(),
                "\n```\n",
            ]
        )

        return "".join(lines)


def measure_performance(func: Callable) -> Callable:
    """Decorator to measure function performance"""

    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000  # Convert to ms
        return result, duration

    return wrapper
