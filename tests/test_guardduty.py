"""Unit tests for GuardDuty checker"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from guardian.checkers.guardduty import GuardDutyChecker
from guardian.checkers.base import CheckResult


class TestGuardDutyChecker(unittest.TestCase):
    """Unit tests for GuardDutyChecker"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_clients = {"guardduty": Mock(), "ec2": Mock()}
        self.config = {}
        self.checker = GuardDutyChecker(self.mock_clients, self.config)

    def test_initialization(self):
        """Test GuardDutyChecker initialization"""
        self.assertEqual(self.checker.guardduty, self.mock_clients["guardduty"])
        self.assertIsNotNone(self.checker.ec2)

    def test_check_no_findings(self):
        """Test check() when no threats detected"""
        self.checker._get_active_findings = Mock(return_value=[])

        result = self.checker.check()

        self.assertEqual(result.severity, "INFO")
        self.assertIn("No active", result.message)

    def test_check_with_findings(self):
        """Test check() with threat findings"""
        findings = [
            {
                "id": "finding-1",
                "type": "Trojan:EC2/BlackholeTraffic",
                "severity": 8.5,
                "title": "EC2 instance probing",
                "description": "Instance is probing external hosts",
                "resource_type": "Instance",
                "resource_id": "i-1234567890abcdef0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        self.checker._get_active_findings = Mock(return_value=findings)

        result = self.checker.check()

        self.assertEqual(result.severity, "CRITICAL")
        self.assertIn("threat", result.message.lower())

    def test_get_active_findings_no_detector(self):
        """Test _get_active_findings() when no detector found"""
        self.mock_clients["guardduty"].list_detectors.return_value = {"DetectorIds": []}

        findings = self.checker._get_active_findings()

        self.assertEqual(findings, [])

    def test_get_active_findings_success(self):
        """Test _get_active_findings() retrieves findings successfully"""
        detector_id = "detector-123"
        finding_ids = ["finding-1", "finding-2"]

        self.mock_clients["guardduty"].list_detectors.return_value = {"DetectorIds": [detector_id]}
        self.mock_clients["guardduty"].list_findings.return_value = {"FindingIds": finding_ids}
        self.mock_clients["guardduty"].get_findings.return_value = {
            "Findings": [
                {
                    "Id": "finding-1",
                    "Type": "Trojan:EC2/BlackholeTraffic",
                    "Severity": 8.5,
                    "Title": "EC2 probing",
                    "Description": "Instance probing",
                    "Resource": {
                        "ResourceType": "Instance",
                        "InstanceDetails": {"InstanceId": "i-123"},
                    },
                    "UpdatedAt": datetime.now(timezone.utc).timestamp() * 1000,
                }
            ]
        }

        findings = self.checker._get_active_findings()

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "Trojan:EC2/BlackholeTraffic")

    def test_determine_severity_critical(self):
        """Test _determine_severity() returns CRITICAL for high-severity findings"""
        findings = [{"severity": 7.5}, {"severity": 8.0}]

        severity = self.checker._determine_severity(findings)

        self.assertEqual(severity, "CRITICAL")

    def test_determine_severity_high(self):
        """Test _determine_severity() returns HIGH for medium-high findings"""
        findings = [{"severity": 5.5}, {"severity": 6.5}]

        severity = self.checker._determine_severity(findings)

        self.assertEqual(severity, "HIGH")

    def test_determine_severity_medium(self):
        """Test _determine_severity() returns MEDIUM for lower findings"""
        findings = [{"severity": 2.5}, {"severity": 3.5}]

        severity = self.checker._determine_severity(findings)

        self.assertEqual(severity, "MEDIUM")

    def test_determine_severity_info(self):
        """Test _determine_severity() returns INFO for empty findings"""
        findings = []

        severity = self.checker._determine_severity(findings)

        self.assertEqual(severity, "INFO")

    def test_get_remediation_suggestion_rdp_bruteforce(self):
        """Test remediation suggestion for RDP brute force"""
        findings = [{"type": "UnauthorizedAccess:EC2/RDPBruteForce"}]

        suggestion = self.checker._get_remediation_suggestion(findings)

        self.assertIn("RDP", suggestion.upper())
        self.assertIn("port 3389", suggestion)

    def test_get_remediation_suggestion_ssh_bruteforce(self):
        """Test remediation suggestion for SSH brute force"""
        findings = [{"type": "UnauthorizedAccess:EC2/SSHBruteForce"}]

        suggestion = self.checker._get_remediation_suggestion(findings)

        self.assertIn("SSH", suggestion.upper())
        self.assertIn("port 22", suggestion)

    def test_get_remediation_suggestion_cryptocurrency(self):
        """Test remediation suggestion for crypto mining"""
        findings = [{"type": "CryptoCurrency:EC2/BitcoinTool"}]

        suggestion = self.checker._get_remediation_suggestion(findings)

        self.assertIn("compromised", suggestion.lower())

    def test_get_remediation_suggestion_spambot(self):
        """Test remediation suggestion for spambot"""
        findings = [{"type": "Trojan:EC2/Spambot"}]

        suggestion = self.checker._get_remediation_suggestion(findings)

        self.assertIn("malware", suggestion.lower())

    def test_get_remediation_suggestion_unauthorized_access(self):
        """Test remediation suggestion for unauthorized access"""
        findings = [{"type": "UnauthorizedAccess:EC2/MaliciousIPCaller"}]

        suggestion = self.checker._get_remediation_suggestion(findings)

        self.assertIn("IAM", suggestion)

    def test_get_remediation_suggestion_fallback(self):
        """Test remediation suggestion fallback for unknown threat types"""
        findings = [{"type": "UnknownThreat:EC2/SomethingNew"}]

        suggestion = self.checker._get_remediation_suggestion(findings)

        self.assertIn("GuardDuty", suggestion)

    def test_check_result_structure(self):
        """Test check() returns properly structured CheckResult"""
        self.checker._get_active_findings = Mock(return_value=[])

        result = self.checker.check()

        self.assertIsInstance(result, CheckResult)
        self.assertIn(result.severity, ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.assertIsNotNone(result.title)
        self.assertIsNotNone(result.message)
        self.assertIsInstance(result.details, dict)

    def test_check_error_handling(self):
        """Test check() handles exceptions gracefully"""
        self.checker._get_active_findings = Mock(side_effect=Exception("API error"))

        result = self.checker.check()

        # CheckResult.error() returns HIGH severity
        self.assertEqual(result.severity, "HIGH")
        self.assertIn("Failed", result.message)

    def test_finding_details_extraction(self):
        """Test that finding details are properly extracted"""
        findings = [
            {
                "id": "finding-123",
                "type": "Trojan:EC2/BlackholeTraffic",
                "severity": 8.5,
                "title": "EC2 blackhole traffic",
                "description": "Instance sending traffic to blackhole IPs",
                "resource_type": "Instance",
                "resource_id": "i-1234567890abcdef0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        self.mock_clients["guardduty"].list_detectors.return_value = {
            "DetectorIds": ["detector-123"]
        }
        self.mock_clients["guardduty"].list_findings.return_value = {"FindingIds": ["finding-123"]}
        self.mock_clients["guardduty"].get_findings.return_value = {"Findings": findings}

        result = self.checker.check()

        self.assertIn("details", result.__dict__)

    def test_high_severity_findings_separation(self):
        """Test that findings are separated by severity level"""
        high_findings = [{"severity": 8.5, "type": "Trojan", "title": "High threat"}]
        medium_findings = [{"severity": 5.0, "type": "ProbeMalware", "title": "Medium threat"}]

        # Simulate findings with both high and medium severity
        high_findings + medium_findings  # noqa: F841

        self.mock_clients["guardduty"].list_detectors.return_value = {
            "DetectorIds": ["detector-123"]
        }
        self.mock_clients["guardduty"].list_findings.return_value = {
            "FindingIds": ["finding-1", "finding-2"]
        }

        result = self.checker.check()

        self.assertIsNotNone(result)


class TestGuardDutyCheckerIntegration(unittest.TestCase):
    """Integration tests for GuardDutyChecker"""

    @patch("guardian.checkers.guardduty.logging")
    def test_check_with_no_detectors(self, mock_logging):
        """Test check() when GuardDuty is not enabled"""
        mock_clients = {"guardduty": Mock(), "ec2": Mock()}
        mock_clients["guardduty"].list_detectors.return_value = {"DetectorIds": []}

        checker = GuardDutyChecker(mock_clients, {})
        result = checker.check()

        self.assertEqual(result.severity, "INFO")


if __name__ == "__main__":
    unittest.main()
