"""Rule Version Repository for Sprint 35 Phase 3

Manages rule version history and enables rollback to previous versions.
Tracks all rule changes with timestamps for complete audit trail.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import boto3
import uuid
from botocore.exceptions import ClientError


@dataclass
class RuleVersion:
    """Represents a single version of a rule"""
    rule_id: str
    version_id: str
    version_number: int
    rule_content: Dict[str, Any]
    created_at: str
    created_by: Optional[str] = None
    change_reason: Optional[str] = None
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class RuleVersionRepository:
    """Repository for managing rule versions"""

    def __init__(self, table_name: str):
        """
        Initialize version repository
        Args:
            table_name: DynamoDB table name for rule versions
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def save_version(
        self,
        rule_id: str,
        rule_content: Dict[str, Any],
        created_by: Optional[str] = None,
        change_reason: Optional[str] = None
    ) -> RuleVersion:
        """
        Save a new version of a rule
        Args:
            rule_id: ID of the rule
            rule_content: The complete rule configuration
            created_by: User or system that made the change
            change_reason: Reason for the version (e.g., "Manual update", "Rollback")
        Returns:
            Created RuleVersion object
        """
        try:
            # Get current version count to increment
            current_versions = self.list_versions(rule_id, limit=1)
            next_version_number = (current_versions[0].version_number + 1 if current_versions else 1)

            version_id = str(uuid.uuid4())
            created_at = datetime.now(timezone.utc).isoformat()

            version = RuleVersion(
                rule_id=rule_id,
                version_id=version_id,
                version_number=next_version_number,
                rule_content=rule_content,
                created_at=created_at,
                created_by=created_by,
                change_reason=change_reason,
                is_active=False
            )

            self.table.put_item(Item=version.to_dict())
            return version

        except ClientError as e:
            print(f"Error saving version: {e}")
            raise

    def get_version(self, rule_id: str, version_id: str) -> Optional[RuleVersion]:
        """
        Get a specific version of a rule
        Args:
            rule_id: Rule ID
            version_id: Version ID to retrieve
        Returns:
            RuleVersion object or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    "rule_id": rule_id,
                    "version_id": version_id
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]
            return RuleVersion(
                rule_id=item["rule_id"],
                version_id=item["version_id"],
                version_number=item.get("version_number", 1),
                rule_content=item.get("rule_content", {}),
                created_at=item.get("created_at", ""),
                created_by=item.get("created_by"),
                change_reason=item.get("change_reason"),
                is_active=item.get("is_active", False)
            )

        except ClientError as e:
            print(f"Error getting version: {e}")
            return None

    def list_versions(
        self,
        rule_id: str,
        limit: int = 20
    ) -> List[RuleVersion]:
        """
        Get all versions of a rule
        Args:
            rule_id: Rule ID to get versions for
            limit: Maximum number of versions to return
        Returns:
            List of RuleVersion objects (most recent first)
        """
        try:
            response = self.table.query(
                KeyConditionExpression="rule_id = :rid",
                ExpressionAttributeValues={":rid": rule_id},
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )

            versions = []
            for item in response.get("Items", []):
                version = RuleVersion(
                    rule_id=item["rule_id"],
                    version_id=item["version_id"],
                    version_number=item.get("version_number", 1),
                    rule_content=item.get("rule_content", {}),
                    created_at=item.get("created_at", ""),
                    created_by=item.get("created_by"),
                    change_reason=item.get("change_reason"),
                    is_active=item.get("is_active", False)
                )
                versions.append(version)

            return versions

        except ClientError as e:
            print(f"Error listing versions: {e}")
            return []

    def get_latest_version(self, rule_id: str) -> Optional[RuleVersion]:
        """
        Get the most recent version of a rule
        Args:
            rule_id: Rule ID to get latest version for
        Returns:
            Latest RuleVersion or None
        """
        try:
            versions = self.list_versions(rule_id, limit=1)
            return versions[0] if versions else None

        except Exception as e:
            print(f"Error getting latest version: {e}")
            return None

    def rollback_to_version(
        self,
        rule_id: str,
        version_id: str,
        rolled_back_by: Optional[str] = None
    ) -> Optional[RuleVersion]:
        """
        Rollback to a previous version
        Args:
            rule_id: Rule ID
            version_id: Version to rollback to
            rolled_back_by: User or system performing rollback
        Returns:
            The version being restored, or None if failed
        """
        try:
            # Get the target version
            target_version = self.get_version(rule_id, version_id)
            if not target_version:
                print(f"Version {version_id} not found")
                return None

            # Create a new version from the old one
            new_version = self.save_version(
                rule_id=rule_id,
                rule_content=target_version.rule_content,
                created_by=rolled_back_by,
                change_reason=f"Rollback to version {version_id}"
            )

            return new_version

        except Exception as e:
            print(f"Error rolling back version: {e}")
            return None

    def count_versions(self, rule_id: str) -> int:
        """Count total versions for a rule"""
        try:
            versions = self.list_versions(rule_id, limit=100)
            return len(versions)

        except Exception as e:
            print(f"Error counting versions: {e}")
            return 0
