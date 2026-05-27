"""S3 Archive Manager for long-term storage of events and decisions."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from guardian.aws_client_provider import AWSClientProvider
from guardian.config import Config

logger = logging.getLogger(__name__)


class S3ArchiveManager:
    """Manages archival of old data to S3 for long-term storage."""

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or f"{Config.get_project_name()}-archive"
        self.s3_client = AWSClientProvider.get_client("s3")

        try:
            # Verify bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Initialized S3ArchiveManager with bucket {self.bucket_name}")
        except Exception as e:
            logger.warning(f"Could not verify bucket {self.bucket_name}: {e}")

    def archive_events(self, events: List[Dict[str, Any]], partition_date: Optional[str] = None) -> bool:
        """Archive events to S3 with date-based partitioning."""
        try:
            if not events:
                logger.warning("No events to archive")
                return False

            if partition_date is None:
                partition_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y/%m/%d")

            archive_key = f"events/{partition_date}/events-{datetime.now(timezone.utc).isoformat()}.json.gz"

            # Compress and upload
            import gzip

            event_records = []
            for event in events:
                event_copy = dict(event)
                # Ensure raw_event is string
                if isinstance(event_copy.get("raw_event"), dict):
                    event_copy["raw_event"] = json.dumps(event_copy["raw_event"])
                event_records.append(event_copy)

            data = json.dumps(event_records).encode("utf-8")
            compressed_data = gzip.compress(data)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=archive_key,
                Body=compressed_data,
                ContentType="application/gzip",
                ServerSideEncryption="AES256",
                Metadata={"archive-type": "events", "event-count": str(len(events))},
            )

            logger.info(f"Archived {len(events)} events to s3://{self.bucket_name}/{archive_key}")
            return True

        except Exception as e:
            logger.error(f"Error archiving events to S3: {e}")
            return False

    def archive_decisions(self, decisions: List[Dict[str, Any]], partition_date: Optional[str] = None) -> bool:
        """Archive decisions to S3 with date-based partitioning."""
        try:
            if not decisions:
                logger.warning("No decisions to archive")
                return False

            if partition_date is None:
                partition_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y/%m/%d")

            archive_key = f"decisions/{partition_date}/decisions-{datetime.now(timezone.utc).isoformat()}.json.gz"

            import gzip

            decision_records = []
            for decision in decisions:
                decision_copy = dict(decision)
                # Ensure details is string
                if isinstance(decision_copy.get("details"), dict):
                    decision_copy["details"] = json.dumps(decision_copy["details"])
                # Convert Decimal to float
                for key in ["confidence", "z_score"]:
                    if key in decision_copy:
                        from decimal import Decimal

                        if isinstance(decision_copy[key], Decimal):
                            decision_copy[key] = float(decision_copy[key])
                decision_records.append(decision_copy)

            data = json.dumps(decision_records, default=str).encode("utf-8")
            compressed_data = gzip.compress(data)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=archive_key,
                Body=compressed_data,
                ContentType="application/gzip",
                ServerSideEncryption="AES256",
                Metadata={"archive-type": "decisions", "decision-count": str(len(decisions))},
            )

            logger.info(f"Archived {len(decisions)} decisions to s3://{self.bucket_name}/{archive_key}")
            return True

        except Exception as e:
            logger.error(f"Error archiving decisions to S3: {e}")
            return False

    def archive_feedback(self, feedbacks: List[Dict[str, Any]], partition_date: Optional[str] = None) -> bool:
        """Archive feedback to S3 with date-based partitioning."""
        try:
            if not feedbacks:
                logger.warning("No feedback to archive")
                return False

            if partition_date is None:
                partition_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y/%m/%d")

            archive_key = f"feedback/{partition_date}/feedback-{datetime.now(timezone.utc).isoformat()}.json.gz"

            import gzip

            feedback_records = []
            for feedback in feedbacks:
                feedback_copy = dict(feedback)
                # Convert Decimal to float
                for key in ["rating", "confidence"]:
                    if key in feedback_copy:
                        from decimal import Decimal

                        if isinstance(feedback_copy[key], Decimal):
                            feedback_copy[key] = float(feedback_copy[key])
                feedback_records.append(feedback_copy)

            data = json.dumps(feedback_records, default=str).encode("utf-8")
            compressed_data = gzip.compress(data)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=archive_key,
                Body=compressed_data,
                ContentType="application/gzip",
                ServerSideEncryption="AES256",
                Metadata={"archive-type": "feedback", "feedback-count": str(len(feedbacks))},
            )

            logger.info(f"Archived {len(feedbacks)} feedback entries to s3://{self.bucket_name}/{archive_key}")
            return True

        except Exception as e:
            logger.error(f"Error archiving feedback to S3: {e}")
            return False

    def list_archives(self, prefix: str = "", max_results: int = 1000) -> List[Dict[str, Any]]:
        """List archived files in S3."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix, MaxKeys=max_results)

            archives = []
            for obj in response.get("Contents", []):
                archives.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "storage_class": obj["StorageClass"],
                    }
                )

            return archives

        except Exception as e:
            logger.error(f"Error listing archives: {e}")
            return []

    def retrieve_archive(self, archive_key: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve and decompress archived data from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=archive_key)

            import gzip

            compressed_data = response["Body"].read()
            data = gzip.decompress(compressed_data).decode("utf-8")
            records = json.loads(data)

            logger.info(f"Retrieved {len(records)} records from {archive_key}")
            return records

        except Exception as e:
            logger.error(f"Error retrieving archive {archive_key}: {e}")
            return None

    def get_archive_statistics(self) -> Dict[str, Any]:
        """Get statistics about archived data."""
        try:
            stats = {
                "total_size_bytes": 0,
                "total_objects": 0,
                "by_type": {"events": 0, "decisions": 0, "feedback": 0},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)

            for obj in response.get("Contents", []):
                stats["total_size_bytes"] += obj["Size"]
                stats["total_objects"] += 1

                key = obj["Key"]
                if "events/" in key:
                    stats["by_type"]["events"] += 1
                elif "decisions/" in key:
                    stats["by_type"]["decisions"] += 1
                elif "feedback/" in key:
                    stats["by_type"]["feedback"] += 1

            return stats

        except Exception as e:
            logger.error(f"Error getting archive statistics: {e}")
            return {}

    def delete_old_archives(self, days_to_keep: int = 90) -> int:
        """Delete archives older than specified days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            deleted_count = 0

            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)

            for obj in response.get("Contents", []):
                if obj["LastModified"].replace(tzinfo=timezone.utc) < cutoff_date:
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj["Key"])
                    deleted_count += 1

            logger.info(f"Deleted {deleted_count} old archives (older than {days_to_keep} days)")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting old archives: {e}")
            return 0
