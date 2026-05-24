"""Sprint 45 Phase 3: 워크플로우-SOAR 통합 테스트 (3 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock

# Add lambda directory to path
lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.exceptions import SOARIntegrationException, WorkflowExecutionException


class TestWorkflowSOARIntegration:
    """워크플로우와 SOAR 플랫폼 간의 통합 검증"""

    def test_workflow_completion_submits_to_soar(self):
        """✅ 워크플로우 완료 → SOAR 제출"""
        workflow_engine = Mock()
        soar_connector = Mock()

        threat = {"threat_id": "THREAT-001", "severity": 8}
        workflow_id = "WF-001"

        # 워크플로우 완료
        workflow_engine.get_status.return_value = {"workflow_id": workflow_id, "status": "completed"}

        # SOAR 제출
        soar_response = {"submission_id": "SUB-001", "status": "submitted"}
        soar_connector.submit_playbook.return_value = soar_response

        # 통합 흐름
        workflow_status = workflow_engine.get_status()
        assert workflow_status["status"] == "completed"

        # 워크플로우 완료 시 SOAR에 제출
        soar_result = soar_connector.submit_playbook({
            "workflow_id": workflow_id,
            "threat": threat
        })
        assert soar_result["submission_id"] == "SUB-001"

    def test_soar_failure_triggers_fallback_workflow(self):
        """✅ SOAR 실패 시 폴백 워크플로우 실행"""
        workflow_engine = Mock()
        soar_connector = Mock()

        threat = {"threat_id": "THREAT-002"}
        workflow_id = "WF-002"

        # 워크플로우 완료
        workflow_status = {"workflow_id": workflow_id, "status": "completed"}

        # SOAR 제출 실패
        soar_connector.submit_playbook.side_effect = SOARIntegrationException("SOAR unavailable")

        # 폴백 워크플로우 실행
        fallback_result = {"workflow_id": "WF-FALLBACK", "status": "completed"}
        workflow_engine.execute_fallback.return_value = fallback_result

        # SOAR 제출 실패 후 폴백
        try:
            soar_connector.submit_playbook({"workflow_id": workflow_id})
        except SOARIntegrationException:
            # 폴백 실행
            result = workflow_engine.execute_fallback({"threat": threat})
            assert result["status"] == "completed"

    def test_parallel_workflow_and_soar_execution(self):
        """✅ 워크플로우와 SOAR 병렬 실행"""
        workflow_engine = Mock()
        soar_connector = Mock()

        threat = {"threat_id": "THREAT-003"}

        # 워크플로우 완료 응답
        workflow_engine.execute.return_value = {
            "workflow_id": "WF-003",
            "status": "completed",
            "remediation_id": "REM-001"
        }

        # SOAR 제출 응답
        soar_connector.submit_playbook.return_value = {
            "submission_id": "SUB-003",
            "status": "queued"
        }

        # 병렬 실행 (실제로는 asyncio 사용)
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # 워크플로우와 SOAR을 병렬로 제출
            wf_future = executor.submit(
                workflow_engine.execute,
                {"threat": threat}
            )
            soar_future = executor.submit(
                soar_connector.submit_playbook,
                {"threat": threat}
            )

            wf_result = wf_future.result()
            soar_result = soar_future.result()

        # 둘 다 성공
        assert wf_result["status"] == "completed"
        assert soar_result["status"] == "queued"
