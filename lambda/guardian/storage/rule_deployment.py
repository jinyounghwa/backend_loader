"""Rule Deployment Repository for Sprint 35 Phase 2

Manages rule deployment history and state tracking.
Tracks deployment status, timestamps, and rollback information.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import boto3
import uuid
from botocore.exceptions import ClientError


@dataclass
class Deployment:
    """Represents a rule deployment"""
    rule_id: str
    deployment_id: str
    status: str  # PENDING, ACTIVE, FAILED, ROLLED_BACK
    deployment_date: str  # ISO format
    deployed_by: Optional[str] = None
    rule_content: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    previous_deployment_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class RuleDeploymentRepository:
    """Repository for managing rule deployments"""

    def __init__(self, table_name: str):
        """
        Initialize deployment repository
        Args:
            table_name: DynamoDB table name for deployments
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def create_deployment(
        self,
        rule_id: str,
        status: str = "PENDING",
        rule_content: Optional[Dict[str, Any]] = None,
        deployed_by: Optional[str] = None,
        previous_deployment_id: Optional[str] = None
    ) -> Deployment:
        """
        Create a new deployment record
        Args:
            rule_id: ID of the rule being deployed
            status: Deployment status (PENDING, ACTIVE, FAILED, ROLLED_BACK)
            rule_content: The rule configuration being deployed
            deployed_by: User/system that initiated the deployment
            previous_deployment_id: Previous deployment ID for rollback tracking
        Returns:
            Created Deployment object
        """
        try:
            deployment_id = str(uuid.uuid4())
            deployment_date = datetime.now(timezone.utc).isoformat()

            deployment = Deployment(
                rule_id=rule_id,
                deployment_id=deployment_id,
                status=status,
                deployment_date=deployment_date,
                deployed_by=deployed_by,
                rule_content=rule_content,
                previous_deployment_id=previous_deployment_id
            )

            self.table.put_item(Item=deployment.to_dict())
            return deployment

        except ClientError as e:
            print(f"Error creating deployment: {e}")
            raise

    def get_deployment(self, rule_id: str, deployment_id: str) -> Optional[Deployment]:
        """Get a specific deployment"""
        try:
            response = self.table.get_item(
                Key={
                    "rule_id": rule_id,
                    "deployment_id": deployment_id
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return Deployment(
                rule_id=item["rule_id"],
                deployment_id=item["deployment_id"],
                status=item["status"],
                deployment_date=item["deployment_date"],
                deployed_by=item.get("deployed_by"),
                rule_content=item.get("rule_content"),
                error_message=item.get("error_message"),
                previous_deployment_id=item.get("previous_deployment_id")
            )

        except ClientError as e:
            print(f"Error getting deployment: {e}")
            return None

    def list_deployments(
        self,
        rule_id: str,
        limit: int = 10
    ) -> List[Deployment]:
        """
        Get deployment history for a rule
        Args:
            rule_id: Rule ID to get deployments for
            limit: Maximum number of deployments to return
        Returns:
            List of deployments (most recent first)
        """
        try:
            response = self.table.query(
                KeyConditionExpression="rule_id = :rid",
                ExpressionAttributeValues={":rid": rule_id},
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )

            deployments = []
            for item in response.get("Items", []):
                deployment = Deployment(
                    rule_id=item["rule_id"],
                    deployment_id=item["deployment_id"],
                    status=item["status"],
                    deployment_date=item["deployment_date"],
                    deployed_by=item.get("deployed_by"),
                    rule_content=item.get("rule_content"),
                    error_message=item.get("error_message"),
                    previous_deployment_id=item.get("previous_deployment_id")
                )
                deployments.append(deployment)

            return deployments

        except ClientError as e:
            print(f"Error listing deployments: {e}")
            return []

    def update_deployment_status(
        self,
        rule_id: str,
        deployment_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Deployment]:
        """
        Update deployment status
        Args:
            rule_id: Rule ID
            deployment_id: Deployment ID
            status: New status
            error_message: Optional error message
        Returns:
            Updated deployment or None if failed
        """
        try:
            update_expr = "SET #status = :status"
            expr_values = {
                ":status": status
            }

            if error_message:
                update_expr += ", error_message = :error"
                expr_values[":error"] = error_message

            response = self.table.update_item(
                Key={
                    "rule_id": rule_id,
                    "deployment_id": deployment_id
                },
                UpdateExpression=update_expr,
                ExpressionAttributeNames={
                    "#status": "status"
                },
                ExpressionAttributeValues=expr_values,
                ReturnValues="ALL_NEW"
            )

            if "Attributes" not in response:
                return None

            item = response["Attributes"]
            return Deployment(
                rule_id=item["rule_id"],
                deployment_id=item["deployment_id"],
                status=item["status"],
                deployment_date=item["deployment_date"],
                deployed_by=item.get("deployed_by"),
                rule_content=item.get("rule_content"),
                error_message=item.get("error_message"),
                previous_deployment_id=item.get("previous_deployment_id")
            )

        except ClientError as e:
            print(f"Error updating deployment status: {e}")
            return None

    def get_active_deployment(self, rule_id: str) -> Optional[Deployment]:
        """
        Get the most recent ACTIVE deployment for a rule
        Args:
            rule_id: Rule ID to check
        Returns:
            Active deployment or None
        """
        try:
            deployments = self.list_deployments(rule_id, limit=20)

            for deployment in deployments:
                if deployment.status == "ACTIVE":
                    return deployment

            return None

        except Exception as e:
            print(f"Error getting active deployment: {e}")
            return None

    def count_active_deployments(self, rule_id: str) -> int:
        """Count how many active deployments exist for a rule"""
        try:
            deployments = self.list_deployments(rule_id, limit=100)
            return sum(1 for d in deployments if d.status == "ACTIVE")

        except Exception as e:
            print(f"Error counting active deployments: {e}")
            return 0
