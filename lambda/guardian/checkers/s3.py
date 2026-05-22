"""S3 bucket security checker for AWS Guardian."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
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
        self.is_localstack = Config.is_localstack()

        self.s3_client = self.clients.get("s3")
        if self.s3_client is None:
            self.s3_client = boto3.client("s3", **Config.get_boto3_kwargs())

    # ------------------------------------------------------------------
    # Main check entry (sync-first)
    # ------------------------------------------------------------------

    def check(self) -> CheckResult:
        """Check for S3 bucket security issues.

        Detects:
        - Public buckets (via ACL, bucket policy, or disabled public access block)
        - New buckets created in last 24 hours
        """
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
            return self._handle_client_error("S3", e)
        except Exception as e:
            return self._handle_generic_error("S3", e)

    # ------------------------------------------------------------------
    # Bucket enumeration
    # ------------------------------------------------------------------

    def _list_all_buckets(self) -> List[Dict[str, Any]]:
        """List all S3 buckets."""
        try:
            response = self.s3_client.list_buckets()
            return response.get("Buckets", [])
        except ClientError as e:
            logger.error("ClientError listing buckets: %s", e)
            return []
        except Exception as e:
            logger.error("Error listing buckets: %s", e)
            return []

    # ------------------------------------------------------------------
    # Public bucket detection
    # ------------------------------------------------------------------

    def _is_bucket_public_acl(self, bucket_name: str) -> bool:
        """Check if bucket is public via ACL."""
        try:
            acl = self.s3_client.get_bucket_acl(Bucket=bucket_name)
            for grant in acl.get("Grants", []):
                grantee = grant.get("Grantee", {})
                if grantee.get("Type") == "Group":
                    uri = grantee.get("URI", "")
                    if "AuthenticatedUsers" in uri or "AllUsers" in uri:
                        return True
            return False
        except ClientError:
            return False
        except Exception as e:
            logger.error("Error checking ACL for %s: %s", bucket_name, e)
            return False

    def _is_bucket_public_policy(self, bucket_name: str) -> Tuple[bool, Dict]:
        """Check if bucket is public via policy."""
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
        """Check if public access block is disabled."""
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
                return True
            logger.error("ClientError checking public access block for %s: %s", bucket_name, e)
            return False
        except Exception as e:
            logger.error("Error checking public access block for %s: %s", bucket_name, e)
            return False

    def _get_public_buckets(self) -> List[Dict]:
        """Get list of public buckets with reasons."""
        public_buckets = []
        buckets = self._list_all_buckets()

        def _check_bucket(bucket: Dict[str, Any]) -> Optional[Dict]:
            bucket_name = bucket["Name"]
            public_reasons: List[str] = []

            if self._is_bucket_public_acl(bucket_name):
                public_reasons.append("Public ACL")

            has_public_policy, _ = self._is_bucket_public_policy(bucket_name)
            if has_public_policy:
                public_reasons.append("Public Bucket Policy")

            if self._is_bucket_public_block_disabled(bucket_name):
                public_reasons.append("Public Access Block Disabled")

            if public_reasons:
                return {
                    "bucket_name": bucket_name,
                    "creation_date": bucket["CreationDate"].isoformat(),
                    "public_reasons": public_reasons,
                }
            return None

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(len(buckets), 10) if buckets else 1) as executor:
            results = executor.map(_check_bucket, buckets)

        for res in results:
            if res:
                public_buckets.append(res)

        return public_buckets

    def _get_new_buckets(self, hours: int = 24) -> List[Dict]:
        """Get new buckets created in last N hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        new_buckets = []
        buckets = self._list_all_buckets()

        for bucket in buckets:
            creation_date = bucket["CreationDate"]
            if hasattr(creation_date, "tzinfo") and creation_date.tzinfo is None:
                creation_date = creation_date.replace(tzinfo=timezone.utc)
            if creation_date > cutoff_time:
                new_buckets.append(
                    {
                        "bucket_name": bucket["Name"],
                        "creation_date": creation_date.isoformat(),
                    }
                )
        return new_buckets
