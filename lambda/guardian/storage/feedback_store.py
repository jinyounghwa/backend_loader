"""Feedback Store for persistence of user feedback and learning data."""

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


class FeedbackStore:
    """Persistence layer for user feedback and learning data."""

    def __init__(self, table_name: Optional[str] = None):
        self.table_name = table_name or f"{Config.get_project_name()}-feedback-store"
        self.is_localstack = Config.is_localstack()

        try:
            self.table = AWSClientProvider.get_resource("dynamodb").Table(self.table_name)
            logger.info(f"Initialized FeedbackStore with table {self.table_name}")
        except Exception as e:
            logger.warning(f"Could not access table {self.table_name}: {e}")
            self.table = None

    def save_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """Save a single feedback entry to DynamoDB."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return False

            feedback_id = feedback_data.get("feedback_id") or str(uuid.uuid4())
            timestamp = feedback_data.get("timestamp") or datetime.now(timezone.utc).isoformat()

            item = {
                "feedback_id": feedback_id,
                "timestamp": timestamp,
                "decision_id": feedback_data.get("decision_id", "unknown"),
                "feedback_type": feedback_data.get("feedback_type", "unknown"),  # success, partial, failure
                "rating": Decimal(str(feedback_data.get("rating", 0))),  # 0-10 scale
                "confidence": Decimal(str(feedback_data.get("confidence", 0.0))),  # 0-1 scale
                "comments": feedback_data.get("comments", ""),
                "threat_id": feedback_data.get("threat_id", "unknown"),
                "action_taken": feedback_data.get("action_taken", None),
                "outcome_description": feedback_data.get("outcome_description", ""),
                "user_id": feedback_data.get("user_id", "automated"),
                "tags": feedback_data.get("tags", []),
                "ttl": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            self.table.put_item(Item=item)
            logger.debug(f"Saved feedback {feedback_id} to FeedbackStore")
            return True

        except Exception as e:
            logger.error(f"Error saving feedback to FeedbackStore: {e}")
            return False

    def save_feedback_batch(self, feedbacks: List[Dict[str, Any]]) -> int:
        """Save multiple feedback entries in batch."""
        if not self.table:
            logger.warning("DynamoDB table not available")
            return 0

        saved_count = 0
        with self.table.batch_writer(batch_size=25) as batch:
            for feedback_data in feedbacks:
                try:
                    feedback_id = feedback_data.get("feedback_id") or str(uuid.uuid4())
                    timestamp = feedback_data.get("timestamp") or datetime.now(timezone.utc).isoformat()

                    item = {
                        "feedback_id": feedback_id,
                        "timestamp": timestamp,
                        "decision_id": feedback_data.get("decision_id", "unknown"),
                        "feedback_type": feedback_data.get("feedback_type", "unknown"),
                        "rating": Decimal(str(feedback_data.get("rating", 0))),
                        "confidence": Decimal(str(feedback_data.get("confidence", 0.0))),
                        "comments": feedback_data.get("comments", ""),
                        "threat_id": feedback_data.get("threat_id", "unknown"),
                        "action_taken": feedback_data.get("action_taken", None),
                        "outcome_description": feedback_data.get("outcome_description", ""),
                        "user_id": feedback_data.get("user_id", "automated"),
                        "tags": feedback_data.get("tags", []),
                        "ttl": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }

                    batch.put_item(Item=item)
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Error in batch save for feedback: {e}")
                    continue

        logger.info(f"Batch saved {saved_count}/{len(feedbacks)} feedback entries to FeedbackStore")
        return saved_count

    def get_feedback(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single feedback entry by ID."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return None

            response = self.table.get_item(Key={"feedback_id": feedback_id})
            item = response.get("Item")

            if item:
                # Convert Decimal to float
                if "rating" in item:
                    item["rating"] = int(item["rating"])
                if "confidence" in item:
                    item["confidence"] = float(item["confidence"])
                return dict(item)

            return None

        except Exception as e:
            logger.error(f"Error retrieving feedback {feedback_id}: {e}")
            return None

    def query_feedback_by_decision(self, decision_id: str) -> List[Dict[str, Any]]:
        """Query all feedback for a specific decision."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return []

            response = self.table.query(
                IndexName="DecisionIdIndex",
                KeyConditionExpression=Key("decision_id").eq(decision_id),
            )

            feedbacks = []
            for item in response.get("Items", []):
                if "rating" in item:
                    item["rating"] = int(item["rating"])
                if "confidence" in item:
                    item["confidence"] = float(item["confidence"])
                feedbacks.append(dict(item))

            return feedbacks

        except Exception as e:
            logger.error(f"Error querying feedback for decision {decision_id}: {e}")
            return []

    def query_feedback_by_type(self, feedback_type: str, lookback_hours: int = 24) -> List[Dict[str, Any]]:
        """Query feedback by type within a time window."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return []

            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()

            response = self.table.query(
                IndexName="FeedbackTypeIndex",
                KeyConditionExpression=Key("feedback_type").eq(feedback_type) & Key("timestamp").gt(cutoff_time),
            )

            feedbacks = []
            for item in response.get("Items", []):
                if "rating" in item:
                    item["rating"] = int(item["rating"])
                if "confidence" in item:
                    item["confidence"] = float(item["confidence"])
                feedbacks.append(dict(item))

            return feedbacks

        except Exception as e:
            logger.error(f"Error querying feedback by type {feedback_type}: {e}")
            return []

    def update_feedback(self, feedback_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing feedback entry."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return False

            update_expression_parts = []
            expression_values = {":now": datetime.now(timezone.utc).isoformat()}

            for key, value in updates.items():
                if key in ["rating", "confidence"]:
                    value = Decimal(str(value))
                expression_values[f":{key}"] = value
                update_expression_parts.append(f"{key} = :{key}")

            update_expression_parts.append("updated_at = :now")
            update_expression = "SET " + ", ".join(update_expression_parts)

            self.table.update_item(
                Key={"feedback_id": feedback_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
            )

            logger.debug(f"Updated feedback {feedback_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating feedback {feedback_id}: {e}")
            return False

    def get_learning_summary(self, lookback_hours: int = 24) -> Dict[str, Any]:
        """Get learning summary from recent feedback."""
        try:
            if not self.table:
                logger.warning("DynamoDB table not available")
                return {}

            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()

            response = self.table.scan(FilterExpression=Attr("timestamp").gt(cutoff_time))

            feedback_by_type = {"success": 0, "partial": 0, "failure": 0}
            total_rating = 0
            feedback_count = 0
            avg_confidence = 0.0

            for item in response.get("Items", []):
                feedback_type = item.get("feedback_type", "unknown")
                if feedback_type in feedback_by_type:
                    feedback_by_type[feedback_type] += 1

                rating = item.get("rating", 0)
                if isinstance(rating, Decimal):
                    rating = int(rating)
                total_rating += rating

                confidence = item.get("confidence", 0.0)
                if isinstance(confidence, Decimal):
                    confidence = float(confidence)
                avg_confidence += confidence

                feedback_count += 1

            if feedback_count > 0:
                avg_confidence /= feedback_count
                avg_rating = total_rating / feedback_count
            else:
                avg_rating = 0
                avg_confidence = 0

            return {
                "total_feedback": feedback_count,
                "by_type": feedback_by_type,
                "average_rating": round(avg_rating, 2),
                "average_confidence": round(avg_confidence, 2),
                "lookback_hours": lookback_hours,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting learning summary: {e}")
            return {}
