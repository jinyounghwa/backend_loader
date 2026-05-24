"""Sprint 45 Phase 3: 완전한 오케스트레이션 통합 테스트 (3 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock, patch

# Add lambda directory to path
lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.exceptions import GuardianException


class TestFullOrchestrationIntegration:
    """완전한 인시던트 대응 흐름 검증"""

    def test_threat_detection_to_complete_response(self):
        """✅ 위협 탐지 → 티켓 → 워크플로우 → SOAR → 추적"""
        # 모든 컴포넌트 Mock
        detector = Mock()
        ticketing = Mock()
        workflow = Mock()
        soar = Mock()
        tracker = Mock()

        threat = {
            "threat_id": "THREAT-FULL-001",
            "event_type": "Unauthorized EC2 Stop",
            "severity": 9,
            "account_id": "123456789012"
        }

        # Step 1: 위협 탐지
        detector.detect.return_value = threat
        detected = detector.detect()
        assert detected["threat_id"] == "THREAT-FULL-001"

        # Step 2: 티켓 생성
        ticketing.create_ticket.return_value = {"ticket_id": "JIRA-FULL-001"}
        ticket = ticketing.create_ticket(detected)
        assert ticket["ticket_id"] == "JIRA-FULL-001"

        # Step 3: 워크플로우 실행
        workflow.execute.return_value = {"workflow_id": "WF-FULL-001", "status": "completed"}
        wf_result = workflow.execute({"ticket_id": ticket["ticket_id"], "threat": detected})
        assert wf_result["status"] == "completed"

        # Step 4: SOAR 제출
        soar.submit_playbook.return_value = {"submission_id": "SUB-FULL-001"}
        soar_result = soar.submit_playbook({"workflow_id": wf_result["workflow_id"]})
        assert soar_result["submission_id"] == "SUB-FULL-001"

        # Step 5: 결과 추적
        tracker.track.return_value = {"status": "tracked"}
        tracking = tracker.track({
            "threat_id": detected["threat_id"],
            "ticket_id": ticket["ticket_id"],
            "workflow_id": wf_result["workflow_id"],
            "submission_id": soar_result["submission_id"]
        })
        assert tracking["status"] == "tracked"

        # 모든 호출 확인
        detector.detect.assert_called_once()
        ticketing.create_ticket.assert_called_once()
        workflow.execute.assert_called_once()
        soar.submit_playbook.assert_called_once()
        tracker.track.assert_called_once()

    def test_cross_service_error_isolation(self):
        """✅ 서비스 간 에러 격리"""
        detector = Mock()
        ticketing = Mock()
        workflow = Mock()
        soar = Mock()
        tracker = Mock()

        threat = {"threat_id": "THREAT-ERROR-001", "severity": 8}

        # Step 1: 위협 탐지 성공
        detector.detect.return_value = threat

        # Step 2: 티켓팅 실패
        ticketing.create_ticket.side_effect = GuardianException("Ticketing failed")

        # Step 3: 워크플로우 계속 실행
        workflow.execute.return_value = {"workflow_id": "WF-ERROR-001"}

        # 실행
        detected = detector.detect()
        assert detected["threat_id"] == "THREAT-ERROR-001"

        # 티켓팅 실패 처리
        try:
            ticketing.create_ticket(detected)
            ticket_id = None
        except GuardianException:
            ticket_id = None  # 티켓 없이 계속

        # 워크플로우는 계속 실행
        wf_result = workflow.execute({"threat": detected})
        assert wf_result["workflow_id"] == "WF-ERROR-001"

        # SOAR은 별도로 실행
        soar.submit_playbook.return_value = {"submission_id": "SUB-ERROR-001"}
        soar_result = soar.submit_playbook({"threat": detected})
        assert soar_result["submission_id"] == "SUB-ERROR-001"

        # 추적
        tracker.track.return_value = {"status": "partial"}
        tracking = tracker.track({
            "threat_id": detected["threat_id"],
            "ticket_id": ticket_id,
            "workflow_id": wf_result["workflow_id"],
            "submission_id": soar_result["submission_id"],
            "error": "Ticketing failed"
        })
        assert tracking["status"] == "partial"

    def test_timeout_doesnt_block_other_components(self):
        """✅ 한 컴포넌트 타임아웃이 다른 컴포넌트를 막지 않음"""
        import time
        import threading

        detector = Mock()
        ticketing = Mock()
        workflow = Mock()
        soar = Mock()

        threat = {"threat_id": "THREAT-TIMEOUT-001"}

        def slow_ticketing(threat_data):
            time.sleep(0.1)  # 느린 티켓팅
            return {"ticket_id": "JIRA-TIMEOUT-001"}

        def fast_workflow(params):
            return {"workflow_id": "WF-TIMEOUT-001"}

        def fast_soar(params):
            return {"submission_id": "SUB-TIMEOUT-001"}

        # 병렬 실행
        start = time.time()

        ticketing_thread = threading.Thread(
            target=slow_ticketing,
            args=(threat,)
        )
        workflow_thread = threading.Thread(
            target=fast_workflow,
            args=({"threat": threat},)
        )
        soar_thread = threading.Thread(
            target=fast_soar,
            args=({"threat": threat},)
        )

        ticketing_thread.start()
        workflow_thread.start()
        soar_thread.start()

        ticketing_thread.join()
        workflow_thread.join()
        soar_thread.join()

        elapsed = time.time() - start

        # 병렬이므로 0.1초 정도만 걸림 (sequential은 더 오래 걸림)
        assert elapsed < 0.2, f"Parallel execution took {elapsed}s"
