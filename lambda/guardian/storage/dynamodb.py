"""DynamoDB storage for AWS Guardian."""

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
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats(v) for v in obj]
    return obj


class DynamoDBStorage:
    def __init__(self, table_name: Optional[str] = None):
        self.table_name = table_name or Config.get_dynamodb_table_name()
        self.is_localstack = Config.is_localstack()

        try:
            self.table = AWSClientProvider.get_resource("dynamodb").Table(self.table_name)
        except Exception as e:
            logger.warning("Could not access table %s: %s", self.table_name, e)
            self.table = None

    def _put_item(self, item: Dict[str, Any]) -> bool:
        """Persist a single item to DynamoDB with error handling."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return False
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            logger.error("Error writing to DynamoDB: %s", e)
            return False

    def save_event(
        self, event_type: str, severity: str, details: Dict[str, Any], account_id: str = "current"
    ) -> bool:
        item = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "account_id": account_id,
            "gsi_pk": "EVENT",
            "details": (
                _convert_floats(details) if isinstance(details, dict) else {"raw": details}
            ),
        }
        return self._put_item(item)

    def save_auto_response(
        self, action_type: str, resource_id: str, status: str, details: Dict[str, Any]
    ) -> bool:
        item = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "auto_response",
            "severity": "info",
            "account_id": "current",
            "gsi_pk": "EVENT",
            "action_type": action_type,
            "resource_id": resource_id,
            "status": status,
            "details": (
                _convert_floats(details) if isinstance(details, dict) else {"raw": details}
            ),
        }
        return self._put_item(item)

    def get_recent_events(self, hours: int = 24, event_type: Optional[str] = None) -> List[Dict]:  # type: ignore
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            if event_type:
                index, pk_name, pk_val = (
                    "TypeTimestampIndex",
                    "event_type",
                    event_type,
                )
            else:
                index, pk_name, pk_val = "AllEventsIndex", "gsi_pk", "EVENT"

            response = self.table.query(
                IndexName=index,
                KeyConditionExpression=Key(pk_name).eq(pk_val)
                & Key("timestamp").gt(cutoff_time.isoformat()),
                ScanIndexForward=False,
                Limit=100,
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error("Error getting recent events: %s", e)
            return []

    def get_events_by_severity(self, severity: str, hours: int = 24) -> List[Dict]:
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            response = self.table.query(
                IndexName="SeverityTimestampIndex",
                KeyConditionExpression=Key("severity").eq(severity)
                & Key("timestamp").gt(cutoff_time.isoformat()),
                ScanIndexForward=False,
                Limit=100,
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error("Error getting events by severity: %s", e)
            return []

    def get_events_by_account(self, account_id: str, hours: int = 24) -> List[Dict]:
        """Query events for a specific account (Phase 4: Multi-account support).

        Falls back to scan if no account-specific GSI exists, but limits result size.
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Use scan with strict limit to prevent unbounded reads
            response = self.table.scan(
                FilterExpression=Attr("account_id").eq(account_id)
                & Attr("timestamp").gt(cutoff_time.isoformat()),
                Limit=100,
            )

            items = response.get("Items", [])
            # Do not paginate scans to avoid unbounded cost
            if len(items) >= 100:
                logger.warning(
                    "Account %s scan hit limit (100 items). Results may be incomplete.",
                    account_id,
                )
            return items
        except Exception as e:
            logger.error("Error getting events by account %s: %s", account_id, e)
            return []

    def get_event_summary(
        self, hours: int = 24, account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            if account_id:
                events = self.get_events_by_account(account_id, hours)
            else:
                events = self.get_recent_events(hours)

            summary: Dict[str, Any] = {
                "total_events": len(events),
                "by_type": {},
                "by_severity": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if account_id:
                summary["account_id"] = account_id

            for event in events:
                event_type = event.get("event_type", "unknown")
                severity = event.get("severity", "unknown")

                summary["by_type"][event_type] = summary["by_type"].get(event_type, 0) + 1
                summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

            return summary
        except Exception as e:
            logger.error("Error getting event summary: %s", e)
            return {}

    def get_latest_check_result(self, time_filter: Optional[str] = None) -> List[Dict]:
        try:
            cutoff = time_filter or (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

            response = self.table.query(
                IndexName="TypeTimestampIndex",
                KeyConditionExpression=Key("event_type").eq("check_result")
                & Key("timestamp").gt(cutoff),
                ScanIndexForward=False,
                Limit=10,
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error("Error getting latest check result: %s", e)
            return []

    def create_table(self) -> bool:
        try:
            dynamodb = AWSClientProvider.get_resource("dynamodb")
            dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {"AttributeName": "event_id", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "event_id", "AttributeType": "S"},
                    {"AttributeName": "timestamp", "AttributeType": "S"},
                    {"AttributeName": "event_type", "AttributeType": "S"},
                    {"AttributeName": "severity", "AttributeType": "S"},
                    {"AttributeName": "gsi_pk", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "AllEventsIndex",
                        "KeySchema": [
                            {"AttributeName": "gsi_pk", "KeyType": "HASH"},
                            {"AttributeName": "timestamp", "KeyType": "RANGE"},
                        ],
                        "Projection": {
                            "ProjectionType": "INCLUDE",
                            "NonKeyAttributes": ["event_type", "severity", "details"],
                        },
                    },
                    {
                        "IndexName": "TypeTimestampIndex",
                        "KeySchema": [
                            {"AttributeName": "event_type", "KeyType": "HASH"},
                            {"AttributeName": "timestamp", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                    {
                        "IndexName": "SeverityTimestampIndex",
                        "KeySchema": [
                            {"AttributeName": "severity", "KeyType": "HASH"},
                            {"AttributeName": "timestamp", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            self.table.meta.client.get_waiter("table_exists").wait(TableName=self.table_name)
            return True
        except Exception as e:
            if "ResourceInUseException" in str(e):
                logger.info("Table %s already exists", self.table_name)
                return True
            logger.error("Error creating table: %s", e)
            return False

    def _query_by_event_id(self, event_id: str) -> List[Dict]:
        """Query items by event_id, returning the raw response Items."""
        return self.table.query(
            KeyConditionExpression=Key("event_id").eq(event_id),
            Limit=1,
        ).get("Items", [])

    def get_item_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        try:
            if not self.table:
                return None
            items = self._query_by_event_id(event_id)
            return items[0] if items else None
        except Exception as e:
            logger.error("Error getting item by id %s: %s", event_id, e)
            return None

    def update_remediation_status(self, event_id: str, status: str, result: str = "") -> bool:
        """Update remediation status for an event.

        Note: This table uses a composite key (event_id HASH + timestamp RANGE).
        We query first to get the full key, then update.
        """
        try:
            if not self.table:
                return False

            # Retrieve the item first to get the full composite key
            items = self._query_by_event_id(event_id)
            if not items:
                logger.warning("No item found for event_id %s", event_id)
                return False

            item_key = {
                "event_id": items[0]["event_id"],
                "timestamp": items[0]["timestamp"],
            }

            update_expr = "SET remediation_status = :s"
            expr_values = {":s": status}
            if result:
                update_expr += ", remediation_result = :r"
                expr_values[":r"] = result
            self.table.update_item(
                Key=item_key,
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
            )
            return True
        except Exception as e:
            logger.error("Error updating remediation status for %s: %s", event_id, e)
            return False
