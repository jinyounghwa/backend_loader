"""S3 bucket security checker for AWS Guardian"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError
from guardian.aws_client_provider import AWSClientProvider
from guardian.checkers.base import BaseChecker, CheckResult
from guardian.config import Config

logger = logging.getLogger(__name__)


class S3Checker(BaseChecker):
    """Detect S3 security anomalies: public buckets, new buckets."""

    def __init__(
        self,
        clients: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        super().__init__(clients or {}, config or {}, account_id, credentials)
        self.s3_client = AWSClientProvider.get_client("s3")
        self.is_localstack = Config.is_localstack()

    def check(self) -> CheckResult:
        """Run all S3 security checks and return unified CheckResult."""
        self._log_check_start("S3")

        try:
            anomalies: List[str] = []
            details: Dict[str, Any] = {
                "is_anomaly": False,
                "public_buckets": [],
                "new_buckets": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            public_buckets = self._get_public_buckets()
            if public_buckets:
                details["public_buckets"] = public_buckets
                for bucket in public_buckets:
                    anomalies.append(
                        f"Public bucket detected: {bucket['bucket_name']} "
                        f"({', '.join(bucket['public_reasons'])})"
                    )

            new_buckets = self._get_new_buckets()
            if new_buckets:
                details["new_buckets"] = new_buckets
                anomalies.append(f"Detected {len(new_buckets)} new buckets in last 24 hours")

            details["is_anomaly"] = len(anomalies) > 0
            details["anomalies"] = anomalies

            if not anomalies:
                self._log_check_end("S3", "INFO")
                return CheckResult.info("S3 Check", "All buckets secure")

            severity = "CRITICAL" if public_buckets else "MEDIUM"
            self._log_check_end("S3", severity)
            return CheckResult(
                severity=severity,
                title="S3 Security Issues Detected",
                message=f"Found {len(anomalies)} S3 issues",
                details=details,
                suggested_action="Block public access on exposed buckets",
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self._log_error("S3", e)
            return CheckResult.error(
                "S3 Check Failed",
                f'AWS error ({error_code}): {e.response.get("Error", {}).get("Message", str(e))}',
            )
        except Exception as e:
            self._log_error("S3", e)
            return CheckResult.error("S3 Check Failed", f"Failed to check S3: {str(e)}")

    def _list_all_buckets(self) -> List[Dict[str, Any]]:
        """List all S3 buckets. list_buckets is not paginated by AWS,
        but we wrap it for consistency and future-proofing."""
        try:
            buckets_response = self.s3_client.list_buckets()
            return buckets_response.get("Buckets", [])
        except ClientError as e:
            logger.error("ClientError listing buckets: %s", e)
            return []
        except Exception as e:
            logger.error("Error listing buckets: %s", e)
            return []

    def _is_bucket_public_acl(self, bucket_name: str) -> bool:
        try:
            acl = self.s3_client.get_bucket_acl(Bucket=bucket_name)
            for grant in acl.get("Grants", []):
                grantee = grant.get("Grantee", {})
                if grantee.get("Type") == "Group":
                    uri = grantee.get("URI", "")
                    if "AuthenticatedUsers" in uri or "AllUsers" in uri:
                        return True
            return False
        except ClientError as e:
            logger.error("ClientError checking ACL for %s: %s", bucket_name, e)
            return False
        except Exception as e:
            logger.error("Error checking ACL for %s: %s", bucket_name, e)
            return False

    def _is_bucket_public_policy(self, bucket_name: str) -> Tuple[bool, Dict]:
        try:
            policy_response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
            policy_str = policy_response["Policy"]
            policy = json.loads(policy_str) if isinstance(policy_str, str) else policy_str

            for statement in policy.get("Statement", []):
                principal = statement.get("Principal")
                if principal == "*" or (
                    isinstance(principal, dict) and principal.get("AWS") == "*"
                ):
                    if statement.get("Effect", "").upper() == "ALLOW":
                        return True, statement
            return False, {}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if "NoSuchBucketPolicy" in str(error_code):
                return False, {}
            logger.error("ClientError checking policy for %s: %s", bucket_name, e)
            return False, {}
        except Exception as e:
            logger.error("Error checking policy for %s: %s", bucket_name, e)
            return False, {}

    def _is_bucket_public_block_disabled(self, bucket_name: str) -> bool:
        try:
            response = self.s3_client.get_public_access_block(Bucket=bucket_name)
            config = response["PublicAccessBlockConfiguration"]
            return not (
                config.get("BlockPublicAcls", False)
                and config.get("BlockPublicPolicy", False)
                and config.get("IgnorePublicAcls", False)
                and config.get("RestrictPublicBuckets", False)
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if "NoSuchPublicAccessBlockConfiguration" in str(error_code):
                # No block configured — treat as potentially public
                return True
            logger.error("ClientError checking public access block for %s: %s", bucket_name, e)
            return False
        except Exception as e:
            logger.error("Error checking public access block for %s: %s", bucket_name, e)
            return False

    def _get_public_buckets(self) -> List[Dict]:
        public_buckets = []
        buckets = self._list_all_buckets()

        for bucket in buckets:
            bucket_name = bucket["Name"]
            is_public = False
            public_reasons: List[str] = []

            if self._is_bucket_public_acl(bucket_name):
                is_public = True
                public_reasons.append("Public ACL")

            has_public_policy, _ = self._is_bucket_public_policy(bucket_name)
            if has_public_policy:
                is_public = True
                public_reasons.append("Public Bucket Policy")

            if self._is_bucket_public_block_disabled(bucket_name):
                is_public = True
                public_reasons.append("Public Access Block Disabled")

            if is_public:
                public_buckets.append(
                    {
                        "bucket_name": bucket_name,
                        "creation_date": bucket["CreationDate"].isoformat(),
                        "public_reasons": public_reasons,
                    }
                )
        return public_buckets

    def _get_new_buckets(self, hours: int = 24) -> List[Dict]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        new_buckets = []
        buckets = self._list_all_buckets()

        for bucket in buckets:
            creation_date = bucket["CreationDate"]
            if hasattr(creation_date, "replace") and creation_date.tzinfo is not None:
                creation_date = creation_date.replace(tzinfo=None)
            if creation_date > cutoff_time.replace(tzinfo=None):
                new_buckets.append(
                    {
                        "bucket_name": bucket["Name"],
                        "creation_date": creation_date.isoformat(),
                    }
                )
        return new_buckets
