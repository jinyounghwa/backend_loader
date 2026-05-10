"""Tests for async checker implementations using aioboto3."""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from guardian.checkers.cost import CostChecker
from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.s3 import S3Checker
from guardian.checkers.cloudtrail import CloudTrailChecker
from guardian.checkers.iam import IAMChecker
from guardian.checkers.guardduty import GuardDutyChecker


class AsyncTestCase(unittest.TestCase):
    """Base test case for async tests."""

    def setUp(self):
        """Set up event loop for each test."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up event loop after each test."""
        self.loop.close()

    def async_test(self, coro):
        """Helper to run async functions in tests."""
        return self.loop.run_until_complete(coro)


class TestCostCheckerAsync(AsyncTestCase):
    """Test async Cost Explorer integration."""

    @patch("guardian.checkers.cost.AWSClientProvider.get_async_client")
    def test_check_async_no_anomalies(self, mock_get_client):
        """Test check_async when costs are normal."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        today = datetime.now(timezone.utc).date().isoformat()
        mock_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {"TimePeriod": {"Start": today}, "Total": {"UnblendedCost": {"Amount": "5.00"}}}
            ]
        }

        checker = CostChecker({}, {"daily_cost_threshold": 100})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "INFO")
        self.assertIn("within budget", result.message.lower())

    @patch("guardian.checkers.cost.AWSClientProvider.get_async_client")
    def test_check_async_cost_anomaly(self, mock_get_client):
        """Test check_async when daily cost exceeds threshold."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        today = datetime.now(timezone.utc).date().isoformat()
        mock_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {"TimePeriod": {"Start": today}, "Total": {"UnblendedCost": {"Amount": "150.00"}}}
            ]
        }

        checker = CostChecker({}, {"daily_cost_threshold": 100})
        result = self.async_test(checker.check_async())

        self.assertIn(["HIGH", "CRITICAL"], [result.severity])
        self.assertIn("exceeded", result.message.lower())


