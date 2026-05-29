"""Rule Template Repository for Sprint 34 Phase 1

Manages CRUD operations for rule templates stored in DynamoDB.
Templates provide reusable rule configurations for common threat patterns.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import boto3
from botocore.exceptions import ClientError


class RuleTemplate:
    """Data class representing a rule template"""

    def __init__(
        self,
        template_id: str,
        template_name: str,
        description: str,
        rule_type: str,
        condition_schema: Dict[str, Any],
        action_schema: Dict[str, Any],
        example_condition: Dict[str, Any],
        example_action: Dict[str, Any],
        tags: Optional[List[str]] = None,
        version: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.template_id = template_id
        self.template_name = template_name
        self.description = description
        self.rule_type = rule_type
        self.condition_schema = condition_schema
        self.action_schema = action_schema
        self.example_condition = example_condition
        self.example_action = example_action
        self.tags = tags or []
        self.version = version
        self.created_at = created_at or datetime.now(timezone.utc).replace(tzinfo=None)
        self.updated_at = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert template to DynamoDB item format"""
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "description": self.description,
            "rule_type": self.rule_type,
            "condition_schema": json.dumps(self.condition_schema),
            "action_schema": json.dumps(self.action_schema),
            "example_condition": json.dumps(self.example_condition),
            "example_action": json.dumps(self.example_action),
            "tags": self.tags,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    def from_dynamodb_item(item: Dict[str, Any]) -> "RuleTemplate":
        """Create template from DynamoDB item"""
        return RuleTemplate(
            template_id=item["template_id"],
            template_name=item["template_name"],
            description=item["description"],
            rule_type=item["rule_type"],
            condition_schema=json.loads(item["condition_schema"]),
            action_schema=json.loads(item["action_schema"]),
            example_condition=json.loads(item["example_condition"]),
            example_action=json.loads(item["example_action"]),
            tags=item.get("tags", []),
            version=item.get("version", 1),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )


# Built-in templates for common threat patterns
BUILTIN_TEMPLATES = [
    RuleTemplate(
        template_id="template-connection-spike",
        template_name="Connection Spike Detection",
        description="Detect sudden spike in WebSocket connection attempts",
        rule_type="connection_spike",
        condition_schema={"threshold": "integer", "window_minutes": "integer"},
        action_schema={"notify": "list of strings"},
        example_condition={"threshold": 10, "window_minutes": 5},
        example_action={"notify": ["telegram", "discord"]},
        tags=["network", "realtime", "security"],
        version=1,
    ),
    RuleTemplate(
        template_id="template-auth-failure",
        template_name="Authentication Failure Detection",
        description="Detect excessive authentication failures",
        rule_type="auth_failure",
        condition_schema={"threshold": "integer"},
        action_schema={"notify": "list of strings"},
        example_condition={"threshold": 5},
        example_action={"notify": ["telegram", "discord"]},
        tags=["authentication", "security"],
        version=1,
    ),
    RuleTemplate(
        template_id="template-unknown-region",
        template_name="Unknown Region Detection",
        description="Detect operations from unauthorized AWS regions",
        rule_type="unknown_region",
        condition_schema={"allowed_regions": "list of region codes"},
        action_schema={"notify": "list of strings"},
        example_condition={"allowed_regions": ["ap-northeast-1", "us-east-1"]},
        example_action={"notify": ["telegram", "discord"]},
        tags=["compliance", "regional", "security"],
        version=1,
    ),
    RuleTemplate(
        template_id="template-public-bucket",
        template_name="Public Bucket Detection",
        description="Detect public S3 bucket creation or modification",
        rule_type="public_bucket",
        condition_schema={},
        action_schema={"notify": "list of strings"},
        example_condition={},
        example_action={"notify": ["telegram", "discord"]},
        tags=["s3", "compliance", "security"],
        version=1,
    ),
]


class TemplateRepository:
    """Repository for managing rule templates in DynamoDB"""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def create_template(self, template: RuleTemplate) -> RuleTemplate:
        """Create a new rule template"""
        try:
            template.template_id = template.template_id or str(uuid.uuid4())
            self.table.put_item(Item=template.to_dynamodb_item())
            return template
        except ClientError as e:
            print(f"Error creating template: {e}")
            raise

    def get_template(self, template_id: str) -> Optional[RuleTemplate]:
        """Get a template by ID"""
        try:
            response = self.table.get_item(Key={"template_id": template_id})
            if "Item" in response:
                return RuleTemplate.from_dynamodb_item(response["Item"])
            return None
        except ClientError as e:
            print(f"Error getting template: {e}")
            return None

    def update_template(self, template: RuleTemplate) -> bool:
        """Update an existing template"""
        try:
            template.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.table.put_item(Item=template.to_dynamodb_item())
            return True
        except ClientError as e:
            print(f"Error updating template: {e}")
            return False

    def delete_template(self, template_id: str) -> bool:
        """Delete a template by ID"""
        try:
            self.table.delete_item(Key={"template_id": template_id})
            return True
        except ClientError as e:
            print(f"Error deleting template: {e}")
            return False

    def list_templates(self) -> List[RuleTemplate]:
        """List all templates (latest version only)"""
        try:
            response = self.table.scan()
            templates = []

            # Group by template_name and keep only latest version
            template_dict = {}
            for item in response.get("Items", []):
                template = RuleTemplate.from_dynamodb_item(item)
                key = template.template_name

                if key not in template_dict or template.version > template_dict[key].version:
                    template_dict[key] = template

            return list(template_dict.values())
        except ClientError as e:
            print(f"Error listing templates: {e}")
            return []

    def list_versions(self, template_name: str) -> List[RuleTemplate]:
        """List all versions of a template"""
        try:
            response = self.table.query(
                IndexName="TemplateNameIndex",
                KeyConditionExpression="template_name = :tn",
                ExpressionAttributeValues={":tn": template_name},
            )

            templates = [RuleTemplate.from_dynamodb_item(item) for item in response.get("Items", [])]
            # Sort by version descending
            templates.sort(key=lambda t: t.version, reverse=True)
            return templates
        except ClientError as e:
            print(f"Error listing versions: {e}")
            return []

    def bootstrap_builtin_templates(self) -> bool:
        """Initialize built-in templates"""
        try:
            for template in BUILTIN_TEMPLATES:
                existing = self.get_template(template.template_id)
                if not existing:
                    self.create_template(template)
            return True
        except Exception as e:
            print(f"Error bootstrapping templates: {e}")
            return False
