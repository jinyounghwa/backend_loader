"""Decision Store for persistence of threat detection and response decisions."""

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


class DecisionStore:
    """Persistence layer for threat detection and response decisions."""

    def __init__(self, table_name: Optional[str] = None):
        self.table_name = table_name or f"{Config.get_project_name()}-decision-store"
        self.is_localstack = Config.is_localstack()

        try:
            self.table = AWSClientProvider.get_resource("dynamodb").Table(self.table_name)
            logger.info(f"Initialized DecisionStore with table {self.table_name}")
        except Exception as e:
            logger.warning(f"Could not access table {self.table_name}: {e}")
            self.table = None

    def save_decision(self, decision_data: Dict[str, Any]) -> bool:
        """Save a single threat detection decision to DynamoDB."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return False

            decision_id = decision_data.get("decision_id") or str(uuid.uuid4())
            timestamp = decision_data.get("timestamp") or datetime.now(timezone.utc).isoformat()

            item = {
                "decision_id": decision_id,
                "timestamp": timestamp,
                "threat_id": decision_data.get("threat_id", "unknown"),
                "severity": decision_data.get("severity", "NORMAL"),
                "detection_type": decision_data.get("detection_type", "unknown"),
                "event_count": Decimal(str(decision_data.get("event_count", 0))),
                "confidence": Decimal(str(decision_data.get("confidence", 0.0))),
                "z_score": Decimal(str(decision_data.get("z_score", 0.0))),
                "recommended_action": decision_data.get("recommended_action", "alert"),
                "executed_action": decision_data.get("executed_action", None),
                "action_cost": Decimal(str(decision_data.get("action_cost", 0))),
                "account_id": decision_data.get("account_id", "unknown"),
                "region": decision_data.get("region", "unknown"),
                "details": json.dumps(decision_data.get("details", {})),
                "ttl": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            self.table.put_item(Item=item)
            logger.debug(f"Saved decision {decision_id} to DecisionStore")
            return True

        except Exception as e:
            logger.error(f"Error saving decision to DecisionStore: {e}")
            return False

    def save_decisions_batch(self, decisions: List[Dict[str, Any]]) -> int:
        """Save multiple decisions in batch."""
        if not self.table:
            logger.warning("DynamoDB table not available")
            return 0

        saved_count = 0
        with self.table.batch_writer(batch_size=25) as batch:
            for decision_data in decisions:
                try:
                    decision_id = decision_data.get("decision_id") or str(uuid.uuid4())
                    timestamp = decision_data.get("timestamp") or datetime.now(timezone.utc).isoformat()

                    item = {
                        "decision_id": decision_id,
                        "timestamp": timestamp,
                        "threat_id": decision_data.get("threat_id", "unknown"),
                        "severity": decision_data.get("severity", "NORMAL"),
                        "detection_type": decision_data.get("detection_type", "unknown"),
                        "event_count": Decimal(str(decision_data.get("event_count", 0))),
                        "confidence": Decimal(str(decision_data.get("confidence", 0.0))),
                        "z_score": Decimal(str(decision_data.get("z_score", 0.0))),
                        "recommended_action": decision_data.get("recommended_action", "alert"),
                        "executed_action": decision_data.get("executed_action", None),
                        "action_cost": Decimal(str(decision_data.get("action_cost", 0))),
                        "account_id": decision_data.get("account_id", "unknown"),
                        "region": decision_data.get("region", "unknown"),
                        "details": json.dumps(decision_data.get("details", {})),
                        "ttl": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }

                    batch.put_item(Item=item)
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error in batch save for decision: {e}")
                    continue

        logger.info(f"Batch saved {saved_count}/{len(decisions)} decisions to DecisionStore")
        return saved_count

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single decision by ID."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return None

            response = self.table.get_item(Key={"decision_id": decision_id})
            item = response.get("Item")

            if item:
                # Deserialize details from JSON string
                if "details" in item:
                    item["details"] = json.loads(item.get("details", "{}"))
                # Convert Decimal to float
                if "confidence" in item:
                    item["confidence"] = float(item["confidence"])
                if "z_score" in item:
                    item["z_score"] = float(item["z_score"])
                if "event_count" in item:
                    item["event_count"] = int(item["event_count"])
                if "action_cost" in item:
                    item["action_cost"] = int(item["action_cost"])
                return dict(item)

            return None

        except Exception as e:
            logger.error(f"Error retrieving decision {decision_id}: {e}")
            return None

    def query_decisions_by_threat(self, threat_id: str) -> List[Dict[str, Any]]:
        """Query all decisions related to a specific threat."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return []

            response = self.table.query(
                IndexName="ThreatIdIndex",
                KeyConditionExpression=Key("threat_id").eq(threat_id),
            )

            decisions = []
            for item in response.get("Items", []):
                if "details" in item:
                    item["details"] = json.loads(item.get("details", "{}"))
                if "confidence" in item:
                    item["confidence"] = float(item["confidence"])
                if "z_score" in item:
                    item["z_score"] = float(item["z_score"])
                decisions.append(dict(item))

            return decisions

        except Exception as e:
            logger.error(f"Error querying decisions for threat {threat_id}: {e}")
            return []

    def query_decisions_by_severity(self, severity: str, lookback_hours: int = 24) -> List[Dict[str, Any]]:
        """Query decisions by severity level."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return []

            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()

            response = self.table.query(
                IndexName="SeverityIndex",
                KeyConditionExpression=Key("severity").eq(severity) & Key("timestamp").gt(cutoff_time),
            )

            decisions = []
            for item in response.get("Items", []):
                if "details" in item:
                    item["details"] = json.loads(item.get("details", "{}"))
                decisions.append(dict(item))

            return decisions

        except Exception as e:
            logger.error(f"Error querying decisions by severity: {e}")
            return []

    def update_decision_action(self, decision_id: str, executed_action: str, action_cost: int) -> bool:
        """Update decision with executed action and cost."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return False

            self.table.update_item(
                Key={"decision_id": decision_id},
                UpdateExpression="SET executed_action = :action, action_cost = :cost, updated_at = :now",
                ExpressionAttributeValues={
                    ":action": executed_action,
                    ":cost": Decimal(str(action_cost)),
                    ":now": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.debug(f"Updated decision {decision_id} with action {executed_action}")
            return True

        except Exception as e:
            logger.error(f"Error updating decision {decision_id}: {e}")
            return False

    def get_recent_decisions(self, limit: int = 100, lookback_hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent decisions within a time window."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return []

            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()

            response = self.table.scan(
                FilterExpression=Attr("timestamp").gt(cutoff_time),
                Limit=limit,
            )

            decisions = []
            for item in response.get("Items", []):
                if "details" in item:
                    item["details"] = json.loads(item.get("details", "{}"))
                decisions.append(dict(item))

            return sorted(decisions, key=lambda x: x.get("timestamp", ""), reverse=True)

        except Exception as e:
            logger.error(f"Error retrieving recent decisions: {e}")
            return []

    def get_statistics(self, account_id: Optional[str] = None, lookback_hours: int = 24) -> Dict[str, Any]:
        """Get statistics about decisions."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return {}

            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()

            response = self.table.scan(
                FilterExpression=Attr("timestamp").gt(cutoff_time),
                Select="COUNT",
            )

            total_decisions = response.get("Count", 0)

            # Count by severity
            severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "NORMAL": 0}
            response = self.table.scan(FilterExpression=Attr("timestamp").gt(cutoff_time))

            for item in response.get("Items", []):
                severity = item.get("severity", "NORMAL")
                if severity in severity_counts:
                    severity_counts[severity] += 1

            return {
                "total_decisions": total_decisions,
                "by_severity": severity_counts,
                "lookback_hours": lookback_hours,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting decision statistics: {e}")
            return {}