class TestEC2CheckerAsync(AsyncTestCase):
    """Test async EC2 security checks."""

    @patch("guardian.checkers.ec2.AWSClientProvider.get_async_client")
    def test_check_async_no_instances(self, mock_get_client):
        """Test check_async when no EC2 instances running."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}
        mock_client.describe_instances.return_value = {"Reservations": []}

        checker = EC2Checker({}, {"authorized_regions": ["us-east-1"]})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "INFO")

    @patch("guardian.checkers.ec2.AWSClientProvider.get_async_client")
    def test_check_async_unauthorized_region(self, mock_get_client):
        """Test check_async detects instances in unauthorized regions."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.describe_regions.return_value = {
            "Regions": [
                {"RegionName": "us-east-1"},
                {"RegionName": "eu-west-1"}
            ]
        }
        mock_client.describe_instances.side_effect = [
            {"Reservations": []},
            {
                "Reservations": [
                    {
                        "Instances": [
                            {
                                "InstanceId": "i-unauthorized",
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

        checker = EC2Checker({}, {"authorized_regions": ["us-east-1"]})
        result = self.async_test(checker.check_async())

        self.assertIn(result.severity, ["HIGH", "CRITICAL"])
        self.assertIn("unauthorized regions", result.message.lower())


class TestS3CheckerAsync(AsyncTestCase):
    """Test async S3 bucket security checks."""

    @patch("guardian.checkers.s3.AWSClientProvider.get_async_client")
    def test_check_async_all_secure(self, mock_get_client):
        """Test check_async when all buckets are secure."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [
                {"Name": "secure-bucket", "CreationDate": datetime.now(timezone.utc)}
            ]
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

        checker = S3Checker({}, {})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "INFO")

    @patch("guardian.checkers.s3.AWSClientProvider.get_async_client")
    def test_check_async_public_bucket_detected(self, mock_get_client):
        """Test check_async detects public buckets."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.list_buckets.return_value = {
            "Buckets": [
                {"Name": "public-bucket", "CreationDate": datetime.now(timezone.utc) - timedelta(days=1)}
            ]
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

        checker = S3Checker({}, {})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "CRITICAL")
        self.assertIn("public", result.message.lower())


class TestCloudTrailCheckerAsync(AsyncTestCase):
    """Test async CloudTrail suspicious activity detection."""

    @patch("guardian.checkers.cloudtrail.AWSClientProvider.get_async_client")
    def test_check_async_no_suspicious_events(self, mock_get_client):
        """Test check_async when no suspicious events found."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_paginator = AsyncMock()
        mock_client.get_paginator.return_value = mock_paginator

        async def mock_paginate(*args, **kwargs):
            yield {"Events": []}

        mock_paginator.paginate.return_value = mock_paginate()

        checker = CloudTrailChecker({}, {})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "INFO")

    @patch("guardian.checkers.cloudtrail.AWSClientProvider.get_async_client")
    def test_check_async_root_account_activity(self, mock_get_client):
        """Test check_async detects root account activity."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_paginator = AsyncMock()
        mock_client.get_paginator.return_value = mock_paginator

        async def mock_paginate(*args, **kwargs):
            yield {
                "Events": [
                    {
                        "EventName": "DescribeInstances",
                        "Username": "root",
                        "EventTime": datetime.now(timezone.utc),
                        "SourceIPAddress": "1.2.3.4",
                        "CloudTrailEvent": "{}",
                    }
                ]
            }

        mock_paginator.paginate.return_value = mock_paginate()

        checker = CloudTrailChecker({}, {})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "CRITICAL")
        self.assertIn("root", result.message.lower())


class TestIAMCheckerAsync(AsyncTestCase):
    """Test async IAM permission change detection."""

    @patch("guardian.checkers.iam.AWSClientProvider.get_async_client")
    def test_check_async_no_baseline(self, mock_get_client):
        """Test check_async when no baseline exists yet."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_paginator = AsyncMock()
        mock_client.get_paginator.return_value = mock_paginator

        async def mock_paginate(*args, **kwargs):
            yield {"Users": []}

        mock_paginator.paginate.return_value = mock_paginate()

        checker = IAMChecker({"dynamodb_resource": None}, {})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "INFO")


class TestGuardDutyCheckerAsync(AsyncTestCase):
    """Test async GuardDuty threat detection."""

    @patch("guardian.checkers.guardduty.AWSClientProvider.get_async_client")
    def test_check_async_no_findings(self, mock_get_client):
        """Test check_async when no GuardDuty findings."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.list_detectors.return_value = {"DetectorIds": ["detector-123"]}
        mock_client.list_findings.return_value = {"FindingIds": []}

        checker = GuardDutyChecker({}, {})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "INFO")

    @patch("guardian.checkers.guardduty.AWSClientProvider.get_async_client")
    def test_check_async_critical_findings(self, mock_get_client):
        """Test check_async detects critical threat findings."""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client

        mock_client.list_detectors.return_value = {"DetectorIds": ["detector-123"]}
        mock_client.list_findings.return_value = {
            "FindingIds": ["finding-1"]
        }
        mock_client.get_findings.return_value = {
            "Findings": [
                {
                    "Id": "finding-1",
                    "Type": "UnauthorizedAccess:EC2/SSHBruteForce",
                    "Severity": 7.0,
                    "Title": "SSH Brute Force Attack",
                    "Description": "Detected brute force SSH attack",
                    "Resource": {
                        "ResourceType": "Instance",
                        "InstanceDetails": {"InstanceId": "i-12345"},
                    },
                    "UpdatedAt": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
            ]
        }

        checker = GuardDutyChecker({}, {})
        result = self.async_test(checker.check_async())

        self.assertEqual(result.severity, "CRITICAL")
        self.assertIn("threat", result.message.lower())


if __name__ == "__main__":
    unittest.main()
