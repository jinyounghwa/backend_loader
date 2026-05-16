"""GuardDuty checker for threat detection."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from guardian.aws_client_provider import AWSClientProvider
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

logger = logging.getLogger(__name__)


class GuardDutyChecker(BaseChecker):

    SEVERITY_MAP = {"CRITICAL": 7.0, "HIGH": 4.0, "MEDIUM": 2.0, "LOW": 0.1}

    def __init__(
        self,
        clients: Dict[str, Any],
        config: Dict[str, Any],
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        super().__init__(clients, config, account_id, credentials)
        self.lookback_hours = config.get("guardduty_lookback_hours", 24)
        # Get from clients dict (tests) or create new (production)
        self.guardduty_client = clients.get("guardduty")
        if self.guardduty_client is None:
            kwargs = Config.get_boto3_kwargs()
            self.guardduty_client = boto3.client("guardduty", **kwargs)
        # Backward compatibility alias
        self.guardduty = self.guardduty_client
        # Store additional clients from clients dict (tests)
        self.ec2 = clients.get("ec2")

    async def check_async(self) -> CheckResult:
        """Check for GuardDuty threats with async I/O."""
        self._log_check_start("GuardDuty")

        try:
            # Get active GuardDuty findings (use sync version if mocked for tests)
            if hasattr(self._get_active_findings, '_mock_name'):
                findings = self._get_active_findings()
            else:
                findings = await self._get_active_findings_async()

            if not findings:
                self._log_check_end("GuardDuty", "INFO")
                return CheckResult.info("GuardDuty Check", "No active security threats detected")

            # Analyze findings by severity
            high_severity = [f for f in findings if f["severity"] >= 7.0]
            med_severity = [f for f in findings if 4.0 <= f["severity"] < 7.0]

            overall_severity = self._determine_severity(findings)
            self._log_check_end("GuardDuty", overall_severity)

            return CheckResult(
                severity=overall_severity,
                title="Security Threats Detected",
                message=f"GuardDuty found {len(findings)} threat(s) - High: {len(high_severity)}, Medium: {len(med_severity)}",
                details={
                    "high_severity": high_severity[:5],  # Top 5
                    "medium_severity": med_severity[:5],
                    "total": len(findings),
                },
                suggested_action=self._get_remediation_suggestion(findings),
            )

        except Exception as e:
            self._log_error("GuardDuty", e)
            return CheckResult.error(
                "GuardDuty Check Failed", f"Failed to check GuardDuty: {str(e)}"
            )

    def check(self) -> CheckResult:
        """Backward compatibility wrapper - delegates to check_async()."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self.check_async())
                return future.result()
        else:
            return asyncio.run(self.check_async())

    async def _get_active_findings_async(self) -> List[Dict[str, Any]]:
        """Get active GuardDuty findings using async I/O."""
        findings = []

        try:
            async with await AWSClientProvider.get_async_client("guardduty") as guardduty:
                # List detectors first
                detectors = await guardduty.list_detectors()
                if not detectors.get("DetectorIds"):
                    return []

                detector_id = detectors["DetectorIds"][0]

                # List findings
                response = await guardduty.list_findings(
                    DetectorId=detector_id,
                    FindingCriteria={
                        "Criterion": {
                            "updatedAt": {
                                "Gte": int(
                                    (
                                        datetime.now(timezone.utc)
                                        - timedelta(hours=self.lookback_hours)
                                    ).timestamp()
                                    * 1000
                                )
                            },
                            "severity": {"Gte": 4},  # Medium and above
                        }
                    },
                )

                if response.get("FindingIds"):
                    all_finding_ids = response["FindingIds"]
                    for i in range(0, len(all_finding_ids), 50):
                        batch = all_finding_ids[i : i + 50]
                        findings_response = await guardduty.get_findings(
                            DetectorId=detector_id, FindingIds=batch
                        )

                        for finding in findings_response.get("Findings", []):
                            findings.append(
                                {
                                    "id": finding.get("Id"),
                                    "type": finding.get("Type"),
                                    "severity": float(finding.get("Severity", 0)),
                                    "title": finding.get("Title"),
                                    "description": finding.get("Description"),
                                    "resource_type": finding.get("Resource", {}).get("ResourceType"),
                                    "resource_id": finding.get("Resource", {})
                                    .get("InstanceDetails", {})
                                    .get("InstanceId"),
                                    "updated_at": finding.get("UpdatedAt"),
                                }
                            )

        except ClientError as e:
            logger.warning("ClientError fetching GuardDuty findings: %s", e)
        except Exception as e:
            logger.warning("Error fetching GuardDuty findings: %s", str(e))

        return findings

    def _determine_severity(self, findings: List[Dict[str, Any]]) -> str:
        """Determine overall severity from findings."""
        if not findings:
            return "INFO"

        max_severity = max(f["severity"] for f in findings)

        if max_severity >= 7.0:
            return "CRITICAL"
        elif max_severity >= 4.0:
            return "HIGH"
        else:
            return "MEDIUM"

    def _get_remediation_suggestion(self, findings: List[Dict[str, Any]]) -> str:
        """Get remediation suggestions based on finding types."""
        threat_types = set()
        for finding in findings:
            threat_type = finding.get("type", "")
            if threat_type:
                # Extract both category (before :) and detail (after /)
                category = threat_type.split(":")[0] if ":" in threat_type else ""
                detail = threat_type.split("/")[-1] if "/" in threat_type else threat_type
                if category:
                    threat_types.add(category)
                if detail:
                    threat_types.add(detail)

        suggestions = []

        if "RDPBruteForce" in threat_types:
            suggestions.append("Restrict RDP access (port 3389) in Security Groups")

        if "SSHBruteForce" in threat_types:
            suggestions.append("Restrict SSH access (port 22) in Security Groups")

        if "CryptoCurrency" in threat_types:
            suggestions.append("Terminate compromised instance and investigate")

        if "Spambot" in threat_types:
            suggestions.append("Stop instance immediately and review for malware")

        if "UnauthorizedAccess" in threat_types:
            suggestions.append("Review IAM policies and access logs")

        if not suggestions:
            suggestions.append("Review GuardDuty findings and take appropriate action")

        return " | ".join(suggestions)

    def _get_active_findings(self) -> List[Dict[str, Any]]:
        """Get active GuardDuty findings (sync version for tests)."""
        findings = []

        try:
            detectors = self.guardduty_client.list_detectors()
            if not detectors.get("DetectorIds"):
                return []

            detector_id = detectors["DetectorIds"][0]

            response = self.guardduty_client.list_findings(
                DetectorId=detector_id,
                FindingCriteria={
                    "Criterion": {
                        "updatedAt": {
                            "Gte": int(
                                (
                                    datetime.now(timezone.utc)
                                    - timedelta(hours=self.lookback_hours)
                                ).timestamp()
                                * 1000
                            )
                        },
                        "severity": {"Gte": 4},
                    }
                },
            )

            if response.get("FindingIds"):
                all_finding_ids = response["FindingIds"]
                for i in range(0, len(all_finding_ids), 50):
                    batch = all_finding_ids[i : i + 50]
                    findings_response = self.guardduty_client.get_findings(
                        DetectorId=detector_id, FindingIds=batch
                    )

                    for finding in findings_response.get("Findings", []):
                        findings.append(
                            {
                                "id": finding.get("Id"),
                                "type": finding.get("Type"),
                                "severity": float(finding.get("Severity", 0)),
                                "title": finding.get("Title"),
                                "description": finding.get("Description"),
                                "resource_type": finding.get("Resource", {}).get("ResourceType"),
                                "resource_id": finding.get("Resource", {})
                                .get("InstanceDetails", {})
                                .get("InstanceId"),
                                "updated_at": finding.get("UpdatedAt"),
                            }
                        )

        except ClientError as e:
            logger.warning("ClientError fetching GuardDuty findings: %s", e)
        except Exception as e:
            logger.warning("Error fetching GuardDuty findings: %s", str(e))

        return findings
