"""CloudTrail event processing for real-time anomaly detection."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class CloudTrailEventProcessor:
    """Parse and process CloudTrail events."""

    def __init__(self):
        """Initialize event processor."""
        self.processed_events = []

    def parse_event(self, raw_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw CloudTrail event.
        
        Args:
            raw_event: Raw CloudTrail event dict
            
        Returns:
            Parsed event dict or None
        """
        try:
            event = {
                'event_id': raw_event.get('eventID'),
                'event_name': raw_event.get('eventName'),
                'event_time': raw_event.get('eventTime'),
                'username': raw_event.get('userIdentity', {}).get('principalId'),
                'source_ip': raw_event.get('sourceIPAddress'),
                'user_agent': raw_event.get('userAgent'),
                'aws_region': raw_event.get('awsRegion'),
                'event_source': raw_event.get('eventSource'),
                'request_params': raw_event.get('requestParameters', {}),
                'response_elements': raw_event.get('responseElements', {}),
                'error_code': raw_event.get('errorCode'),
                'error_message': raw_event.get('errorMessage'),
                'raw': raw_event,
            }
            return event
        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            return None

    def process_batch(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch of CloudTrail events.
        
        Args:
            events: List of raw CloudTrail events
            
        Returns:
            List of parsed events
        """
        processed = []
        for raw_event in events:
            parsed = self.parse_event(raw_event)
            if parsed:
                processed.append(parsed)
        
        self.processed_events.extend(processed)
        return processed

    def get_events_by_type(
        self, event_type: str, events: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """Get events filtered by type.
        
        Args:
            event_type: Event name to filter by
            events: Optional list of events (uses processed if not provided)
            
        Returns:
            Filtered event list
        """
        event_list = events or self.processed_events
        return [
            event for event in event_list
            if event.get('event_name') == event_type
        ]

    def get_events_by_username(
        self, username: str, events: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """Get events filtered by username.
        
        Args:
            username: Username to filter by
            events: Optional list of events
            
        Returns:
            Filtered event list
        """
        event_list = events or self.processed_events
        return [
            event for event in event_list
            if event.get('username') == username
        ]

    def get_failed_events(
        self, events: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """Get all failed API calls.
        
        Args:
            events: Optional list of events
            
        Returns:
            List of failed events
        """
        event_list = events or self.processed_events
        return [
            event for event in event_list
            if event.get('error_code')
        ]

    def correlate_events(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate related events.
        
        Args:
            events: List of events to correlate
            
        Returns:
            List of correlated event groups
        """
        correlations = {}
        
        for event in events:
            username = event.get('username')
            if not username:
                continue
            
            if username not in correlations:
                correlations[username] = {
                    'username': username,
                    'events': [],
                    'event_count': 0,
                    'failed_count': 0,
                }
            
            correlations[username]['events'].append(event)
            correlations[username]['event_count'] += 1
            
            if event.get('error_code'):
                correlations[username]['failed_count'] += 1
        
        return list(correlations.values())
