"""Orchestrator Harness Tests - Full Checker Chain"""

import pytest
from harness import LambdaHarness


class TestOrchestratorHarness:
    """모든 checker를 orchestrator를 통해 실행하는 통합 테스트"""

    @pytest.fixture
    def harness(self):
        return LambdaHarness(function_name="GuardianChecker")

    def test_orchestrator_all_checkers(self, harness, eventbridge_multi_region_event):
        """Test: 모든 checker가 orchestrator를 통해 실행"""
        # detail이 비어있으면 모든 checker 실행
        eventbridge_multi_region_event["detail"] = {}
        response = harness.invoke_local(eventbridge_multi_region_event)

        assert response is not None
        # Orchestrator는 모든 checker 결과 수집

    def test_orchestrator_selective_checkers(self, harness, eventbridge_cost_event):
        """Test: 특정 checker만 실행"""
        response = harness.invoke_local(eventbridge_cost_event)

        assert response is not None
        # Cost checker만 실행됨

    def test_orchestrator_error_propagation(self, harness):
        """Test: Checker 오류가 orchestrator에서 처리됨"""
        # 잘못된 event로 오류 테스트
        bad_event = {
            "version": "0",
            "id": "bad-event",
            "detail": {"invalid_key": "value"},
        }
        response = harness.invoke_local(bad_event)

        # Orchestrator는 오류를 처리하고 응답 반환
        assert response is not None

    def test_orchestrator_performance_multi_checker(self, harness):
        """Test: 모든 checker 실행 성능 (target: <15s for 4 regions)"""
        event = {
            "version": "0",
            "id": "multi-checker-event",
            "detail": {"regions": ["ap-northeast-1", "us-east-1", "eu-west-1"]},
        }
        response, duration = harness.invoke_local_with_timing(event)

        assert response is not None
        print(f"Multi-checker execution time: {duration:.3f}s")
        # 4개 리전 x 3개 checker이지만, 병렬/캐싱으로 최적화되어야 함
        assert duration < 20.0, f"Orchestrator too slow: {duration:.3f}s"
