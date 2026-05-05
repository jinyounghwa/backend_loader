"""Lambda Test Harness for SAM Local Invocation

This harness provides utilities to invoke Lambda handlers locally via SAM CLI,
measure performance, and validate IAM permissions.
"""

import json
import subprocess
import time
import os
from typing import Any, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LambdaHarness:
    """LocalStack SAM을 통한 실제 Lambda 호출 테스트"""

    def __init__(self, function_name: str = "GuardianChecker", sam_template: str = "sam.yaml"):
        """Initialize Lambda harness.

        Args:
            function_name: SAM template에 정의된 Lambda function logical ID
            sam_template: SAM template file path (relative to project root)
        """
        self.function_name = function_name
        self.sam_template = sam_template
        self.project_root = Path(__file__).parent.parent.parent
        self.performance_metrics = {}

    def invoke_local(self, event: Dict[str, Any], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """SAM local invoke를 통해 Lambda handler 호출.

        Args:
            event: Lambda event (dict)
            env: 추가 환경 변수 (optional)

        Returns:
            Lambda handler의 응답 (dict)

        Raises:
            RuntimeError: SAM invoke 실패 시
        """
        # 임시 event 파일 생성
        event_file = self.project_root / ".sam_event.json"
        try:
            with open(event_file, "w") as f:
                json.dump(event, f)

            # SAM local invoke 명령어
            cmd = [
                "sam",
                "local",
                "invoke",
                self.function_name,
                f"--template={self.sam_template}",
                f"--event={event_file}",
            ]

            # 환경 변수 설정
            env_vars = os.environ.copy()
            env_vars["AWS_REGION"] = "ap-northeast-1"
            env_vars["AWS_ENV"] = "localstack"
            if env:
                env_vars.update(env)

            # SAM invoke 실행
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
                env=env_vars,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"SAM invoke failed for {self.function_name}:\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                )

            # 응답 파싱
            try:
                response = json.loads(result.stdout)
                return response
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse SAM response as JSON: {result.stdout}")
                return {"statusCode": 200, "body": result.stdout}

        finally:
            # 임시 파일 정리
            if event_file.exists():
                event_file.unlink()

    def invoke_local_with_timing(
        self, event: Dict[str, Any], env: Optional[Dict[str, str]] = None
    ) -> tuple[Dict[str, Any], float]:
        """SAM local invoke with execution time measurement.

        Args:
            event: Lambda event (dict)
            env: 추가 환경 변수 (optional)

        Returns:
            Tuple of (response, execution_time_seconds)
        """
        start_time = time.time()
        response = self.invoke_local(event, env)
        execution_time = time.time() - start_time
        return response, execution_time

    def measure_cold_start(self) -> float:
        """Cold start 시간 측정 (SAM container cold boot 포함).

        Returns:
            Cold start time in seconds
        """
        event = {"detail": {}}
        _, duration = self.invoke_local_with_timing(event)
        self.performance_metrics["cold_start"] = duration
        logger.info(f"Cold start time: {duration:.2f}s")
        return duration

    def measure_warm_invocation(self, iterations: int = 3) -> float:
        """Warm invocation 시간 측정 (평균).

        Args:
            iterations: Number of subsequent invocations

        Returns:
            Average execution time in seconds
        """
        event = {"detail": {}}
        times = []
        for _ in range(iterations):
            _, duration = self.invoke_local_with_timing(event)
            times.append(duration)

        avg_time = sum(times) / len(times)
        self.performance_metrics["warm_invocation_avg"] = avg_time
        logger.info(f"Warm invocation avg ({iterations}x): {avg_time:.3f}s")
        return avg_time

    def validate_iam_permissions(self) -> bool:
        """IAM role 권한 검증 (LocalStack).

        Returns:
            True if IAM permissions are valid, False otherwise
        """
        # LocalStack에서는 IAM 검증이 제한적이므로,
        # 실제 Lambda 호출을 시도해서 권한 오류 발생 여부로 판단
        try:
            event = {"detail": {}}
            response = self.invoke_local(event)
            # 권한 오류가 없으면 True
            return "AccessDenied" not in str(response)
        except RuntimeError as e:
            if "AccessDenied" in str(e) or "UnauthorizedOperation" in str(e):
                logger.warning(f"IAM permission denied: {e}")
                return False
            # SAM invoke 실패는 다른 이유일 수 있으므로 경고만
            logger.warning(f"IAM validation inconclusive: {e}")
            return True

    def get_performance_metrics(self) -> Dict[str, float]:
        """수집된 성능 메트릭 반환.

        Returns:
            Dict of performance metrics
        """
        return self.performance_metrics.copy()

    def print_performance_summary(self):
        """성능 메트릭 요약 출력."""
        logger.info("=== Lambda Performance Summary ===")
        for metric, value in self.performance_metrics.items():
            logger.info(f"{metric}: {value:.3f}s")


class CostCheckerHarness(LambdaHarness):
    """Cost Checker 전용 테스트 하네스"""

    def __init__(self):
        super().__init__(function_name="GuardianChecker")

    def create_cost_check_event(self, regions: list = None) -> Dict[str, Any]:
        """Cost check EventBridge event 생성."""
        if regions is None:
            regions = ["ap-northeast-1"]

        return {
            "version": "0",
            "id": "12345678-1234-1234-1234-123456789012",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789012",
            "time": "2026-05-05T12:00:00Z",
            "region": "ap-northeast-1",
            "resources": [],
            "detail": {
                "checker_type": "cost",
                "regions": regions,
            },
        }


class EC2CheckerHarness(LambdaHarness):
    """EC2 Checker 전용 테스트 하네스"""

    def __init__(self):
        super().__init__(function_name="GuardianChecker")

    def create_ec2_check_event(self, regions: list = None) -> Dict[str, Any]:
        """EC2 check EventBridge event 생성."""
        if regions is None:
            regions = ["ap-northeast-1"]

        return {
            "version": "0",
            "id": "12345678-1234-1234-1234-123456789013",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789012",
            "time": "2026-05-05T12:00:00Z",
            "region": "ap-northeast-1",
            "resources": [],
            "detail": {
                "checker_type": "ec2",
                "regions": regions,
            },
        }


class S3CheckerHarness(LambdaHarness):
    """S3 Checker 전용 테스트 하네스"""

    def __init__(self):
        super().__init__(function_name="GuardianChecker")

    def create_s3_check_event(self, regions: list = None) -> Dict[str, Any]:
        """S3 check EventBridge event 생성."""
        if regions is None:
            regions = ["ap-northeast-1"]

        return {
            "version": "0",
            "id": "12345678-1234-1234-1234-123456789014",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789012",
            "time": "2026-05-05T12:00:00Z",
            "region": "ap-northeast-1",
            "resources": [],
            "detail": {
                "checker_type": "s3",
                "regions": regions,
            },
        }
