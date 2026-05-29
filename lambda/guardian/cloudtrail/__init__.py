"""CloudTrail event processing for threat detection."""

from .event_processor import CloudTrailEventProcessor
from .pattern_matcher import PatternMatcher
from .threat_scorer import ThreatScorer

__all__ = ['CloudTrailEventProcessor', 'PatternMatcher', 'ThreatScorer']
