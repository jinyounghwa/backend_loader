"""RDS checker tests for AWS Guardian."""

import os
import unittest
from unittest.mock import Mock

os.environ["AWS_ENV"] = "localstack"

import sys
from pathlib import Path
from guardian.checkers.rds import RDSChecker


class TestRDSChecker(unittest.TestCase):
    """Test RDS security checks."""

    def setUp(self):
        """Setup mock RDS client."""
        self.mock_rds = Mock()
        self.mock_clients = {"rds": self.mock_rds}

        # Configure paginator
        paginator = Mock()
        paginator.paginate.return_value = [{"DBInstances": []}]
        self.mock_rds.get_paginator.return_value = paginator

    def test_rds_no_instances(self):
        """Return INFO when no RDS instances exist."""
        checker = RDSChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "INFO")
        self.assertEqual(result.details["instance_count"], 0)

    def test_rds_public_instance_detected(self):
        """Detect publicly accessible RDS instances."""
        public_instance = {
            "DBInstanceIdentifier": "prod-db-1",
            "Engine": "postgres",
            "PubliclyAccessible": True,
            "StorageEncrypted": True,
            "BackupRetentionPeriod": 7,
            "IAMDatabaseAuthenticationEnabled": True,
            "EnabledCloudwatchLogsExports": ["postgresql"],
        }

        paginator = Mock()
        paginator.paginate.return_value = [{"DBInstances": [public_instance]}]
        self.mock_rds.get_paginator.return_value = paginator

        checker = RDSChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "HIGH")
        self.assertIn("prod-db-1", result.details["publicly_accessible"])

    def test_rds_encryption_disabled(self):
        """Detect unencrypted RDS instances."""
        unencrypted_instance = {
            "DBInstanceIdentifier": "dev-db",
            "Engine": "mysql",
            "PubliclyAccessible": False,
            "StorageEncrypted": False,
            "BackupRetentionPeriod": 7,
            "IAMDatabaseAuthenticationEnabled": True,
            "EnabledCloudwatchLogsExports": ["error", "general"],
        }

        paginator = Mock()
        paginator.paginate.return_value = [{"DBInstances": [unencrypted_instance]}]
        self.mock_rds.get_paginator.return_value = paginator

        checker = RDSChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "MEDIUM")
        self.assertIn("dev-db", result.details["unencrypted"])

    def test_rds_backup_disabled(self):
        """Detect RDS instances with backups disabled."""
        backup_disabled = {
            "DBInstanceIdentifier": "test-db",
            "Engine": "mariadb",
            "PubliclyAccessible": False,
            "StorageEncrypted": True,
            "BackupRetentionPeriod": 0,
            "IAMDatabaseAuthenticationEnabled": True,
            "EnabledCloudwatchLogsExports": ["error"],
        }

        paginator = Mock()
        paginator.paginate.return_value = [{"DBInstances": [backup_disabled]}]
        self.mock_rds.get_paginator.return_value = paginator

        checker = RDSChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "LOW")
        self.assertIn("test-db", result.details["backup_disabled"])

    def test_rds_iam_auth_disabled(self):
        """Detect RDS instances with IAM authentication disabled."""
        no_iam_auth = {
            "DBInstanceIdentifier": "secure-db",
            "Engine": "postgres",
            "PubliclyAccessible": False,
            "StorageEncrypted": True,
            "BackupRetentionPeriod": 7,
            "IAMDatabaseAuthenticationEnabled": False,
            "EnabledCloudwatchLogsExports": ["postgresql"],
        }

        paginator = Mock()
        paginator.paginate.return_value = [{"DBInstances": [no_iam_auth]}]
        self.mock_rds.get_paginator.return_value = paginator

        checker = RDSChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "MEDIUM")
        self.assertIn("secure-db", result.details["iam_auth_disabled"])

    def test_rds_cloudwatch_logs_disabled(self):
        """Detect RDS instances with CloudWatch logs disabled."""
        no_logs = {
            "DBInstanceIdentifier": "audit-db",
            "Engine": "postgres",
            "PubliclyAccessible": False,
            "StorageEncrypted": True,
            "BackupRetentionPeriod": 30,
            "IAMDatabaseAuthenticationEnabled": True,
            "EnabledCloudwatchLogsExports": [],
        }

        paginator = Mock()
        paginator.paginate.return_value = [{"DBInstances": [no_logs]}]
        self.mock_rds.get_paginator.return_value = paginator

        checker = RDSChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "LOW")
        self.assertIn("audit-db", result.details["cloudwatch_logs_disabled"])

    def test_rds_all_secure(self):
        """Return INFO when all RDS instances are secure."""
        secure_instance = {
            "DBInstanceIdentifier": "prod-secure",
            "Engine": "postgres",
            "PubliclyAccessible": False,
            "StorageEncrypted": True,
            "BackupRetentionPeriod": 30,
            "IAMDatabaseAuthenticationEnabled": True,
            "EnabledCloudwatchLogsExports": ["postgresql"],
        }

        paginator = Mock()
        paginator.paginate.return_value = [{"DBInstances": [secure_instance]}]
        self.mock_rds.get_paginator.return_value = paginator

        checker = RDSChecker(clients=self.mock_clients)
        result = checker.check()

        self.assertEqual(result.severity, "INFO")


if __name__ == "__main__":
    unittest.main()
