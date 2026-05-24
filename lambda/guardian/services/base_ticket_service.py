"""Abstract base class for ticketing services (Jira, ServiceNow)"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseTicketService(ABC):
    """티켓팅 서비스의 공통 인터페이스"""

    @abstractmethod
    def create_ticket(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """위협 정보로 티켓 생성"""
        pass

    @abstractmethod
    def update_ticket_status(self, ticket_id: str, status: str) -> bool:
        """티켓 상태 업데이트"""
        pass

    @abstractmethod
    def add_comment(self, ticket_id: str, comment: str) -> bool:
        """티켓에 주석 추가"""
        pass

    def convert_severity(self, severity: int) -> str:
        """AWS 심각도(1-10)를 티켓 우선순위로 변환"""
        if severity >= 9:
            return "Blocker"
        elif severity >= 7:
            return "Critical"
        elif severity >= 5:
            return "High"
        elif severity >= 3:
            return "Medium"
        else:
            return "Low"

    def format_evidence(self, evidence: Dict[str, Any]) -> str:
        """CloudTrail 증거를 포맷된 문자열로 변환"""
        if not evidence:
            return "No evidence available"

        lines = []
        lines.append("=== Threat Evidence ===")

        if "event_type" in evidence:
            lines.append(f"Event: {evidence['event_type']}")

        if "account_id" in evidence:
            lines.append(f"Account: {evidence['account_id']}")

        if "region" in evidence:
            lines.append(f"Region: {evidence['region']}")

        if "timestamp" in evidence:
            lines.append(f"Timestamp: {evidence['timestamp']}")

        if "details" in evidence:
            lines.append(f"Details: {evidence['details']}")

        return "\n".join(lines)

    def extract_priority(self, threat: Dict[str, Any]) -> int:
        """위협에서 우선순위 추출"""
        severity = threat.get("severity", 5)
        return max(1, min(10, int(severity)))

    def extract_assignee(self, threat: Dict[str, Any]) -> Optional[str]:
        """위협에서 담당자 추출"""
        return threat.get("assignee")

    def extract_description(self, threat: Dict[str, Any]) -> str:
        """위협에서 설명 생성"""
        event_type = threat.get("event_type", "Unknown")
        account_id = threat.get("account_id", "Unknown")
        return f"[{account_id}] {event_type} threat detected"
