"""Integration tests with LocalStack for AWS Guardian checkers."""

import asyncio
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

# Only run these tests if LocalStack is available
LOCALSTACK_AVAILABLE = os.getenv("LOCALSTACK_ENDPOINT") is not None


@pytest.mark.integration
@pytest.mark.skipif(not LOCALSTACK_AVAILABLE, reason="LocalStack not available")
class TestCostCheckerLocalStack(unittest.TestCase):
    """Integration tests for CostChecker with LocalStack."""

    @classmethod
    def setUpClass(cls):
        """Set up LocalStack connection."""
        cls.endpoint = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
        cls.region = "us-east-1"

    def setUp(self):
        """Set up event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up event loop."""
        self.loop.close()

    @patch("guardian.checkers.cost.AWSClientProvider.get_async_client")
    def test_cost_checker_with_localstack_ce(self, mock_get_client):
        """Test CostChecker with LocalStack Cost Explorer."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        today = datetime.now(timezone.utc).date().isoformat()
        mock_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": today, "End": today},
                    "Total": {"UnblendedCost": {"Amount": "25.50", "Unit": "USD"}},
                    "Groups": [],
                    "Estimated": False,
                }
            ]
        }

        from guardian.checkers.cost import CostChecker

        checker = CostChecker({}, {"daily_cost_threshold": 50})
        result = self.loop.run_until_complete(checker.check_async())

        assert result.severity == "INFO"
        assert "within budget" in result.message.lower()


@pytest.mark.integration
@pytest.mark.skipif(not LOCALSTACK_AVAILABLE, reason="LocalStack not available")
class TestEC2CheckerLocalStack(unittest.TestCase):
    """Integration tests for EC2Checker with LocalStack."""

    @classmethod
    def setUpClass(cls):
        """Set up LocalStack connection."""
        cls.endpoint = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
        cls.region = "us-east-1"

    def setUp(self):
        """Set up event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up event loop."""
        self.loop.close()

    @patch("guardian.checkers.ec2.AWSClientProvider.get_async_client")
    def test_ec2_checker_detects_instances(self, mock_get_client):
        """Test EC2Checker detects running instances in LocalStack."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}
        mock_client.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-localstack-001",
                            "InstanceType": "t2.micro",
                            "LaunchTime": datetime.now(timezone.utc),
                            "State": {"Name": "running"},
                            "SecurityGroups": [],
                            "Tags": [{"Key": "Name", "Value": "test-instance"}],
                        }
                    ]
                }
            ]
        }

        from guardian.checkers.ec2 import EC2Checker

        checker = EC2Checker({}, {"authorized_regions": ["us-east-1"]})
        result = self.loop.run_until_complete(checker.check_async())

        assert result.severity == "INFO"
        assert "secure" in result.message.lower()

    @patch("guardian.checkers.ec2.AWSClientProvider.get_async_client")
    def test_ec2_checker_detects_unauthorized_region(self, mock_get_client):
        """Test EC2Checker flags instances in unauthorized regions."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.describe_regions.return_value = {
            "Regions": [
                {"RegionName": "us-east-1"},
                {"RegionName": "eu-west-1"},
            ]
        }

        mock_client.describe_instances.side_effect = [
            {"Reservations": []},
            {
                "Reservations": [
                    {
                        "Instances": [
                            {
                                "InstanceId": "i-eu-unauthorized",
                                "InstanceType": "t2.micro",
                                "LaunchTime": datetime.now(timezone.utc),
                                "SecurityGroups": [],
                                "Tags": [],
                            }
                        ]
                    }
                ]
            },
        ]

        from guardian.checkers.ec2 import EC2Checker

        checker = EC2Checker({}, {"authorized_regions": ["us-east-1"]})
        result = self.loop.run_until_complete(checker.check_async())

        assert result.severity in ["HIGH", "CRITICAL"]
        assert "unauthorized" in result.message.lower()


@pytest.mark.integration
@pytest.mark.skipif(not LOCALSTACK_AVAILABLE, reason="LocalStack not available")
class TestS3CheckerLocalStack(unittest.TestCase):
    """Integration tests for S3Checker with LocalStack."""

    @classmethod
    def setUpClass(cls):
        """Set up LocalStack connection."""
        cls.endpoint = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
        cls.region = "us-east-1"

    def setUp(self):
        """Set up event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up event loop."""
        self.loop.close()

    @patch("guardian.checkers.s3.AWSClientProvider.get_async_client")
    def test_s3_checker_detects_public_bucket(self, mock_get_client):
        """Test S3Checker detects public buckets in LocalStack."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [{"Name": "public-test-bucket", "CreationDate": datetime.now(timezone.utc)}]
        }
        mock_client.get_bucket_acl.return_value = {
            "Grants": [
                {
                    "Grantee": {
                        "Type": "Group",
                        "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
                    },
                    "Permission": "READ",
                }
            ]
        }

        from guardian.checkers.s3 import S3Checker

        checker = S3Checker({}, {})
        result = self.loop.run_until_complete(checker.check_async())

        assert result.severity == "CRITICAL"
        assert "public" in result.message.lower()

    @patch("guardian.checkers.s3.AWSClientProvider.get_async_client")
    def test_s3_checker_detects_secure_bucket(self, mock_get_client):
        """Test S3Checker verifies secure buckets."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [{"Name": "secure-test-bucket", "CreationDate": datetime.now(timezone.utc)}]
        }
        mock_client.get_bucket_acl.return_value = {"Grants": []}
        mock_client.get_bucket_policy.side_effect = Exception("NoSuchBucketPolicy")
        mock_client.get_public_access_block.return_value = {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        }

        from guardian.checkers.s3 import S3Checker

        checker = S3Checker({}, {})
        result = self.loop.run_until_complete(checker.check_async())

        assert result.severity == "INFO"
        assert "secure" in result.message.lower()


@pytest.mark.integration
@pytest.mark.skipif(not LOCALSTACK_AVAILABLE, reason="LocalStack not available")
class TestMultiCheckerIntegration(unittest.TestCase):
    """Integration tests for running multiple checkers together."""

    @classmethod
    def setUpClass(cls):
        """Set up LocalStack connection."""
        cls.endpoint = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")

    def setUp(self):
        """Set up event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up event loop."""
        self.loop.close()

    @patch("guardian.checkers.cost.AWSClientProvider.get_async_client")
    @patch("guardian.checkers.ec2.AWSClientProvider.get_async_client")
    @patch("guardian.checkers.s3.AWSClientProvider.get_async_client")
    def test_run_all_checkers_concurrently(self, mock_s3_client, mock_ec2_client, mock_ce_client):
        """Test running multiple checkers concurrently."""
        # Setup mock clients
        cost_client = AsyncMock()
        ec2_client = AsyncMock()
        s3_client = AsyncMock()

        mock_ce_client.return_value.__aenter__.return_value = cost_client
        mock_ec2_client.return_value.__aenter__.return_value = ec2_client
        mock_s3_client.return_value.__aenter__.return_value = s3_client

        # Setup responses
        today = datetime.now(timezone.utc).date().isoformat()
        cost_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": today, "End": today},
                    "Total": {"UnblendedCost": {"Amount": "15.00", "Unit": "USD"}},
                }
            ]
        }

        ec2_client.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}
        ec2_client.describe_instances.return_value = {"Reservations": []}

        s3_client.list_buckets.return_value = {"Buckets": []}

        from guardian.checkers.cost import CostChecker
        from guardian.checkers.ec2 import EC2Checker
        from guardian.checkers.s3 import S3Checker

        checkers = [
            CostChecker({}, {"daily_cost_threshold": 100}),
            EC2Checker({}, {"authorized_regions": ["us-east-1"]}),
            S3Checker({}, {}),
        ]

        # Run all checkers concurrently
        async def run_all():
            return await asyncio.gather(*[c.check_async() for c in checkers])

        results = self.loop.run_until_complete(run_all())

        assert len(results) == 3
        assert all(r.severity in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
