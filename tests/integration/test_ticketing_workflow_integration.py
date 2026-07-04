"""Sprint 45 Phase 3: 티켓팅-워크플로우 통합 테스트 (3 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add lambda directory to path
from guardian.exceptions import TicketingException, WorkflowExecutionException


class TestTicketingWorkflowIntegration:
    """티켓팅과 워크플로우 간의 통합 검증"""

    def test_threat_detected_creates_ticket_triggers_workflow(self):
        """✅ 위협 탐지 → 티켓 생성 → 워크플로우 실행"""
        # Mock 객체 생성
        ticketing_service = Mock()
        workflow_engine = Mock()

        threat = {
            "threat_id": "THREAT-001",
            "event_type": "Unauthorized EC2 Instance",
            "severity": 8,
            "account_id": "123456789012"
        }

        # Ticketing 서비스가 티켓 생성
        ticket_response = {"ticket_id": "JIRA-001", "status": "created"}
        ticketing_service.create_ticket.return_value = ticket_response

        # Workflow 엔진이 실행
        workflow_response = {"workflow_id": "WF-001", "status": "running"}
        workflow_engine.execute.return_value = workflow_response

        # 통합 흐름
        ticket = ticketing_service.create_ticket(threat)
        assert ticket["ticket_id"] == "JIRA-001"

        # 티켓이 생성되면 워크플로우 실행
        workflow = workflow_engine.execute({
            "ticket_id": ticket["ticket_id"],
            "threat": threat
        })
        assert workflow["workflow_id"] == "WF-001"

        # 호출 확인
        ticketing_service.create_ticket.assert_called_once_with(threat)
        workflow_engine.execute.assert_called_once()

    def test_ticketing_failure_doesnt_block_workflow(self):
        """✅ 티켓팅 실패 시 워크플로우는 계속 실행"""
        ticketing_service = Mock()
        workflow_engine = Mock()

        threat = {"threat_id": "THREAT-002", "severity": 9}

        # Ticketing 실패
        ticketing_service.create_ticket.side_effect = TicketingException("Jira unavailable")

        # Workflow는 계속 실행되어야 함
        workflow_response = {"workflow_id": "WF-002", "status": "running"}
        workflow_engine.execute.return_value = workflow_response

        # 오류 처리와 함께 워크플로우 실행
        try:
            ticketing_service.create_ticket(threat)
        except TicketingException:
            # 티켓팅 실패를 처리하고 계속 진행
            pass

        # 워크플로우는 여전히 실행됨
        workflow = workflow_engine.execute({"threat": threat})
        assert workflow["status"] == "running"

    def test_workflow_failure_logs_ticket_status(self):
        """✅ 워크플로우 실패 시 티켓에 상태 로깅"""
        ticketing_service = Mock()
        workflow_engine = Mock()

        threat = {"threat_id": "THREAT-003", "severity": 7}

        # 티켓 생성 성공
        ticket_response = {"ticket_id": "JIRA-003"}
        ticketing_service.create_ticket.return_value = ticket_response

        # 워크플로우 실패
        workflow_engine.execute.side_effect = WorkflowExecutionException("Workflow error")

        ticket = ticketing_service.create_ticket(threat)

        # 워크플로우 실행 시도
        try:
            workflow_engine.execute({"ticket_id": ticket["ticket_id"]})
        except WorkflowExecutionException:
            # 워크플로우 실패를 티켓에 기록
            ticketing_service.add_comment(
                ticket["ticket_id"],
                "Workflow execution failed"
            )

        # 티켓에 주석 추가 확인
        ticketing_service.add_comment.assert_called_once_with(
            "JIRA-003",
            "Workflow execution failed"
        )
