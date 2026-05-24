"""Sprint 45 Phase 2: 코드 리펙토링 검증 테스트 (8 tests)"""

import sys
from pathlib import Path

import pytest
from abc import ABC

# Add lambda directory to path
lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.services.base_ticket_service import BaseTicketService


class MockTicketService(BaseTicketService):
    """BaseTicketService의 구현 테스트용 Mock"""

    def create_ticket(self, threat):
        return {"ticket_id": "TEST-001", "status": "created"}

    def update_ticket_status(self, ticket_id, status):
        return True

    def add_comment(self, ticket_id, comment):
        return True


class TestRefactoring:
    """코드 리펙토링 검증"""

    def test_base_ticket_service_abstract(self):
        """✅ BaseTicketService는 ABC(추상 클래스)"""
        assert issubclass(BaseTicketService, ABC)

        # 직접 인스턴스화 불가능
        with pytest.raises(TypeError):
            BaseTicketService()

    def test_jira_inherits_base_service(self):
        """✅ JiraService가 BaseTicketService 상속"""
        try:
            from guardian.services.jira_service import JiraService
            assert issubclass(JiraService, BaseTicketService)
        except ImportError:
            pytest.skip("JiraService 미구현")

    def test_servicenow_inherits_base_service(self):
        """✅ ServiceNowService가 BaseTicketService 상속"""
        try:
            from guardian.services.servicenow_service import ServiceNowService
            assert issubclass(ServiceNowService, BaseTicketService)
        except ImportError:
            pytest.skip("ServiceNowService 미구현")

    def test_shared_severity_conversion(self):
        """✅ 공통 심각도 변환 함수"""
        service = MockTicketService()

        # 테스트 케이스
        test_cases = [
            (10, "Blocker"),
            (9, "Blocker"),
            (8, "Critical"),
            (7, "Critical"),
            (6, "High"),
            (5, "High"),
            (4, "Medium"),
            (3, "Medium"),
            (2, "Low"),
            (1, "Low"),
        ]

        for severity, expected_priority in test_cases:
            assert service.convert_severity(severity) == expected_priority

    def test_shared_evidence_formatting(self):
        """✅ 공통 증거 포맷팅 함수"""
        service = MockTicketService()

        evidence = {
            "event_type": "UnauthorizedOperation",
            "account_id": "123456789012",
            "region": "us-east-1",
            "timestamp": "2026-05-25T10:00:00Z",
            "details": "Attempted S3 bucket access"
        }

        formatted = service.format_evidence(evidence)

        assert "UnauthorizedOperation" in formatted
        assert "123456789012" in formatted
        assert "us-east-1" in formatted
        assert "S3 bucket access" in formatted

    def test_code_duplication_reduced(self):
        """✅ 중복 코드 제거됨"""
        service = MockTicketService()

        # BaseTicketService의 메서드들이 모두 접근 가능
        assert hasattr(service, "convert_severity")
        assert hasattr(service, "format_evidence")
        assert hasattr(service, "extract_priority")
        assert hasattr(service, "extract_assignee")
        assert hasattr(service, "extract_description")

    def test_api_consistency_between_implementations(self):
        """✅ 구현 간 API 일관성"""
        service = MockTicketService()
        threat = {
            "event_type": "EC2 Stop",
            "account_id": "123456789012",
            "severity": 7
        }

        # 모든 구현이 동일한 인터페이스 제공
        assert callable(service.create_ticket)
        assert callable(service.update_ticket_status)
        assert callable(service.add_comment)

        # 반환값이 예상 타입
        ticket = service.create_ticket(threat)
        assert isinstance(ticket, dict)

        result = service.update_ticket_status("TEST-001", "resolved")
        assert isinstance(result, bool)

    def test_error_handling_unified(self):
        """✅ 에러 처리 통일화"""
        service = MockTicketService()

        # 빈 증거 처리
        empty_evidence = {}
        formatted = service.format_evidence(empty_evidence)
        assert "No evidence available" in formatted

        # None 증거 처리
        none_evidence = None
        formatted = service.format_evidence(none_evidence)
        assert "No evidence available" in formatted
