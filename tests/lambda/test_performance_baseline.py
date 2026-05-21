"""Performance baseline tests for AWS Guardian checkers."""

import os
import time
import unittest
from unittest.mock import Mock, patch

import sys
from pathlib import Path

# Set localstack mode to avoid real AWS calls
os.environ["AWS_ENV"] = "localstack"

# Add lambda directory to path
lambda_dir = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))

from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.s3 import S3Checker
from guardian.checkers.cost import CostChecker
from guardian.checkers.iam import IAMChecker
from guardian.checkers.cloudtrail import CloudTrailChecker
from guardian.checkers.guardduty import GuardDutyChecker


class TestCheckerPerformance(unittest.TestCase):
    """Measure individual checker performance."""

    def setUp(self):
        """Create mock clients for testing."""
        self.mock_clients = {
            "ec2": Mock(),
            "s3": Mock(),
            "iam": Mock(),
            "cloudtrail": Mock(),
            "ce": Mock(),
            "guardduty": Mock(),
        }

        # Configure EC2
        ec2_paginator = Mock()
        ec2_paginator.paginate.return_value = [{"Reservations": []}]
        self.mock_clients["ec2"].get_paginator.return_value = ec2_paginator
        self.mock_clients["ec2"].describe_instances.return_value = {"Reservations": []}
        self.mock_clients["ec2"].describe_security_groups.return_value = {
            "SecurityGroups": []
        }

        # Configure S3
        self.mock_clients["s3"].list_buckets.return_value = {"Buckets": []}
        self.mock_clients["s3"].get_bucket_acl.return_value = {"Grants": []}
        self.mock_clients["s3"].get_public_access_block.side_effect = Exception(
            "NoSuchPublicAccessBlockConfiguration"
        )

        # Configure IAM
        iam_paginator = Mock()
        iam_paginator.paginate.return_value = [{"Users": []}]
        self.mock_clients["iam"].get_paginator.return_value = iam_paginator

        # Configure CloudTrail
        ct_paginator = Mock()
        ct_paginator.paginate.return_value = [{"Events": []}]
        self.mock_clients["cloudtrail"].get_paginator.return_value = ct_paginator
        self.mock_clients["cloudtrail"].list_detectors.return_value = {"DetectorIds": []}

        # Configure Cost Explorer
        self.mock_clients["ce"].get_cost_and_usage.return_value = {"ResultsByTime": []}

        # Configure GuardDuty
        self.mock_clients["guardduty"].list_detectors.return_value = {"DetectorIds": []}

    @patch("guardian.aws_client_provider.AWSClientProvider.get_client")
    def test_ec2_checker_performance(self, mock_get_client):
        """EC2 checker should complete in < 500ms."""
        mock_get_client.return_value = self.mock_clients["ec2"]
        checker = EC2Checker(clients=self.mock_clients)

        start = time.perf_counter()
        result = checker.check()
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.5)
        self.assertIsNotNone(result.severity)

    @patch("guardian.aws_client_provider.AWSClientProvider.get_client")
    def test_s3_checker_performance(self, mock_get_client):
        """S3 checker should complete in < 500ms."""
        mock_get_client.return_value = self.mock_clients["s3"]
        checker = S3Checker(clients=self.mock_clients)

        start = time.perf_counter()
        result = checker.check()
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.5)
        self.assertIsNotNone(result.severity)

    @patch("guardian.aws_client_provider.AWSClientProvider.get_client")
    def test_cost_checker_performance(self, mock_get_client):
        """Cost checker should complete in < 500ms."""
        mock_get_client.return_value = self.mock_clients["ce"]
        checker = CostChecker(clients=self.mock_clients, config={"cost_threshold": 10.0})

        start = time.perf_counter()
        result = checker.check()
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.5)
        self.assertIsNotNone(result.severity)

    @patch("guardian.aws_client_provider.AWSClientProvider.get_client")
    def test_iam_checker_performance(self, mock_get_client):
        """IAM checker should complete in < 500ms."""
        mock_get_client.return_value = self.mock_clients["iam"]
        checker = IAMChecker(clients=self.mock_clients)

        start = time.perf_counter()
        result = checker.check()
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.5)
        self.assertIsNotNone(result.severity)

    @patch("guardian.aws_client_provider.AWSClientProvider.get_client")
    def test_cloudtrail_checker_performance(self, mock_get_client):
        """CloudTrail checker should complete in < 500ms."""
        mock_get_client.return_value = self.mock_clients["cloudtrail"]
        checker = CloudTrailChecker(clients=self.mock_clients)

        start = time.perf_counter()
        result = checker.check()
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.5)
        self.assertIsNotNone(result.severity)

    @patch("guardian.aws_client_provider.AWSClientProvider.get_client")
    def test_guardduty_checker_performance(self, mock_get_client):
        """GuardDuty checker should complete in < 500ms."""
        mock_get_client.return_value = self.mock_clients["guardduty"]
        checker = GuardDutyChecker(clients=self.mock_clients)

        start = time.perf_counter()
        result = checker.check()
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.5)
        self.assertIsNotNone(result.severity)

    @patch("guardian.aws_client_provider.AWSClientProvider.get_client")
    def test_all_checkers_combined(self, mock_get_client):
        """All 6 checkers together should complete in < 2 seconds."""
        def get_client_side_effect(service, **kwargs):
            return self.mock_clients.get(service, Mock())

        mock_get_client.side_effect = get_client_side_effect

        checkers = [
            EC2Checker(clients=self.mock_clients),
            S3Checker(clients=self.mock_clients),
            IAMChecker(clients=self.mock_clients),
            CloudTrailChecker(clients=self.mock_clients),
            CostChecker(clients=self.mock_clients, config={"cost_threshold": 10.0}),
            GuardDutyChecker(clients=self.mock_clients),
        ]

        start = time.perf_counter()
        results = [checker.check() for checker in checkers]
        elapsed = time.perf_counter() - start

        # All checkers together should be < 2 seconds
        self.assertLess(elapsed, 2.0)
        self.assertEqual(len(results), 6)


if __name__ == "__main__":
    unittest.main()
