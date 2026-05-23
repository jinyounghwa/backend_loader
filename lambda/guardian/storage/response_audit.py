"""Advanced Response Audit System (Sprint 36 Phase 3)

Tracks automatic responses with full rollback capability.
Each response is recorded with metadata needed for rollback execution.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import boto3
import uuid
from botocore.exceptions import ClientError


@dataclass
class ResponseAction:
    """Represents an automatic response action with rollback metadata"""
    response_id: str
    threat_id: str
    rule_id: str
    action_type: str  # EC2_STOP, S3_BLOCK_PUBLIC, etc.
    target: str
    success: bool
    status: str  # EXECUTED, PENDING, FAILED, ROLLED_BACK, PARTIALLY_ROLLED_BACK
    timestamp: str
    executed_by: str  # 'system' for automatic, user ID for manual
    message: str

    # Rollback metadata
    can_rollback: bool = True
    rollback_action_type: Optional[str] = None  # e.g., EC2_START for EC2_STOP
    rollback_metadata: Optional[Dict[str, Any]] = None
    rollback_executed_at: Optional[str] = None
    rollback_status: Optional[str] = None  # SUCCESS, FAILED

    # Approval workflow
    requires_approval: bool = False
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    approval_message: Optional[str] = None

    # Resource state snapshot (for accurate rollback)
    pre_action_state: Optional[Dict[str, Any]] = None
    post_action_state: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ResponseAuditRepository:
    """Repository for managing response audit logs with rollback capability"""

    def __init__(self, table_name: str):
        """
        Initialize response audit repository
        Args:
            table_name: DynamoDB table name for response logs
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def record_response(
        self,
        threat_id: str,
        rule_id: str,
        action_type: str,
        target: str,
        success: bool,
        message: str,
        executed_by: str = "system",
        rollback_action_type: Optional[str] = None,
        rollback_metadata: Optional[Dict[str, Any]] = None,
        pre_action_state: Optional[Dict[str, Any]] = None,
        post_action_state: Optional[Dict[str, Any]] = None,
        requires_approval: bool = False
    ) -> ResponseAction:
        """
        Record an automatic response action
        Args:
            threat_id: ID of detected threat
            rule_id: ID of rule that triggered response
            action_type: Type of response (EC2_STOP, etc.)
            target: Target resource (instance ID, bucket, etc.)
            success: Whether action succeeded
            message: Action message
            executed_by: Who executed ('system' or user ID)
            rollback_action_type: What action to do for rollback (e.g., EC2_START)
            rollback_metadata: Metadata needed for rollback
            pre_action_state: State before action
            post_action_state: State after action
            requires_approval: Whether rollback requires approval
        Returns:
            Created ResponseAction
        """
        try:
            response_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()

            action = ResponseAction(
                response_id=response_id,
                threat_id=threat_id,
                rule_id=rule_id,
                action_type=action_type,
                target=target,
                success=success,
                status="EXECUTED" if success else "FAILED",
                timestamp=timestamp,
                executed_by=executed_by,
                message=message,
                rollback_action_type=rollback_action_type,
                rollback_metadata=rollback_metadata,
                pre_action_state=pre_action_state,
                post_action_state=post_action_state,
                requires_approval=requires_approval
            )

            self.table.put_item(Item=action.to_dict())
            return action

        except ClientError as e:
            print(f"Error recording response: {e}")
            raise

    def get_response(self, response_id: str) -> Optional[ResponseAction]:
        """Get a specific response action"""
        try:
            response = self.table.get_item(Key={"response_id": response_id})

            if "Item" not in response:
                return None

            item = response["Item"]
            return self._item_to_response(item)

        except ClientError as e:
            print(f"Error getting response: {e}")
            return None

    def list_responses_by_threat(
        self,
        threat_id: str,
        limit: int = 20
    ) -> List[ResponseAction]:
        """Get all responses for a threat"""
        try:
            response = self.table.query(
                IndexName="ThreatIdIndex",
                KeyConditionExpression="threat_id = :tid",
                ExpressionAttributeValues={":tid": threat_id},
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )

            responses = []
            for item in response.get("Items", []):
                responses.append(self._item_to_response(item))

            return responses

        except ClientError as e:
            print(f"Error listing responses by threat: {e}")
            return []

    def list_responses_by_rule(
        self,
        rule_id: str,
        limit: int = 20,
        filter_status: Optional[str] = None
    ) -> List[ResponseAction]:
        """Get all responses for a rule, optionally filtered by status"""
        try:
            response = self.table.query(
                IndexName="RuleIdIndex",
                KeyConditionExpression="rule_id = :rid",
                ExpressionAttributeValues={":rid": rule_id},
                Limit=limit,
                ScanIndexForward=False
            )

            responses = []
            for item in response.get("Items", []):
                action = self._item_to_response(item)
                if filter_status is None or action.status == filter_status:
                    responses.append(action)

            return responses

        except ClientError as e:
            print(f"Error listing responses by rule: {e}")
            return []

    def mark_rollback_executed(
        self,
        response_id: str,
        rollback_status: str,
        executed_by: str,
        message: str = ""
    ) -> bool:
        """
        Mark a response as rolled back
        Args:
            response_id: ID of response to rollback
            rollback_status: SUCCESS or FAILED
            executed_by: User who executed rollback
            message: Rollback message
        Returns:
            True if successful
        """
        try:
            self.table.update_item(
                Key={"response_id": response_id},
                UpdateExpression="""
                    SET #status = :status,
                        #rollback_executed = :executed,
                        #rollback_status = :rb_status,
                        #rollback_by = :executed_by,
                        #msg = :msg
                """,
                ExpressionAttributeNames={
                    "#status": "status",
                    "#rollback_executed": "rollback_executed_at",
                    "#rollback_status": "rollback_status",
                    "#rollback_by": "rollback_executed_by",
                    "#msg": "rollback_message"
                },
                ExpressionAttributeValues={
                    ":status": f"ROLLED_BACK",
                    ":executed": datetime.now(timezone.utc).isoformat(),
                    ":rb_status": rollback_status,
                    ":executed_by": executed_by,
                    ":msg": message
                }
            )
            return True

        except ClientError as e:
            print(f"Error marking rollback: {e}")
            return False

    def approve_response(
        self,
        response_id: str,
        approved_by: str,
        message: str = ""
    ) -> bool:
        """
        Approve a response action (for approval workflow)
        Args:
            response_id: ID of response to approve
            approved_by: User who approved
            message: Approval message
        Returns:
            True if successful
        """
        try:
            self.table.update_item(
                Key={"response_id": response_id},
                UpdateExpression="""
                    SET approved_at = :timestamp,
                        approved_by = :user,
                        approval_message = :msg
                """,
                ExpressionAttributeValues={
                    ":timestamp": datetime.now(timezone.utc).isoformat(),
                    ":user": approved_by,
                    ":msg": message
                }
            )
            return True

        except ClientError as e:
            print(f"Error approving response: {e}")
            return False

    def get_response_summary(self, rule_id: str) -> Dict[str, Any]:
        """Get response summary for a rule"""
        try:
            responses = self.list_responses_by_rule(rule_id, limit=100)

            total = len(responses)
            executed = sum(1 for r in responses if r.status == "EXECUTED")
            failed = sum(1 for r in responses if r.status == "FAILED")
            rolled_back = sum(1 for r in responses if r.status == "ROLLED_BACK")

            action_counts: Dict[str, int] = {}
            for response in responses:
                key = response.action_type
                action_counts[key] = action_counts.get(key, 0) + 1

            return {
                "rule_id": rule_id,
                "total_responses": total,
                "executed": executed,
                "failed": failed,
                "rolled_back": rolled_back,
                "success_rate": executed / total if total > 0 else 0,
                "action_counts": action_counts
            }

        except Exception as e:
            print(f"Error getting response summary: {e}")
            return {
                "rule_id": rule_id,
                "total_responses": 0,
                "executed": 0,
                "failed": 0,
                "rolled_back": 0,
                "success_rate": 0,
                "action_counts": {}
            }

    @staticmethod
    def _item_to_response(item: Dict[str, Any]) -> ResponseAction:
        """Convert DynamoDB item to ResponseAction"""
        return ResponseAction(
            response_id=item["response_id"],
            threat_id=item["threat_id"],
            rule_id=item["rule_id"],
            action_type=item["action_type"],
            target=item["target"],
            success=item["success"],
            status=item.get("status", "EXECUTED"),
            timestamp=item["timestamp"],
            executed_by=item.get("executed_by", "system"),
            message=item["message"],
            can_rollback=item.get("can_rollback", True),
            rollback_action_type=item.get("rollback_action_type"),
            rollback_metadata=item.get("rollback_metadata"),
            rollback_executed_at=item.get("rollback_executed_at"),
            rollback_status=item.get("rollback_status"),
            requires_approval=item.get("requires_approval", False),
            approved_at=item.get("approved_at"),
            approved_by=item.get("approved_by"),
            approval_message=item.get("approval_message"),
            pre_action_state=item.get("pre_action_state"),
            post_action_state=item.get("post_action_state")
        )
