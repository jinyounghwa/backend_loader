"""EC2 security checker for AWS Guardian."""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError
from guardian.aws_client_provider import AWSClientProvider
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

logger = logging.getLogger(__name__)


class EC2Checker(BaseChecker):
    """Detect EC2 security anomalies: unauthorized regions, exposed security groups, new instances."""

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        authorized_regions: Optional[List[str]] = None,
    ):
        effective_config = config or {}
        if authorized_regions:
            effective_config.setdefault("authorized_regions", authorized_regions)
        super().__init__(clients or {}, effective_config, account_id, credentials)

        self.ec2_client = self._get_or_create_client("ec2")

        self.authorized_regions = self.config.get("authorized_regions", [])
        self.is_localstack = Config.is_localstack()
        self._client_cache: Dict[str, Any] = {}

    def _get_regional_client(self, region: str) -> Any:
        """Get or create a cached EC2 client for the given region.

        Uses the checker's cross-account credentials when present, so
        per-region scans inspect the member account rather than the hub.
        """
        if region not in self._client_cache:
            if self.credentials and self.account_id:
                self._client_cache[region] = AWSClientProvider.get_client_for_account(
                    "ec2", self.account_id, self.credentials, region=region
                )
            else:
                self._client_cache[region] = AWSClientProvider.get_client("ec2", region=region)
        return self._client_cache[region]

    # ------------------------------------------------------------------
    # Main check entry (sync-first)
    # ------------------------------------------------------------------

    def check(self) -> CheckResult:
        """Run all EC2 security checks and return unified CheckResult."""
        self._log_check_start("EC2")
        try:
            all_instances = self._get_all_instances()
            return self._analyze_instances(all_instances)
        except ClientError as e:
            return self._handle_client_error("EC2", e)
        except Exception as e:
            return self._handle_generic_error("EC2", e)

    # ------------------------------------------------------------------
    # Instance fetching
    # ------------------------------------------------------------------

    def _get_all_instances(self) -> Dict[str, List[Dict]]:
        """Fetch running instances across all regions using a cached client pool."""
        instances_by_region: Dict[str, List[Dict]] = {}
        try:
            if self.is_localstack:
                regions = ["us-east-1"]
            else:
                ec2_global = AWSClientProvider.get_client("ec2")
                regions_response = ec2_global.describe_regions()
                regions = [r["RegionName"] for r in regions_response["Regions"]]

            def _fetch_instances_for_region(region: str) -> Optional[tuple]:
                regional_ec2 = self._get_regional_client(region)
                try:
                    response = regional_ec2.describe_instances(
                        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
                    )
                    instances = []
                    for reservation in response["Reservations"]:
                        instances.extend(reservation["Instances"])
                    if instances:
                        return region, instances
                except ClientError as e:
                    logger.error("ClientError in region %s: %s", region, e)
                except Exception as e:
                    logger.error("Error checking region %s: %s", region, e)
                return None

            max_workers = min(len(regions), 10)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = executor.map(_fetch_instances_for_region, regions)

            for res in results:
                if res:
                    region, instances = res
                    instances_by_region[region] = instances

            return instances_by_region
        except ClientError as e:
            logger.error("ClientError getting regions: %s", e)
            return {}
        except Exception as e:
            logger.error("Error getting all instances: %s", e)
            return {}

    # ------------------------------------------------------------------
    # Instance analysis
    # ------------------------------------------------------------------

    def _analyze_instances(self, all_instances: Dict[str, List[Dict]]) -> CheckResult:
        """Analyze fetched instances for security issues."""
        anomalies: List[str] = []
        details: Dict[str, Any] = {
            "is_anomaly": False,
            "unauthorized_region_instances": {},
            "exposed_instances": [],
            "new_instances": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.authorized_regions:
            unauthorized = {
                region: instances
                for region, instances in all_instances.items()
                if region not in self.authorized_regions
            }
            if unauthorized:
                details["unauthorized_region_instances"] = unauthorized
                anomalies.append(f"Instances in unauthorized regions: {list(unauthorized.keys())}")

        for region, instances in all_instances.items():
            for instance in instances:
                exposed_rules = self._check_security_group_exposure(instance, region)
                if exposed_rules:
                    details["exposed_instances"].append(
                        {
                            "instance_id": instance["InstanceId"],
                            "region": region,
                            "exposed_rules": exposed_rules,
                        }
                    )
                    anomalies.append(f"Instance {instance['InstanceId']} has 0.0.0.0/0 exposure")

        new_instances = self._get_new_instances(all_instances)
        if new_instances:
            details["new_instances"] = new_instances
            anomalies.append(f"Detected {len(new_instances)} new instances")

        details["is_anomaly"] = len(anomalies) > 0
        details["anomalies"] = anomalies

        if not anomalies:
            self._log_check_end("EC2", "INFO")
            return CheckResult.info("EC2 Check", "All instances secure")

        severity = "CRITICAL" if details["exposed_instances"] else "HIGH"
        self._log_check_end("EC2", severity)
        return CheckResult(
            severity=severity,
            title="EC2 Security Issues Detected",
            message=f"Found {len(anomalies)} EC2 issues",
            details=details,
            suggested_action="Review and stop unauthorized/exposed instances",
        )

    # ------------------------------------------------------------------
    # Security group checks
    # ------------------------------------------------------------------

    def _check_security_group_exposure(self, instance: Dict, region: str) -> List[Dict]:
        """Check if the instance's security groups expose 0.0.0.0/0."""
        exposed_rules = []
        regional_ec2 = self._get_regional_client(region)

        for sg in instance.get("SecurityGroups", []):
            sg_id = sg["GroupId"]
            try:
                sg_response = regional_ec2.describe_security_groups(GroupIds=[sg_id])

                for sg_detail in sg_response["SecurityGroups"]:
                    for rule in sg_detail.get("IpPermissions", []):
                        for ip_range in rule.get("IpRanges", []):
                            if ip_range.get("CidrIp") == "0.0.0.0/0":
                                exposed_rules.append(
                                    {
                                        "group_id": sg_id,
                                        "group_name": sg_detail["GroupName"],
                                        "protocol": rule.get("IpProtocol", "N/A"),
                                        "from_port": rule.get("FromPort"),
                                        "to_port": rule.get("ToPort"),
                                        "cidr": "0.0.0.0/0",
                                    }
                                )
            except ClientError as e:
                logger.error("ClientError checking security group %s: %s", sg_id, e)
            except Exception as e:
                logger.error("Error checking security group %s: %s", sg_id, e)
        return exposed_rules

    def _get_new_instances(self, all_instances: Dict[str, List[Dict]]) -> List[Dict]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        new_instances = []

        for region, instances in all_instances.items():
            for instance in instances:
                launch_time = instance["LaunchTime"]
                if hasattr(launch_time, "tzinfo") and launch_time.tzinfo is None:
                    launch_time = launch_time.replace(tzinfo=timezone.utc)
                if launch_time > cutoff_time:
                    new_instances.append(
                        {
                            "instance_id": instance["InstanceId"],
                            "instance_type": instance["InstanceType"],
                            "region": region,
                            "launch_time": launch_time.isoformat(),
                            "tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])},
                            "owner": instance.get("OwnerAlias", "Unknown"),
                        }
                    )
        return new_instances
