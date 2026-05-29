"""CloudTrail events storage and retrieval."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class CloudTrailEventStorage:
    """Store and retrieve CloudTrail events from DynamoDB."""

    def __init__(self, dynamodb_table=None):
        """Initialize storage.
        
        Args:
            dynamodb_table: DynamoDB table resource
        """
        self.table = dynamodb_table
        self.in_memory_events = []

    def store_event(self, event: Dict[str, Any]) -> bool:
        """Store a CloudTrail event.
        
        Args:
            event: Event to store
            
        Returns:
            True if successful
        """
        try:
            if self.table:
                self.table.put_item(Item={
                    'event_id': event.get('event_id'),
                    'event_time': event.get('event_time'),
                    'event_name': event.get('event_name'),
                    'username': event.get('username'),
                    'threat_score': event.get('threat_score', 0),
                    'stored_at': datetime.now(timezone.utc).isoformat(),
                })
            else:
                self.in_memory_events.append(event)
            
            logger.info(f"Stored event: {event.get('event_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            return False

    def query_events(
        self,
        username: Optional[str] = None,
        event_name: Optional[str] = None,
        min_threat_score: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query events with filters.
        
        Args:
            username: Filter by username
            event_name: Filter by event name
            min_threat_score: Minimum threat score
            
        Returns:
            List of matching events
        """
        results = self.in_memory_events
        
        if username:
            results = [e for e in results if e.get('username') == username]
        
        if event_name:
            results = [e for e in results if e.get('event_name') == event_name]
        
        if min_threat_score > 0:
            results = [
                e for e in results
                if e.get('threat_score', 0) >= min_threat_score
            ]
        
        return results

    def get_high_risk_events(self) -> List[Dict[str, Any]]:
        """Get all high-risk events (score >= 60).
        
        Returns:
            List of high-risk events
        """
        return self.query_events(min_threat_score=60)

    def get_user_activity(self, username: str) -> List[Dict[str, Any]]:
        """Get all events for a specific user.
        
        Args:
            username: Username to query
            
        Returns:
            List of user events
        """
        return self.query_events(username=username)
