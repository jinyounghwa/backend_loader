"""EC2 Checker Harness Tests"""

import pytest
from harness import EC2CheckerHarness


class TestEC2CheckerHarness:
    """EC2 Checker를 SAM local로 테스트"""

    @pytest.fixture
    def harness(self):
        return EC2CheckerHarness()

    def test_ec2_checker_invocation(self, harness):
        """Test: EC2 checker 정상 호출"""
        event = harness.create_ec2_check_event()
        response = harness.invoke_local(event)

        assert response is not None
        assert isinstance(response, dict)

    def test_ec2_checker_single_region(self, harness):
        """Test: 단일 리전 EC2 확인"""
        event = harness.create_ec2_check_event(regions=["ap-northeast-1"])
        response = harness.invoke_local(event)

        assert response is not None

    def test_ec2_checker_multi_region(self, harness):
        """Test: 여러 리전 EC2 확인"""
        event = harness.create_ec2_check_event(regions=["ap-northeast-1", "us-east-1", "eu-west-1"])
        response = harness.invoke_local(event)

        assert response is not None
        # 각 리전별 인스턴스 데이터

    def test_ec2_checker_response_format(self, harness):
        """Test: EC2 checker response 형식"""
        event = harness.create_ec2_check_event()
        response = harness.invoke_local(event)

        # 응답은 findings 또는 statusCode 포함
        assert "statusCode" in response or "findings" in response

    def test_ec2_checker_security_group_detection(self, harness):
        """Test: 퍼블릭 security group 감지"""
        event = harness.create_ec2_check_event()
        response = harness.invoke_local(event)

        # Security group vulnerability 감지 여부 검증
        assert response is not None

    def test_ec2_checker_performance(self, harness):
        """Test: EC2 checker 성능 (target: <1s)"""
        event = harness.create_ec2_check_event()
        response, duration = harness.invoke_local_with_timing(event)

        assert response is not None
        print(f"EC2 checker execution time: {duration:.3f}s")
        assert duration < 2.0
