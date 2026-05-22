"""Tests for checker implementations (sync-first model).

All checkers now implement ``check()`` (sync). ``check_async()``
is auto-provided by ``BaseChecker`` via ``run_in_executor``.
Tests mock the sync boto3 clients directly.
"""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from guardian.checkers.cost import CostChecker
from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.s3 import S3Checker
from guardian.checkers.cloudtrail import CloudTrailChecker
from guardian.checkers.iam import IAMChecker
from guardian.checkers.guardduty import GuardDutyChecker


class TestCostCheckerSync(unittest.TestCase):
    """Test sync Cost Explorer integration."""

    def test_check_no_anomalies(self):
        """Test check when costs are normal."""
        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {"TimePeriod": {"Start": "2024-01-01"}, "Total": {"UnblendedCost": {"Amount": "5.00"}}}
            ]
        }

        checker = CostChecker(clients={"ce": mock_ce}, config={"cost_threshold": 100})
        result = checker.check()

        self.assertEqual(result.severity, "INFO")

    @patch("guardian.checkers.cost.Config.is_localstack", return_value=False)
    def test_check_cost_anomaly(self, mock_ls):
        """Test check when daily cost exceeds threshold."""
        mock_ce = MagicMock()
        # CostChecker calls get_cost_and_usage 3 times: today, yesterday, monthly
        high_cost_response = {
            "ResultsByTime": [
                {"TimePeriod": {"Start": "2024-01-01"}, "Total": {"UnblendedCost": {"Amount": "150.00"}}}
            ]
        }
        monthly_cost_response = {
            "ResultsByTime": [
                {"TimePeriod": {"Start": "2024-01-01"}, "Total": {"UnblendedCost": {"Amount": "4500.00"}}}
            ]
        }
        mock_ce.get_cost_and_usage.side_effect = [
            high_cost_response,   # today
            high_cost_response,   # yesterday
            monthly_cost_response,  # monthly
        ]

        checker = CostChecker(clients={"ce": mock_ce, "ssm": MagicMock()}, config={"cost_threshold": 100})
        result = checker.check()

        self.assertEqual(result.severity, "HIGH")
        self.assertIn("exceeds", result.message.lower())


