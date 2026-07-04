"""Version Manager for Sprint 35 Phase 3

Manages rule versioning logic and coordinates version transitions.
Handles version tracking, comparisons, and rollback workflows.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from guardian.storage.rule_version import RuleVersionRepository, RuleVersion


class VersionManager:
    """Manages rule versioning and rollback operations"""

    def __init__(self, version_repo: RuleVersionRepository):
        """
        Initialize version manager
        Args:
            version_repo: RuleVersionRepository instance
        """
        self.version_repo = version_repo

    def create_new_version(
        self,
        rule_id: str,
        rule_content: Dict[str, Any],
        user_id: Optional[str] = None,
        reason: str = "Manual update"
    ) -> RuleVersion:
        """
        Create and save a new version
        Args:
            rule_id: Rule ID
            rule_content: New rule configuration
            user_id: User making the change
            reason: Change reason for audit trail
        Returns:
            Created RuleVersion
        """
        return self.version_repo.save_version(
            rule_id=rule_id,
            rule_content=rule_content,
            created_by=user_id,
            change_reason=reason
        )

    def get_version_history(self, rule_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get formatted version history for display
        Args:
            rule_id: Rule ID
            limit: Max versions to return
        Returns:
            List of formatted version objects
        """
        versions = self.version_repo.list_versions(rule_id, limit=limit)
        return [
            {
                "version_id": v.version_id,
                "version_number": v.version_number,
                "created_at": v.created_at,
                "created_by": v.created_by or "system",
                "change_reason": v.change_reason or "Update",
                "rule_content": v.rule_content,
            }
            for v in versions
        ]

    def can_rollback(self, rule_id: str, version_id: str) -> Tuple[bool, str]:
        """
        Check if a version can be rolled back to
        Args:
            rule_id: Rule ID
            version_id: Version to rollback to
        Returns:
            (can_rollback: bool, message: str)
        """
        target = self.version_repo.get_version(rule_id, version_id)
        if not target:
            return False, "Version not found"

        if target.rule_content is None or not target.rule_content:
            return False, "Version content is empty"

        # Check if this is not the current version
        latest = self.version_repo.get_latest_version(rule_id)
        if latest and latest.version_id == version_id:
            return False, "Cannot rollback to current version"

        return True, "Ready to rollback"

    def perform_rollback(
        self,
        rule_id: str,
        version_id: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[RuleVersion]]:
        """
        Perform rollback to a previous version
        Args:
            rule_id: Rule ID
            version_id: Version to rollback to
            user_id: User performing rollback
        Returns:
            (success: bool, message: str, new_version: Optional[RuleVersion])
        """
        # Validate rollback is possible
        can_rollback, message = self.can_rollback(rule_id, version_id)
        if not can_rollback:
            return False, message, None

        # Get the target version
        target = self.version_repo.get_version(rule_id, version_id)
        if not target:
            return False, "Failed to retrieve target version", None

        # Create new version from old one
        try:
            new_version = self.version_repo.rollback_to_version(
                rule_id=rule_id,
                version_id=version_id,
                rolled_back_by=user_id
            )

            if not new_version:
                return False, "Failed to create rollback version", None

            return True, f"Successfully rolled back to version {target.version_number}", new_version

        except Exception as e:
            return False, f"Rollback failed: {str(e)}", None

    def get_version_diff(
        self,
        rule_id: str,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two versions and return differences
        Args:
            rule_id: Rule ID
            version_id_1: First version
            version_id_2: Second version
        Returns:
            Dictionary showing differences
        """
        v1 = self.version_repo.get_version(rule_id, version_id_1)
        v2 = self.version_repo.get_version(rule_id, version_id_2)

        if not v1 or not v2:
            return {"error": "One or both versions not found"}

        differences = {
            "version_1": {
                "version_id": v1.version_id,
                "version_number": v1.version_number,
                "created_at": v1.created_at,
            },
            "version_2": {
                "version_id": v2.version_id,
                "version_number": v2.version_number,
                "created_at": v2.created_at,
            },
            "changes": self._compute_diff(v1.rule_content, v2.rule_content),
        }

        return differences

    def _compute_diff(self, obj1: Any, obj2: Any) -> Dict[str, Any]:
        """Compute differences between two rule contents"""
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            all_keys = set(obj1.keys()) | set(obj2.keys())
            changes = {}

            for key in all_keys:
                val1 = obj1.get(key)
                val2 = obj2.get(key)

                if val1 != val2:
                    changes[key] = {
                        "old": val1,
                        "new": val2,
                    }

            return changes

        return {"changed": obj1 != obj2, "old": obj1, "new": obj2}

    def get_version_stats(self, rule_id: str) -> Dict[str, Any]:
        """
        Get version statistics for a rule
        Args:
            rule_id: Rule ID
        Returns:
            Dictionary with version statistics
        """
        versions = self.version_repo.list_versions(rule_id, limit=100)
        latest = self.version_repo.get_latest_version(rule_id)

        return {
            "rule_id": rule_id,
            "total_versions": len(versions),
            "latest_version_number": latest.version_number if latest else 0,
            "first_version_date": versions[-1].created_at if versions else None,
            "last_modified_date": versions[0].created_at if versions else None,
            "versions_list": self.get_version_history(rule_id, limit=10),
        }
