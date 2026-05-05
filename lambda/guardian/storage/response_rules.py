"""DynamoDB response rules management for multi-region auto-remediation."""

import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
import boto3

TABLE_NAME = 'guardian-response-rules'

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

# In-memory rule cache with TTL
_rule_cache: Dict[str, tuple[list, float]] = {}
CACHE_TTL_SECONDS = 300


class ResponseRule:
    """Multi-region response rule model."""

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
        self.region = region  # "ap-northeast-1" or "*" for global
        self.event_type = event_type  # "open_port", "unauthorized_region", "public_bucket"
        self.action = action  # "stop_instance", "block_bucket"
        self.enabled = enabled
        self.priority = priority  # Lower = higher priority
        self.dry_run = dry_run  # Log only, don't execute
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.created_by = created_by

    def to_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item."""
        return {
            'rule_id': self.rule_id,
            'region': self.region,
            'event_type': self.event_type,
            'action': self.action,
            'enabled': self.enabled,
            'priority': self.priority,
            'dry_run': self.dry_run,
            'created_at': self.created_at,
            'created_by': self.created_by,
        }

    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> 'ResponseRule':
        """Create from DynamoDB item."""
        return cls(
            rule_id=item['rule_id'],
            region=item['region'],
            event_type=item['event_type'],
            action=item['action'],
            enabled=item.get('enabled', True),
            priority=item.get('priority', 100),
            dry_run=item.get('dry_run', False),
            created_at=item.get('created_at'),
            created_by=item.get('created_by'),
        )


def save_rule(rule: ResponseRule) -> bool:
    """Save a response rule to DynamoDB."""
    try:
        table.put_item(Item=rule.to_item())
        _clear_cache()
        return True
    except Exception as e:
        print(f"Error saving rule {rule.rule_id}: {e}")
        return False


def get_rule(rule_id: str) -> Optional[ResponseRule]:
    """Get a single rule by ID."""
    try:
        response = table.get_item(Key={'rule_id': rule_id})
        if 'Item' in response:
            return ResponseRule.from_item(response['Item'])
    except Exception as e:
        print(f"Error getting rule {rule_id}: {e}")
    return None


def get_rules_for_region(region: str) -> List[ResponseRule]:
    """Get all enabled rules for a region (regional + wildcard)."""
    cache_key = f"region:{region}"
    now = time.time()

    # Check cache
    if cache_key in _rule_cache:
        rules, timestamp = _rule_cache[cache_key]
        if now - timestamp < CACHE_TTL_SECONDS:
            return rules

    try:
        # Query GSI1: (region, event_type)
        # Get regional rules
        response_regional = table.query(
            IndexName='region-event_type-index',
            KeyConditionExpression='region = :region',
            ExpressionAttributeValues={':region': region},
        )

        # Get wildcard rules
        response_wildcard = table.query(
            IndexName='region-event_type-index',
            KeyConditionExpression='region = :region',
            ExpressionAttributeValues={':region': '*'},
        )

        rules = [
            ResponseRule.from_item(item)
            for item in response_regional.get('Items', [])
            + response_wildcard.get('Items', [])
            if item.get('enabled', True)
        ]

        # Sort by priority (lower = higher)
        rules.sort(key=lambda r: r.priority)

        # Cache
        _rule_cache[cache_key] = (rules, now)
        return rules

    except Exception as e:
        print(f"Error querying rules for region {region}: {e}")
        return []


def get_effective_rule(
    region: str, event_type: str
) -> Optional[ResponseRule]:
    """Get the effective rule for a region + event_type combo.

    Returns the highest-priority regional rule, else wildcard rule.
    """
    rules = get_rules_for_region(region)

    # Filter by event_type
    matching = [r for r in rules if r.event_type == event_type]

    # Specific-over-Global: prefer regional rules
    regional = [r for r in matching if r.region == region]
    if regional:
        return regional[0]  # Already sorted by priority

    # Fallback to wildcard
    wildcard = [r for r in matching if r.region == '*']
    if wildcard:
        return wildcard[0]

    return None


def delete_rule(rule_id: str) -> bool:
    """Delete a response rule."""
    try:
        table.delete_item(Key={'rule_id': rule_id})
        _clear_cache()
        return True
    except Exception as e:
        print(f"Error deleting rule {rule_id}: {e}")
        return False


def _clear_cache() -> None:
    """Clear in-memory rule cache."""
    _rule_cache.clear()
