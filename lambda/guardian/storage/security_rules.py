"""Security Rules Repository for Sprint 33 Phase 1

Manages CRUD operations for security rules stored in DynamoDB.
Rules define threat detection conditions and alert actions.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import boto3
from botocore.exceptions import ClientError


class SecurityRule:
    """Data class representing a security rule"""

    def __init__(
        self,
        rule_id: str,
        rule_type: str,
        condition: Dict[str, Any],
        action: Dict[str, Any],
        priority: int,
        account_id: Optional[str] = None,
        enabled: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.condition = condition
        self.action = action
        self.priority = priority
        self.account_id = account_id
        self.enabled = enabled
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert rule to DynamoDB item format"""
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "condition": json.dumps(self.condition),
            "action": json.dumps(self.action),
            "priority": self.priority,
            "account_id": self.account_id or "all",
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    def from_dynamodb_item(item: Dict[str, Any]) -> "SecurityRule":
        """Create rule from DynamoDB item"""
        return SecurityRule(
            rule_id=item["rule_id"],
            rule_type=item["rule_type"],
            condition=json.loads(item["condition"]),
            action=json.loads(item["action"]),
            priority=item["priority"],
            account_id=item.get("account_id") if item.get("account_id") != "all" else None,
            enabled=item.get("enabled", True),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )


class SecurityRuleRepository:
    """Repository for managing security rules in DynamoDB"""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def create_rule(self, rule: SecurityRule) -> SecurityRule:
        """Create a new security rule"""
        try:
            rule.rule_id = rule.rule_id or str(uuid.uuid4())
            rule.created_at = datetime.utcnow()
            rule.updated_at = datetime.utcnow()

            self.table.put_item(Item=rule.to_dynamodb_item())
            return rule
        except ClientError as e:
            raise RuntimeError(f"Failed to create rule: {e}")

    def get_rule(self, rule_id: str) -> Optional[SecurityRule]:
        """Get a rule by ID"""
        try:
            response = self.table.get_item(Key={"rule_id": rule_id})
            if "Item" not in response:
                return None
            return SecurityRule.from_dynamodb_item(response["Item"])
        except ClientError as e:
            raise RuntimeError(f"Failed to get rule: {e}")

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> SecurityRule:
        """Update an existing rule"""
        try:
            existing_rule = self.get_rule(rule_id)
            if not existing_rule:
                raise ValueError(f"Rule {rule_id} not found")

            # Apply updates
            if "rule_type" in updates:
                existing_rule.rule_type = updates["rule_type"]
            if "condition" in updates:
                existing_rule.condition = updates["condition"]
            if "action" in updates:
                existing_rule.action = updates["action"]
            if "priority" in updates:
                existing_rule.priority = updates["priority"]
            if "account_id" in updates:
                existing_rule.account_id = updates["account_id"]
            if "enabled" in updates:
                existing_rule.enabled = updates["enabled"]

            existing_rule.updated_at = datetime.utcnow()

            self.table.put_item(Item=existing_rule.to_dynamodb_item())
            return existing_rule
        except ClientError as e:
            raise RuntimeError(f"Failed to update rule: {e}")

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by ID"""
        try:
            response = self.table.delete_item(
                Key={"rule_id": rule_id},
                ReturnValues="ALL_OLD",
            )
            return "Attributes" in response
        except ClientError as e:
            raise RuntimeError(f"Failed to delete rule: {e}")

    def list_rules_by_type(self, rule_type: str, enabled_only: bool = False) -> List[SecurityRule]:
        """List all rules of a specific type"""
        try:
            key_condition = "rule_type = :type"
            expression_values = {":type": rule_type}

            if enabled_only:
                # Add filter expression for enabled rules
                response = self.table.query(
                    IndexName="RuleTypeIndex",
                    KeyConditionExpression=key_condition,
                    ExpressionAttributeValues=expression_values,
                )
                items = response.get("Items", [])
                # Filter in application for enabled_only
                items = [item for item in items if item.get("enabled", True)]
            else:
                response = self.table.query(
                    IndexName="RuleTypeIndex",
                    KeyConditionExpression=key_condition,
                    ExpressionAttributeValues=expression_values,
                )
                items = response.get("Items", [])

            return [SecurityRule.from_dynamodb_item(item) for item in items]
        except ClientError as e:
            raise RuntimeError(f"Failed to list rules by type: {e}")

    def list_rules_by_account(
        self, account_id: Optional[str] = None, enabled_only: bool = False
    ) -> List[SecurityRule]:
        """List all rules for a specific account (or all accounts if account_id is None)"""
        try:
            account_filter = account_id or "all"
            key_condition = "account_id = :aid"
            expression_values = {":aid": account_filter}

            response = self.table.query(
                IndexName="AccountIdIndex",
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expression_values,
            )
            items = response.get("Items", [])

            if enabled_only:
                items = [item for item in items if item.get("enabled", True)]

            return [SecurityRule.from_dynamodb_item(item) for item in items]
        except ClientError as e:
            raise RuntimeError(f"Failed to list rules by account: {e}")

    def list_all_rules(self, enabled_only: bool = False) -> List[SecurityRule]:
        """List all rules"""
        try:
            response = self.table.scan()
            items = response.get("Items", [])

            if enabled_only:
                items = [item for item in items if item.get("enabled", True)]

            return [SecurityRule.from_dynamodb_item(item) for item in items]
        except ClientError as e:
            raise RuntimeError(f"Failed to list all rules: {e}")
