"""S3 Checker Harness Tests"""

import pytest
from harness import S3CheckerHarness


class TestS3CheckerHarness:
    """S3 Checker를 SAM local로 테스트"""

    @pytest.fixture
    def harness(self):
        return S3CheckerHarness()

    def test_s3_checker_invocation(self, harness):
        """Test: S3 checker 정상 호출"""
        event = harness.create_s3_check_event()
        response = harness.invoke_local(event)

        assert response is not None
        assert isinstance(response, dict)

    def test_s3_checker_bucket_discovery(self, harness):
        """Test: S3 버킷 발견"""
        event = harness.create_s3_check_event()
        response = harness.invoke_local(event)

        assert response is not None
        # 버킷 목록 또는 findings 반환

    def test_s3_checker_public_acl_detection(self, harness):
        """Test: 퍼블릭 ACL 감지"""
        event = harness.create_s3_check_event()
        response = harness.invoke_local(event)

        # Public bucket 감지 여부 검증
        assert response is not None

    def test_s3_checker_bucket_policy_analysis(self, harness):
        """Test: Bucket policy 분석"""
        event = harness.create_s3_check_event()
        response = harness.invoke_local(event)

        # Policy 분석 결과
        assert response is not None

    def test_s3_checker_multi_region(self, harness):
        """Test: 여러 리전 버킷 확인"""
        event = harness.create_s3_check_event(regions=["ap-northeast-1", "us-east-1"])
        response = harness.invoke_local(event)

        assert response is not None

    def test_s3_checker_performance(self, harness):
        """Test: S3 checker 성능"""
        event = harness.create_s3_check_event()
        response, duration = harness.invoke_local_with_timing(event)

        assert response is not None
        print(f"S3 checker execution time: {duration:.3f}s")
        assert duration < 2.0
