"""NLP-based threat analysis: Text generation, root cause analysis, sentiment"""

import re
from typing import Dict, List, Tuple
from datetime import datetime


class ThreatTextGenerator:
    """Generate natural language descriptions from threat data."""

    def __init__(self):
        self.threat_templates = {
            'EC2_UNAUTHORIZED_REGION': 'Unauthorized EC2 instance detected in region {region}',
            'S3_PUBLIC_BUCKET': 'Public S3 bucket "{bucket_name}" detected',
            'HIGH_COST': 'Cost spike detected: ${amount} spent (${threshold} threshold)',
            'AUTH_FAILURE_SPIKE': '{count} authentication failures detected',
            'SECURITY_GROUP_OPEN': 'Security group {sg_id} has unrestricted access (0.0.0.0/0)',
            'UNENCRYPTED_DB': 'Database {db_id} is not encrypted',
            'IAM_PRIVILEGE_ESCALATION': 'Potential privilege escalation by {user}',
            'CLOUDTRAIL_DISABLED': 'CloudTrail is disabled for account {account_id}'
        }

    def generate(self, threat: Dict) -> str:
        """Generate threat text from threat data."""
        threat_type = threat.get('type', 'UNKNOWN')

        if threat_type in self.threat_templates:
            template = self.threat_templates[threat_type]
            try:
                return template.format(**threat)
            except KeyError:
                return f"Threat detected: {threat_type}"

        return f"Threat detected: {threat_type}"

    def enrich_description(self, text: str, threat: Dict) -> str:
        """Enrich description with additional context."""
        lines = [text]

        if 'instance_id' in threat:
            lines.append(f"Instance: {threat['instance_id']}")
        if 'severity' in threat:
            lines.append(f"Severity: {threat['severity']}/10")
        if 'timestamp' in threat:
            lines.append(f"Detected: {threat['timestamp']}")

        return " | ".join(lines)


class RootCauseAnalyzer:
    """Analyze and infer root causes of threats."""

    def __init__(self):
        self.cause_patterns = {
            'EC2_UNAUTHORIZED_REGION': [
                ('manual_deployment', 'Developer manually deployed to unauthorized region'),
                ('automation_error', 'Automation/CI-CD deployed to wrong region'),
                ('misconfiguration', 'Infrastructure code has wrong region configured')
            ],
            'S3_PUBLIC_BUCKET': [
                ('acl_misconfiguration', 'Bucket ACL incorrectly set to public-read'),
                ('policy_overpermissive', 'Bucket policy allows public access'),
                ('accidental_change', 'Recent change made bucket public unintentionally')
            ],
            'HIGH_COST': [
                ('new_resource', 'New resource created'),
                ('load_spike', 'Unexpected traffic spike'),
                ('misconfiguration', 'Resource incorrectly configured for high capacity'),
                ('unused_resource', 'Unused resource still running')
            ]
        }

    def analyze(self, threat: Dict) -> Dict:
        """Analyze root cause of threat."""
        threat_type = threat.get('type', 'UNKNOWN')

        if threat_type not in self.cause_patterns:
            return {
                'root_cause': 'Unknown cause',
                'confidence': 0.3,
                'explanation': 'Insufficient data for root cause analysis'
            }

        patterns = self.cause_patterns[threat_type]

        # Match threat details to cause patterns
        best_match = patterns[0]
        confidence = 0.5

        # Increase confidence if we have specific evidence
        if 'changed_by' in threat:
            confidence += 0.2
        if 'time_since_change' in threat:
            confidence = min(confidence + 0.1, 0.95)

        return {
            'root_cause': best_match[0],
            'cause_name': best_match[1],
            'confidence': confidence,
            'explanation': best_match[1]
        }


class SentimentAnalyzer:
    """Analyze threat severity and sentiment."""

    def __init__(self):
        self.severity_keywords = {
            'critical': ['critical', 'emergency', 'urgent', 'breach', 'compromised', 'exploited'],
            'high': ['high', 'severe', 'serious', 'dangerous', 'public', 'unauthorized'],
            'medium': ['medium', 'moderate', 'notable', 'misconfigured', 'detected'],
            'low': ['low', 'minor', 'informational', 'warning', 'attention']
        }

    def analyze_severity(self, threat_text: str) -> Dict:
        """Analyze severity from threat text."""
        text_lower = threat_text.lower()

        # Check for severity keywords
        for severity, keywords in self.severity_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    severity_score = {
                        'critical': 9,
                        'high': 7,
                        'medium': 5,
                        'low': 2
                    }[severity]

                    return {
                        'severity': severity,
                        'score': severity_score,
                        'sentiment': 'negative',
                        'confidence': 0.75
                    }

        return {
            'severity': 'medium',
            'score': 5,
            'sentiment': 'neutral',
            'confidence': 0.5
        }

    def calculate_sentiment_score(self, threat: Dict) -> float:
        """Calculate sentiment score (-1.0 to 1.0, where -1 is very negative)."""
        severity_score = threat.get('severity', 5) / 10.0

        # Threat = negative sentiment
        return -severity_score


class ThreatNLPPipeline:
    """Complete NLP pipeline for threat analysis."""

    def __init__(self):
        self.generator = ThreatTextGenerator()
        self.analyzer = RootCauseAnalyzer()
        self.sentiment = SentimentAnalyzer()

    def analyze_threat(self, threat: Dict) -> Dict:
        """Complete analysis pipeline for threat."""
        # Generate text
        text = self.generator.generate(threat)
        enriched_text = self.generator.enrich_description(text, threat)

        # Analyze root cause
        root_cause = self.analyzer.analyze(threat)

        # Analyze sentiment
        sentiment = self.sentiment.analyze_severity(enriched_text)

        return {
            'text': text,
            'enriched_text': enriched_text,
            'root_cause': root_cause,
            'sentiment': sentiment,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }


def extract_key_phrases(text: str) -> List[str]:
    """Extract key phrases from threat text."""
    # Simple keyword extraction
    keywords = re.findall(r'\b[A-Z][A-Za-z_]*\b', text)
    return list(set(keywords))


def calculate_text_complexity(text: str) -> float:
    """Calculate complexity of threat text (0-1)."""
    words = text.split()
    avg_word_length = sum(len(w) for w in words) / len(words) if words else 0

    # Normalize to 0-1 range
    return min(avg_word_length / 15.0, 1.0)
