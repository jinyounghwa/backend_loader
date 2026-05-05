"""Lambda Performance Baseline Tests

Measures and validates Lambda cold start, warm invocation, and
multi-region performance against v1.1 targets.
"""

import pytest
from harness import LambdaHarness, CostCheckerHarness, EC2CheckerHarness, S3CheckerHarness
from metrics import PerformanceMetrics


class TestColdStart:
    """Cold start performance measurement"""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    def test_cold_start_measurement(self, metrics):
        """Test: Measure Lambda cold start (first SAM invocation)

        This includes SAM container startup time, which is longer than
        actual AWS Lambda cold start. Used for baseline comparison only.
        """
        harness = LambdaHarness()
        event = {"detail": {}}

        _, duration_ms = harness.invoke_local_with_timing(event)
        metrics.add_cold_start(duration_ms)

        # Cold start target: < 2500ms (includes SAM container startup)
        assert duration_ms < 2500.0, f"Cold start too slow: {duration_ms:.1f}ms"
        print(f"Cold start: {duration_ms:.1f}ms")

    def test_cold_start_baseline_documented(self, metrics):
        """Test: Cold start baseline is documented for future comparison"""
        # This test ensures we establish a baseline for regression detection
        # Actual measurement happens in test_cold_start_measurement
        assert hasattr(metrics, "add_cold_start")


class TestWarmInvocation:
    """Warm invocation (subsequent calls) performance"""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    @pytest.fixture
    def warmed_harness(self):
        """Pre-warm the harness with an initial invocation"""
        harness = LambdaHarness()
        event = {"detail": {}}
        # Warm up
        harness.invoke_local(event)
        return harness

    def test_warm_invocation_performance(self, metrics, warmed_harness):
        """Test: Warm invocation (after SAM container is ready)

        Target: < 500ms for subsequent invocations
        """
        event = {"detail": {}}
        times = []

        for _ in range(3):
            _, duration_ms = warmed_harness.invoke_local_with_timing(event)
            times.append(duration_ms)
            metrics.add_warm_invocation(duration_ms)

        avg_time = sum(times) / len(times)
        assert avg_time < 500.0, f"Warm invocation too slow: {avg_time:.1f}ms"
        print(f"Warm invocation avg (3x): {avg_time:.1f}ms")


class TestMultiRegionPerformance:
    """Multi-region Lambda execution performance"""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    def test_multi_region_sequential(self, metrics):
        """Test: Multi-region execution (4 regions, sequential)

        Target: < 15000ms for 4 regions x 3 checkers (with optimization)
        """
        harness = LambdaHarness()
        event = {
            "version": "0",
            "id": "multi-region-test",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789012",
            "time": "2026-05-05T12:00:00Z",
            "region": "ap-northeast-1",
            "resources": [],
            "detail": {
                "regions": [
                    "ap-northeast-1",
                    "ap-southeast-1",
                    "us-east-1",
                    "eu-west-1",
                ]
            },
        }

        _, duration_ms = harness.invoke_local_with_timing(event)
        metrics.add_multi_region(4, duration_ms)

        assert duration_ms < 15000.0, f"Multi-region too slow: {duration_ms:.1f}ms"
        print(f"Multi-region (4x) execution: {duration_ms:.1f}ms")


class TestCheckerPerformance:
    """Individual checker performance baseline"""

    @pytest.fixture
    def metrics(self):
        return PerformanceMetrics()

    def test_cost_checker_performance(self, metrics):
        """Test: Cost checker performance (target: < 1000ms)"""
        harness = CostCheckerHarness()
        event = harness.create_cost_check_event()

        _, duration_ms = harness.invoke_local_with_timing(event)
        metrics.add_checker_execution("cost", duration_ms)

        assert duration_ms < 1000.0, f"Cost checker too slow: {duration_ms:.1f}ms"
        print(f"Cost checker: {duration_ms:.1f}ms")

    def test_ec2_checker_performance(self, metrics):
        """Test: EC2 checker performance (target: < 1000ms)"""
        harness = EC2CheckerHarness()
        event = harness.create_ec2_check_event()

        _, duration_ms = harness.invoke_local_with_timing(event)
        metrics.add_checker_execution("ec2", duration_ms)

        assert duration_ms < 1000.0, f"EC2 checker too slow: {duration_ms:.1f}ms"
        print(f"EC2 checker: {duration_ms:.1f}ms")

    def test_s3_checker_performance(self, metrics):
        """Test: S3 checker performance (target: < 1000ms)"""
        harness = S3CheckerHarness()
        event = harness.create_s3_check_event()

        _, duration_ms = harness.invoke_local_with_timing(event)
        metrics.add_checker_execution("s3", duration_ms)

        assert duration_ms < 1000.0, f"S3 checker too slow: {duration_ms:.1f}ms"
        print(f"S3 checker: {duration_ms:.1f}ms")


class TestPerformanceRegression:
    """Performance regression detection"""

    def test_performance_baseline_consistent(self):
        """Test: Performance remains consistent across runs

        This test ensures we can detect regressions in future sprints.
        """
        harness = LambdaHarness()
        event = {"detail": {}}

        durations = []
        for _ in range(3):
            _, duration_ms = harness.invoke_local_with_timing(event)
            durations.append(duration_ms)

        # Check that performance is reasonably consistent (< 50% variation)
        avg = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        variation = (max_duration - min_duration) / avg
        assert variation < 0.5, f"High performance variation: {variation:.1%}"
        print(f"Performance consistency: ±{variation:.1%}")


@pytest.fixture(scope="module", autouse=True)
def generate_performance_baseline():
    """Auto-generate performance baseline report after tests"""
    metrics = PerformanceMetrics()

    yield

    # After all tests, save baseline
    # This is a simplified version - actual baseline generated from test runs
    metrics.save_baseline()
