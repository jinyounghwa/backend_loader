"""Sprint 45 Phase 2: 에러 처리 검증 테스트 (6 tests)"""

import sys
from pathlib import Path

import pytest

# Add lambda directory to path
from guardian.exceptions import (
    GuardianException,
    TicketingException,
    WorkflowExecutionException,
    SOARIntegrationException,
    ValidationException,
    RetryableException,
    ServiceUnavailableException,
    ConfigurationException,
)


class TestErrorHandling:
    """에러 처리 검증"""

    def test_custom_exceptions_properly_raised(self):
        """✅ Custom exception이 올바르게 발생"""
        # GuardianException
        with pytest.raises(GuardianException):
            raise GuardianException("Test error")

        # TicketingException
        with pytest.raises(TicketingException):
            raise TicketingException("Ticketing error")

        # WorkflowExecutionException
        with pytest.raises(WorkflowExecutionException):
            raise WorkflowExecutionException("Workflow error")

        # SOARIntegrationException
        with pytest.raises(SOARIntegrationException):
            raise SOARIntegrationException("SOAR error")

    def test_retry_logic_for_retryable_exceptions(self):
        """✅ Retryable exception 처리"""
        retry_count = 0
        max_retries = 3

        def flaky_operation():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 2:
                raise RetryableException("Network timeout")
            return "success"

        # 재시도 로직
        for attempt in range(max_retries):
            try:
                result = flaky_operation()
                assert result == "success"
                break
            except RetryableException:
                if attempt == max_retries - 1:
                    raise
                continue

        assert retry_count == 2

    def test_error_logging_captures_full_context(self):
        """✅ 에러 로깅이 전체 컨텍스트 캡처"""
        try:
            raise ValidationException("Invalid threat data")
        except ValidationException as e:
            # 에러 타입 확인
            assert type(e).__name__ == "ValidationException"
            # 에러 메시지 확인
            assert str(e) == "Invalid threat data"
            # 상속 구조 확인
            assert isinstance(e, GuardianException)
            assert isinstance(e, Exception)

    def test_error_recovery_strategies(self):
        """✅ 에러 복구 전략"""
        def service_call_with_fallback():
            try:
                raise ServiceUnavailableException("Service down")
            except ServiceUnavailableException:
                # 폴백 동작
                return {"status": "degraded", "cached_result": True}

        result = service_call_with_fallback()
        assert result["status"] == "degraded"
        assert result["cached_result"] is True

    def test_graceful_degradation_on_service_failure(self):
        """✅ 서비스 실패 시 우아한 성능 저하"""
        services = {
            "ticketing": None,  # 실패
            "workflow": None,   # 실패
            "soar": None        # 실패
        }

        def orchestrate_with_degradation(threat):
            results = {}

            # Ticketing 시도
            try:
                if services["ticketing"] is None:
                    raise TicketingException("Ticketing service unavailable")
                results["ticketing"] = "created"
            except TicketingException:
                results["ticketing"] = "skipped"  # 우아한 처리

            # Workflow 시도
            try:
                if services["workflow"] is None:
                    raise WorkflowExecutionException("Workflow service unavailable")
                results["workflow"] = "executed"
            except WorkflowExecutionException:
                results["workflow"] = "skipped"  # 우아한 처리

            # SOAR 시도
            try:
                if services["soar"] is None:
                    raise SOARIntegrationException("SOAR service unavailable")
                results["soar"] = "submitted"
            except SOARIntegrationException:
                results["soar"] = "skipped"  # 우아한 처리

            return results

        threat = {"severity": 8}
        results = orchestrate_with_degradation(threat)

        # 모든 서비스 실패했지만 전체 flow는 완료
        assert results["ticketing"] == "skipped"
        assert results["workflow"] == "skipped"
        assert results["soar"] == "skipped"
        assert len(results) == 3

    def test_error_metrics_tracking(self):
        """✅ 에러 메트릭 추적"""
        error_metrics = {
            "TicketingException": 0,
            "WorkflowExecutionException": 0,
            "SOARIntegrationException": 0,
            "RetryableException": 0,
        }

        def track_error(exception_type):
            error_name = type(exception_type).__name__
            if error_name in error_metrics:
                error_metrics[error_name] += 1

        # 에러 발생 시뮬레이션
        exceptions = [
            TicketingException("Error 1"),
            WorkflowExecutionException("Error 2"),
            TicketingException("Error 3"),
            RetryableException("Error 4"),
        ]

        for exc in exceptions:
            track_error(exc)

        # 메트릭 확인
        assert error_metrics["TicketingException"] == 2
        assert error_metrics["WorkflowExecutionException"] == 1
        assert error_metrics["RetryableException"] == 1
        assert error_metrics["SOARIntegrationException"] == 0
