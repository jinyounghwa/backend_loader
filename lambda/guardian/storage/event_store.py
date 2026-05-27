"""Event Store for persistence of CloudTrail events."""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from boto3.dynamodb.conditions import Attr, Key
from guardian.aws_client_provider import AWSClientProvider
from guardian.config import Config

logger = logging.getLogger(__name__)


def _convert_floats(obj: Any) -> Any:
    """Convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats(v) for v in obj]
    return obj


class EventStore:
    """Persistence layer for CloudTrail events."""

    def __init__(self, table_name: Optional[str] = None):
        self.table_name = table_name or f"{Config.get_project_name()}-event-store"
        self.is_localstack = Config.is_localstack()

        try:
            self.table = AWSClientProvider.get_resource("dynamodb").Table(self.table_name)
            logger.info(f"Initialized EventStore with table {self.table_name}")
        except Exception as e:
            logger.warning(f"Could not access table {self.table_name}: {e}")
            self.table = None

    def save_event(self, event_data: Dict[str, Any]) -> bool:
        """Save a single CloudTrail event to DynamoDB."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return False

            event_id = event_data.get("event_id") or str(uuid.uuid4())
            timestamp = event_data.get("timestamp") or datetime.now(timezone.utc).isoformat()

            item = {
                "event_id": event_id,
                "timestamp": timestamp,
                "account_id": event_data.get("account_id", "unknown"),
                "event_type": event_data.get("event_type", "unknown"),
                "source": event_data.get("source", "cloudtrail"),
                "severity": event_data.get("severity", "NORMAL"),
                "region": event_data.get("region", "unknown"),
                "principal_id": event_data.get("principal_id", "unknown"),
                "raw_event": json.dumps(event_data.get("raw_event", {})),
                "ttl": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            self.table.put_item(Item=_convert_floats(item))
            logger.debug(f"Saved event {event_id} to EventStore")
            return True

        except Exception as e:
            logger.error(f"Error saving event to EventStore: {e}")
            return False

    def save_events_batch(self, events: List[Dict[str, Any]]) -> int:
        """Save multiple events in batch."""
        if not self.table:
            logger.warning("DynamoDB table not available")
            return 0

        saved_count = 0
        with self.table.batch_writer(batch_size=25) as batch:
            for event_data in events:
                try:
                    event_id = event_data.get("event_id") or str(uuid.uuid4())
                    timestamp = event_data.get("timestamp") or datetime.now(timezone.utc).isoformat()

                    item = {
                        "event_id": event_id,
                        "timestamp": timestamp,
                        "account_id": event_data.get("account_id", "unknown"),
                        "event_type": event_data.get("event_type", "unknown"),
                        "source": event_data.get("source", "cloudtrail"),
                        "severity": event_data.get("severity", "NORMAL"),
                        "region": event_data.get("region", "unknown"),
                        "principal_id": event_data.get("principal_id", "unknown"),
                        "raw_event": json.dumps(event_data.get("raw_event", {})),
                        "ttl": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }

                    batch.put_item(Item=_convert_floats(item))
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error in batch save for event: {e}")
                    continue

        logger.info(f"Batch saved {saved_count}/{len(events)} events to EventStore")
        return saved_count

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single event by ID."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return None

            response = self.table.get_item(Key={"event_id": event_id})
            item = response.get("Item")

            if item:
                # Deserialize raw_event from JSON string
                if "raw_event" in item:
                    item["raw_event"] = json.loads(item.get("raw_event", "{}"))
                return dict(item)

            return None

        except Exception as e:
            logger.error(f"Error retrieving event {event_id}: {e}")
            return None

    def query_events_by_account(self, account_id: str, lookback_minutes: int = 60) -> List[Dict[str, Any]]:
        """Query events for a specific account within a time window."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return []

            cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)).isoformat()

            response = self.table.query(
                IndexName="AccountIdIndex",
                KeyConditionExpression=Key("account_id").eq(account_id) & Key("timestamp").gt(cutoff_time),
            )

            events = []
            for item in response.get("Items", []):
                if "raw_event" in item:
                    item["raw_event"] = json.loads(item.get("raw_event", "{}"))
                events.append(dict(item))

            return events

        except Exception as e:
            logger.error(f"Error querying events for account {account_id}: {e}")
            return []

    def query_events_by_type(self, event_type: str, lookback_minutes: int = 60) -> List[Dict[str, Any]]:
        """Query events by type within a time window."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return []

            cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)).isoformat()

            response = self.table.query(
                IndexName="EventTypeIndex",
                KeyConditionExpression=Key("event_type").eq(event_type) & Key("timestamp").gt(cutoff_time),
            )

            events = []
            for item in response.get("Items", []):
                if "raw_event" in item:
                    item["raw_event"] = json.loads(item.get("raw_event", "{}"))
                events.append(dict(item))

            return events

        except Exception as e:
            logger.error(f"Error querying events by type {event_type}: {e}")
            return []

    def query_events_by_severity(self, severity: str, lookback_hours: int = 24) -> List[Dict[str, Any]]:
        """Scan events by severity level."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return []

            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()

            response = self.table.scan(
                FilterExpression=Attr("severity").eq(severity) & Attr("timestamp").gt(cutoff_time),
                Limit=1000,
            )

            events = []
            for item in response.get("Items", []):
                if "raw_event" in item:
                    item["raw_event"] = json.loads(item.get("raw_event", "{}"))
                events.append(dict(item))

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    FilterExpression=Attr("severity").eq(severity) & Attr("timestamp").gt(cutoff_time),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                    Limit=1000,
                )
                for item in response.get("Items", []):
                    if "raw_event" in item:
                        item["raw_event"] = json.loads(item.get("raw_event", "{}"))
                    events.append(dict(item))

            return events

        except Exception as e:
            logger.error(f"Error querying events by severity: {e}")
            return []

    def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return False

            self.table.delete_item(Key={"event_id": event_id})
            logger.debug(f"Deleted event {event_id} from EventStore")
            return True

        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}")
            return False

    def get_statistics(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about stored events."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return {}

            if account_id:
                # Get count for specific account
                response = self.table.query(
                    IndexName="AccountIdIndex",
                    KeyConditionExpression=Key("account_id").eq(account_id),
                    Select="COUNT",
                )
                count = response.get("Count", 0)
            else:
                # Full table scan for count (use with caution in production)
                response = self.table.scan(Select="COUNT", Limit=1)
                count = response.get("Count", 0)

            return {"total_events": count, "account_id": account_id, "timestamp": datetime.now(timezone.utc).isoformat()}

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
