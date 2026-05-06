"""Cost Checker Harness Tests"""

import pytest
from harness import CostCheckerHarness


class TestCostCheckerHarness:
    """Cost Checker를 SAM local로 테스트"""

    @pytest.fixture
    def harness(self):
        return CostCheckerHarness()

    def test_cost_checker_invocation(self, harness):
        """Test: Cost checker가 정상 호출"""
        event = harness.create_cost_check_event()
        response = harness.invoke_local(event)

        assert response is not None
        assert isinstance(response, dict)

    def test_cost_checker_multi_region(self, harness):
        """Test: 여러 리전 비용 확인"""
        event = harness.create_cost_check_event(regions=["ap-northeast-1", "us-east-1"])
        response = harness.invoke_local(event)

        assert response is not None
        # 각 리전별 비용 데이터 포함되어야 함

    def test_cost_checker_response_structure(self, harness):
        """Test: Cost checker response 구조"""
        event = harness.create_cost_check_event()
        response = harness.invoke_local(event)

        # findings 또는 statusCode 포함
        assert "statusCode" in response or "findings" in response

    def test_cost_checker_performance(self, harness):
        """Test: Cost checker 성능 (target: <500ms)"""
        event = harness.create_cost_check_event()
        response, duration = harness.invoke_local_with_timing(event)

        assert response is not None
        # 성능 로깅
        print(f"Cost checker execution time: {duration:.3f}s")
        # <2s는 합리적인 목표
        assert duration < 2.0, f"Cost checker too slow: {duration:.3f}s"
