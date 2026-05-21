"""DynamoDB response rules management for multi-region auto-remediation."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)

TABLE_NAME = "guardian-response-rules"
CACHE_TTL_SECONDS = 300

_rule_cache: Dict[str, tuple] = {}


def _get_table():
    try:
        return AWSClientProvider.get_resource("dynamodb").Table(TABLE_NAME)
    except Exception as e:
        logger.error("Could not access response rules table: %s", e)
        return None


class ResponseRule:
    def __init__(
        self,
        rule_id: str,
        region: str,
        event_type: str,
        action: str,
        enabled: bool = True,
        priority: int = 100,
        dry_run: bool = False,
        created_at: Optional[str] = None,
        created_by: Optional[str] = None,
    ):
        self.rule_id = rule_id
        self.region = region
        self.event_type = event_type
        self.action = action
        self.enabled = enabled
        self.priority = priority
        self.dry_run = dry_run
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.created_by = created_by

    def to_item(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "region": self.region,
            "event_type": self.event_type,
            "action": self.action,
            "enabled": self.enabled,
            "priority": self.priority,
            "dry_run": self.dry_run,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }

    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> "ResponseRule":
        return cls(
            rule_id=item["rule_id"],
            region=item["region"],
            event_type=item["event_type"],
            action=item["action"],
            enabled=item.get("enabled", True),
            priority=item.get("priority", 100),
            dry_run=item.get("dry_run", False),
            created_at=item.get("created_at"),
            created_by=item.get("created_by"),
        )


class ResponseRuleStorage:
    def __init__(self):
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = _get_table()
        return self._table

    def save_rule(self, rule: ResponseRule) -> bool:
        try:
            if self.table is None:
                return False
            self.table.put_item(Item=rule.to_item())
            _clear_cache()
            return True
        except Exception as e:
            logger.error("Error saving rule %s: %s", rule.rule_id, e)
            return False

    def get_rule(self, rule_id: str) -> Optional[ResponseRule]:
        try:
            if self.table is None:
                return None
            response = self.table.get_item(Key={"rule_id": rule_id})
            if "Item" in response:
                return ResponseRule.from_item(response["Item"])
        except Exception as e:
            logger.error("Error getting rule %s: %s", rule_id, e)
        return None

    def get_rules_for_region(self, region: str) -> List[ResponseRule]:  # type: ignore
        cache_key = f"region:{region}"
        now = time.time()

        if cache_key in _rule_cache:
            rules, timestamp = _rule_cache[cache_key]
            if now - timestamp < CACHE_TTL_SECONDS:
                return rules

        try:
            if self.table is None:
                return []

            response_regional = self.table.query(
                IndexName="region-event_type-index",
                KeyConditionExpression="region = :region",
                ExpressionAttributeValues={":region": region},
            )

            response_wildcard = self.table.query(
                IndexName="region-event_type-index",
                KeyConditionExpression="region = :region",
                ExpressionAttributeValues={":region": "*"},
            )

            rules = [
                ResponseRule.from_item(item)
                for item in response_regional.get("Items", []) + response_wildcard.get("Items", [])
                if item.get("enabled", True)
            ]

            rules.sort(key=lambda r: r.priority)
            _rule_cache[cache_key] = (rules, now)
            return rules

        except Exception as e:
            logger.error("Error querying rules for region %s: %s", region, e)
            return []

    def get_effective_rule(self, region: str, event_type: str) -> Optional[ResponseRule]:
        rules = self.get_rules_for_region(region)
        matching = [r for r in rules if r.event_type == event_type]

        regional = [r for r in matching if r.region == region]
        if regional:
            return regional[0]

        wildcard = [r for r in matching if r.region == "*"]
        if wildcard:
            return wildcard[0]

        return None

    def delete_rule(self, rule_id: str) -> bool:
        try:
            if self.table is None:
                return False
            self.table.delete_item(Key={"rule_id": rule_id})
            _clear_cache()
            return True
        except Exception as e:
            logger.error("Error deleting rule %s: %s", rule_id, e)
            return False


def _clear_cache() -> None:
    _rule_cache.clear()
