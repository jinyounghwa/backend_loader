"""IAM policy analyzer tests for AWS Guardian."""

import os
import unittest
from unittest.mock import Mock

os.environ["AWS_ENV"] = "localstack"

import sys
from pathlib import Path

lambda_dir = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_dir))

from guardian.checkers.iam_policy_analyzer import IAMPolicyAnalyzer


class TestIAMPolicyAnalyzer(unittest.TestCase):
    """Test IAM policy analysis."""

    def setUp(self):
        """Setup mock IAM client."""
        self.mock_iam = Mock()
        self.mock_clients = {"iam": self.mock_iam}

        # Configure paginators
        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": []}]
        roles_paginator = Mock()
        roles_paginator.paginate.return_value = [{"Roles": []}]

        self.mock_iam.get_paginator.side_effect = lambda x: (
            users_paginator if x == "list_users" else roles_paginator
        )

    def test_no_policies(self):
        """Return INFO when no policies exist."""
        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "INFO")
        self.assertEqual(result.details["risky_policies"], 0)

    def test_policy_star_star_detected(self):
        """Detect Action=* and Resource=* (CRITICAL)."""
        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": [{"UserName": "admin"}]}]

        self.mock_iam.get_paginator.side_effect = lambda x: users_paginator

        self.mock_iam.get_user_policy.return_value = {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "*",
                        "Resource": "*",
                    }
                ]
            }
        }

        user_policies_paginator = Mock()
        user_policies_paginator.paginate.return_value = [{"PolicyNames": ["AdminPolicy"]}]

        original_side_effect = self.mock_iam.get_paginator.side_effect

        def get_paginator_impl(x):
            if x == "list_user_policies":
                return user_policies_paginator
            return original_side_effect(x)

        self.mock_iam.get_paginator.side_effect = get_paginator_impl

        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "CRITICAL")
        self.assertGreater(result.details["risky_policies"], 0)

    def test_policy_iam_full_access(self):
        """Detect 'iam:*' permission (HIGH)."""
        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": [{"UserName": "dev"}]}]

        user_policies_paginator = Mock()
        user_policies_paginator.paginate.return_value = [{"PolicyNames": ["DevPolicy"]}]

        self.mock_iam.get_paginator.side_effect = lambda x: (
            user_policies_paginator if x == "list_user_policies" else users_paginator
        )

        self.mock_iam.get_user_policy.return_value = {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "iam:*",
                        "Resource": "arn:aws:iam::123456789:user/dev",
                    }
                ]
            }
        }

        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "HIGH")
        self.assertGreater(result.details["risky_policies"], 0)

    def test_policy_ec2_full_access(self):
        """Detect 'ec2:*' permission (HIGH)."""
        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": [{"UserName": "ops"}]}]

        user_policies_paginator = Mock()
        user_policies_paginator.paginate.return_value = [{"PolicyNames": ["OpsPolicy"]}]

        self.mock_iam.get_paginator.side_effect = lambda x: (
            user_policies_paginator if x == "list_user_policies" else users_paginator
        )

        self.mock_iam.get_user_policy.return_value = {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "ec2:*",
                        "Resource": "*",
                    }
                ]
            }
        }

        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "HIGH")

    def test_policy_s3_public_read(self):
        """Detect S3 GetObject with Resource: '*' (HIGH)."""
        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": [{"UserName": "webapp"}]}]

        user_policies_paginator = Mock()
        user_policies_paginator.paginate.return_value = [{"PolicyNames": ["S3ReadPolicy"]}]

        self.mock_iam.get_paginator.side_effect = lambda x: (
            user_policies_paginator if x == "list_user_policies" else users_paginator
        )

        self.mock_iam.get_user_policy.return_value = {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "s3:GetObject",
                        "Resource": "*",
                    }
                ]
            }
        }

        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "HIGH")

    def test_policy_notaction(self):
        """Detect NotAction with Deny Effect (MEDIUM)."""
        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": [{"UserName": "restricted"}]}]

        user_policies_paginator = Mock()
        user_policies_paginator.paginate.return_value = [{"PolicyNames": ["DenyPolicy"]}]

        self.mock_iam.get_paginator.side_effect = lambda x: (
            user_policies_paginator if x == "list_user_policies" else users_paginator
        )

        self.mock_iam.get_user_policy.return_value = {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Deny",
                        "NotAction": ["s3:DeleteBucket"],
                        "Resource": "*",
                    }
                ]
            }
        }

        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "MEDIUM")

    def test_policy_safe(self):
        """Return INFO for restrictive policies."""
        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": [{"UserName": "safe"}]}]

        user_policies_paginator = Mock()
        user_policies_paginator.paginate.return_value = [{"PolicyNames": ["SafePolicy"]}]

        self.mock_iam.get_paginator.side_effect = lambda x: (
            user_policies_paginator if x == "list_user_policies" else users_paginator
        )

        self.mock_iam.get_user_policy.return_value = {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject"],
                        "Resource": "arn:aws:s3:::my-bucket/*",
                    }
                ]
            }
        }

        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "INFO")
        self.assertEqual(result.details["risky_policies"], 0)

    def test_policy_list_actions(self):
        """Handle policies with list of actions."""
        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": [{"UserName": "listing"}]}]

        user_policies_paginator = Mock()
        user_policies_paginator.paginate.return_value = [{"PolicyNames": ["ListPolicy"]}]

        self.mock_iam.get_paginator.side_effect = lambda x: (
            user_policies_paginator if x == "list_user_policies" else users_paginator
        )

        self.mock_iam.get_user_policy.return_value = {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject", "s3:ListBucket"],
                        "Resource": ["arn:aws:s3:::bucket1/*", "arn:aws:s3:::bucket1"],
                    }
                ]
            }
        }

        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "INFO")

    def test_policy_with_roles(self):
        """Analyze policies attached to roles."""
        roles_paginator = Mock()
        roles_paginator.paginate.return_value = [{"Roles": [{"RoleName": "LambdaRole"}]}]

        role_policies_paginator = Mock()
        role_policies_paginator.paginate.return_value = [{"PolicyNames": ["LambdaPolicy"]}]

        users_paginator = Mock()
        users_paginator.paginate.return_value = [{"Users": []}]

        def get_paginator_impl(x):
            if x == "list_users":
                return users_paginator
            elif x == "list_role_policies":
                return role_policies_paginator
            else:
                return roles_paginator

        self.mock_iam.get_paginator.side_effect = get_paginator_impl

        self.mock_iam.get_role_policy.return_value = {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "dynamodb:*",
                        "Resource": "*",
                    }
                ]
            }
        }

        checker = IAMPolicyAnalyzer(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "HIGH")


if __name__ == "__main__":
    unittest.main()
