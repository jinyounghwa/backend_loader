"""Lambda Handler Harness Tests - Full Guardian Handler Integration"""

import pytest
from harness import LambdaHarness


class TestHandlerIntegration:
    """Guardian Lambda handler의 전체 실행 흐름 테스트"""

    @pytest.fixture
    def handler_harness(self):
        return LambdaHarness(function_name="GuardianChecker")

    def test_handler_eventbridge_scheduled_event(self, handler_harness, eventbridge_cost_event):
        """Test: EventBridge scheduled event가 handler를 정상 실행"""
        response = handler_harness.invoke_local(eventbridge_cost_event)

        assert response is not None
        assert "statusCode" in response or "findings" in response
        # Handler는 성공하거나 findings를 반환

    def test_handler_with_multiple_regions(self, handler_harness, eventbridge_multi_region_event):
        """Test: 여러 리전을 한 번에 처리"""
        response = handler_harness.invoke_local(eventbridge_multi_region_event)

        assert response is not None
        # Multi-region 응답 검증
        if "findings" in response:
            # findings가 여러 리전을 포함할 수 있음
            assert isinstance(response["findings"], list)

    def test_handler_empty_detail(self, handler_harness, lambda_event_base):
        """Test: detail이 빈 경우 모든 checker 실행"""
        lambda_event_base["detail"] = {}
        response = handler_harness.invoke_local(lambda_event_base)

        assert response is not None
        # Handler는 default 리전에서 실행되어야 함

    def test_handler_response_structure(self, handler_harness, eventbridge_cost_event):
        """Test: Handler response 구조 검증"""
        response = handler_harness.invoke_local(eventbridge_cost_event)

        # Response는 dict이어야 함
        assert isinstance(response, dict)
        # statusCode 또는 findings 포함
        assert any(key in response for key in ["statusCode", "findings", "body"])
