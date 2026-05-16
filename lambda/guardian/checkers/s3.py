"""S3 bucket security checker for AWS Guardian"""

import asyncio
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
        # Get from clients dict (tests) or create new (production)
        self.s3_client = self.clients.get("s3")
        if self.s3_client is None:
            kwargs = Config.get_boto3_kwargs()
            self.s3_client = boto3.client("s3", **kwargs)

    async def check_async(self) -> CheckResult:
        """Run all S3 security checks with async I/O."""
        self._log_check_start("S3")

        try:
            anomalies: List[str] = []
            details: Dict[str, Any] = {
                "is_anomaly": False,
                "public_buckets": [],
                "new_buckets": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            public_buckets = await self._get_public_buckets_async()
            if public_buckets:
                details["public_buckets"] = public_buckets
                for bucket in public_buckets:
                    anomalies.append(
                        f"Public bucket detected: {bucket['bucket_name']} "
                        f"({', '.join(bucket['public_reasons'])})"
                    )

            new_buckets = await self._get_new_buckets_async()
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

    async def _list_all_buckets_async(self) -> List[Dict[str, Any]]:
        """List all S3 buckets using async I/O."""
        try:
            async with await AWSClientProvider.get_async_client("s3") as s3_client:
                buckets_response = await s3_client.list_buckets()
                return buckets_response.get("Buckets", [])
        except ClientError as e:
            logger.error("ClientError listing buckets: %s", e)
            return []
        except Exception as e:
            logger.error("Error listing buckets: %s", e)
            return []

    async def _is_bucket_public_acl_async(self, bucket_name: str) -> bool:
        """Check if bucket is public via ACL using async I/O."""
        try:
            async with await AWSClientProvider.get_async_client("s3") as s3_client:
                acl = await s3_client.get_bucket_acl(Bucket=bucket_name)
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

    async def _is_bucket_public_policy_async(self, bucket_name: str) -> Tuple[bool, Dict]:
        """Check if bucket is public via policy using async I/O."""
        try:
            async with await AWSClientProvider.get_async_client("s3") as s3_client:
                policy_response = await s3_client.get_bucket_policy(Bucket=bucket_name)
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

    async def _is_bucket_public_block_disabled_async(self, bucket_name: str) -> bool:
        """Check if public access block is disabled using async I/O."""
        try:
            async with await AWSClientProvider.get_async_client("s3") as s3_client:
                response = await s3_client.get_public_access_block(Bucket=bucket_name)
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

    async def _get_public_buckets_async(self) -> List[Dict]:
        """Get public buckets with parallel async checks."""
        public_buckets = []
        buckets = await self._list_all_buckets_async()

        async def check_bucket_public(bucket: Dict) -> Optional[Dict]:
            bucket_name = bucket["Name"]
            public_reasons: List[str] = []

            is_acl_public = await self._is_bucket_public_acl_async(bucket_name)
            if is_acl_public:
                public_reasons.append("Public ACL")

            has_public_policy, _ = await self._is_bucket_public_policy_async(bucket_name)
            if has_public_policy:
                public_reasons.append("Public Bucket Policy")

            block_disabled = await self._is_bucket_public_block_disabled_async(bucket_name)
            if block_disabled:
                public_reasons.append("Public Access Block Disabled")

            if public_reasons:
                return {
                    "bucket_name": bucket_name,
                    "creation_date": bucket["CreationDate"].isoformat(),
                    "public_reasons": public_reasons,
                }
            return None

        if buckets:
            results = await asyncio.gather(*[check_bucket_public(b) for b in buckets])
            public_buckets = [r for r in results if r is not None]

        return public_buckets

    async def _get_new_buckets_async(self, hours: int = 24) -> List[Dict]:
        """Get new buckets created in last N hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        new_buckets = []
        buckets = await self._list_all_buckets_async()

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

    def _is_bucket_public_acl(self, bucket_name: str) -> bool:
        """Check if bucket is public via ACL (sync version for tests)."""
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