class TestEC2CheckerSync(unittest.TestCase):
    """Test sync EC2 security checks."""

    @patch("guardian.checkers.ec2.AWSClientProvider.get_client")
    def test_check_no_instances(self, mock_get_client):
        """Test check when no EC2 instances running."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}
        mock_ec2.describe_instances.return_value = {"Reservations": []}
        mock_get_client.return_value = mock_ec2

        checker = EC2Checker(config={"authorized_regions": ["us-east-1"]})
        result = checker.check()

        self.assertEqual(result.severity, "INFO")

    @patch("guardian.checkers.ec2.Config.is_localstack", return_value=False)
    @patch("guardian.checkers.ec2.AWSClientProvider.get_client")
    def test_check_unauthorized_region(self, mock_get_client, mock_ls):
        """Test check detects instances in unauthorized regions."""
        mock_global = MagicMock()
        mock_global.describe_regions.return_value = {
            "Regions": [
                {"RegionName": "us-east-1"},
                {"RegionName": "eu-west-1"},
            ]
        }

        mock_us_east = MagicMock()
        mock_us_east.describe_instances.return_value = {"Reservations": []}

        mock_eu_west = MagicMock()
        mock_eu_west.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-unauthorized",
                            "InstanceType": "t2.micro",
                            "LaunchTime": datetime.now(timezone.utc) - timedelta(days=1),
                            "SecurityGroups": [],
                            "Tags": [],
                        }
                    ]
                }
            ]
        }

        def client_factory(service, region=None):
            if service != "ec2" or region is None:
                return mock_global
            if region == "us-east-1":
                return mock_us_east
            if region == "eu-west-1":
                return mock_eu_west
            return MagicMock()

        mock_get_client.side_effect = client_factory

        checker = EC2Checker(config={"authorized_regions": ["us-east-1"]})
        result = checker.check()

        self.assertIn(result.severity, ["HIGH", "CRITICAL"])


class TestS3CheckerSync(unittest.TestCase):
    """Test sync S3 bucket security checks."""

    def test_check_all_secure(self):
        """Test check when all buckets are secure."""
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {
            "Buckets": [
                {"Name": "secure-bucket", "CreationDate": datetime.now(timezone.utc) - timedelta(days=2)}
            ]
        }
        mock_s3.get_bucket_acl.return_value = {"Grants": []}
        mock_s3.get_bucket_policy.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucketPolicy", "Message": "No policy"}}, "GetBucketPolicy"
        )
        mock_s3.get_public_access_block.return_value = {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        }

        checker = S3Checker(clients={"s3": mock_s3})
        result = checker.check()

        self.assertEqual(result.severity, "INFO")

    def test_check_public_bucket_detected(self):
        """Test check detects public buckets."""
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {
            "Buckets": [
                {"Name": "public-bucket", "CreationDate": datetime.now(timezone.utc) - timedelta(days=1)}
            ]
        }
        mock_s3.get_bucket_acl.return_value = {
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
        mock_s3.get_bucket_policy.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucketPolicy", "Message": "No policy"}}, "GetBucketPolicy"
        )

        checker = S3Checker(clients={"s3": mock_s3})
        result = checker.check()

        self.assertEqual(result.severity, "CRITICAL")
        self.assertIn("S3", result.title)


class TestCloudTrailCheckerSync(unittest.TestCase):
    """Test sync CloudTrail suspicious activity detection."""

    def test_check_no_suspicious_events(self):
        """Test check when no suspicious events found."""
        mock_ct = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Events": []}]
        mock_ct.get_paginator.return_value = mock_paginator

        checker = CloudTrailChecker(clients={"cloudtrail": mock_ct})
        result = checker.check()

        self.assertEqual(result.severity, "INFO")

    def test_check_root_account_activity(self):
        """Test check detects root account activity."""
        mock_ct = MagicMock()
        mock_paginator = MagicMock()

        event = {
            "EventName": "DescribeInstances",
            "Username": "root",
            "EventTime": datetime.now(timezone.utc),
            "SourceIPAddress": "1.2.3.4",
            "CloudTrailEvent": "{}",
        }

        # First source returns the event, rest return empty
        mock_paginator.paginate.side_effect = [
            [{"Events": [event]}],  # iam.amazonaws.com
            [{"Events": []}],       # ec2.amazonaws.com
            [{"Events": []}],       # s3.amazonaws.com
            [{"Events": []}],       # dynamodb.amazonaws.com
            [{"Events": []}],       # rds.amazonaws.com
        ]
        mock_ct.get_paginator.return_value = mock_paginator

        checker = CloudTrailChecker(clients={"cloudtrail": mock_ct})
        result = checker.check()

        self.assertEqual(result.severity, "CRITICAL")


class TestIAMCheckerSync(unittest.TestCase):
    """Test sync IAM permission change detection."""

    def test_check_no_baseline_no_changes(self):
        """Test check when no baseline exists and no users."""
        mock_iam = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Users": []}]
        mock_iam.get_paginator.return_value = mock_paginator

        checker = IAMChecker(clients={"iam": mock_iam, "dynamodb_resource": None})
        result = checker.check()

        self.assertEqual(result.severity, "INFO")


class TestGuardDutyCheckerSync(unittest.TestCase):
    """Test sync GuardDuty threat detection."""

    def test_check_no_findings(self):
        """Test check when no GuardDuty findings."""
        mock_gd = MagicMock()
        mock_gd.list_detectors.return_value = {"DetectorIds": ["detector-123"]}
        mock_gd.list_findings.return_value = {"FindingIds": []}

        checker = GuardDutyChecker(clients={"guardduty": mock_gd})
        result = checker.check()

        self.assertEqual(result.severity, "INFO")

    def test_check_critical_findings(self):
        """Test check detects critical threat findings."""
        mock_gd = MagicMock()
        mock_gd.list_detectors.return_value = {"DetectorIds": ["detector-123"]}
        mock_gd.list_findings.return_value = {"FindingIds": ["finding-1"]}
        mock_gd.get_findings.return_value = {
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

        checker = GuardDutyChecker(clients={"guardduty": mock_gd})
        result = checker.check()

        self.assertEqual(result.severity, "CRITICAL")
        self.assertIn("threat", result.message.lower())


if __name__ == "__main__":
    unittest.main()
