"""Threat Clustering Engine for ML-based threat grouping and feature extraction."""

from typing import List, Dict
import uuid
import math


class ThreatClusteringEngine:
    """ML-based threat clustering and similarity analysis."""

    def __init__(self, audit_logger=None):
        """Initialize clustering engine."""
        self.audit = audit_logger
        self.clusters = []

    def cluster_by_similarity(self, threats: List[Dict], threshold=0.7) -> List[Dict]:
        """K-means-style clustering: group threats by similarity."""
        if not threats:
            return []

        clusters = []
        clustered_indices = set()

        for i, threat in enumerate(threats):
            if i in clustered_indices:
                continue

            cluster = [threat]
            clustered_indices.add(i)

            for j, other_threat in enumerate(threats[i+1:], start=i+1):
                if j in clustered_indices:
                    continue

                # Extract features and calculate distance
                features1 = self.extract_threat_features(threat)
                features2 = self.extract_threat_features(other_threat)
                distance = self.calculate_feature_distance(features1, features2)
                similarity = 1.0 - distance

                if similarity >= threshold:
                    cluster.append(other_threat)
                    clustered_indices.add(j)

            if cluster:
                clusters.append({
                    'cluster_id': str(uuid.uuid4()),
                    'threats': cluster,
                    'cluster_size': len(cluster),
                    'centroid': self._calculate_centroid(cluster),
                    'silhouette_score': self._calculate_silhouette(cluster, threats),
                    'threshold_used': threshold
                })

        self.clusters = clusters
        return clusters

    def extract_threat_features(self, threat: Dict) -> Dict:
        """
        Extract features for clustering:
        - threat_type_vector
        - severity_level
        - affected_resource_types
        - evidence_pattern
        - timeframe_window
        """
        threat_type = threat.get('threat_type', 'unknown')
        severity = threat.get('severity', 5)
        resources = threat.get('affected_resources', [])
        evidence = threat.get('evidence', [])
        detected_at = threat.get('detected_at')

        # Normalize threat type to vector (one-hot encoding)
        threat_type_vector = self._encode_threat_type(threat_type)

        # Extract resource types
        resource_types = [r.get('resource_type', 'unknown') for r in resources]
        resource_vector = self._encode_resource_types(resource_types)

        # Evidence pattern vector
        evidence_vector = self._encode_evidence(evidence)

        return {
            'threat_type': threat_type_vector,
            'severity_level': severity / 10.0,  # Normalize to 0-1
            'affected_resource_types': resource_vector,
            'evidence_pattern': evidence_vector,
            'timeframe_window': self._extract_timeframe(detected_at),
            'account_id': threat.get('account_id', ''),
            'resource_count': len(resources),
            'evidence_count': len(evidence)
        }

    def calculate_feature_distance(self, features1: Dict, features2: Dict) -> float:
        """Calculate distance between threat feature vectors."""
        distances = []

        # Threat type distance (categorical)
        type_dist = self._euclidean_distance(features1['threat_type'], features2['threat_type'])
        distances.append(type_dist * 0.4)  # Weight: 40%

        # Severity distance
        sev_dist = abs(features1['severity_level'] - features2['severity_level'])
        distances.append(sev_dist * 0.2)  # Weight: 20%

        # Resource type distance
        resource_dist = self._euclidean_distance(
            features1['affected_resource_types'],
            features2['affected_resource_types']
        )
        distances.append(resource_dist * 0.15)  # Weight: 15%

        # Evidence pattern distance
        evidence_dist = self._euclidean_distance(
            features1['evidence_pattern'],
            features2['evidence_pattern']
        )
        distances.append(evidence_dist * 0.15)  # Weight: 15%

        # Timeframe distance
        time_dist = abs(features1['timeframe_window'] - features2['timeframe_window']) / 60.0
        distances.append(min(time_dist, 1.0) * 0.1)  # Weight: 10%

        # Account distance (if same account, 0, else 1)
        account_dist = 0.0 if features1['account_id'] == features2['account_id'] else 0.2

        return min(sum(distances) + account_dist, 1.0)

    def merge_similar_clusters(self, clusters: List[Dict], merge_threshold=0.8) -> List[Dict]:
        """Merge clusters that are too similar."""
        if not clusters:
            return []

        merged = []
        merged_indices = set()

        for i, cluster1 in enumerate(clusters):
            if i in merged_indices:
                continue

            merged_cluster = cluster1.copy()
            merged_cluster['threats'] = cluster1['threats'].copy()

            for j, cluster2 in enumerate(clusters[i+1:], start=i+1):
                if j in merged_indices:
                    continue

                # Calculate cluster similarity based on centroids
                similarity = 1.0 - self._euclidean_distance(
                    cluster1['centroid'],
                    cluster2['centroid']
                )

                if similarity >= merge_threshold:
                    merged_cluster['threats'].extend(cluster2['threats'])
                    merged_cluster['cluster_size'] = len(merged_cluster['threats'])
                    merged_indices.add(j)

            merged.append(merged_cluster)

        return merged

    def get_cluster_statistics(self) -> Dict:
        """Get statistics about threat clusters."""
        if not self.clusters:
            return {
                'total_clusters': 0,
                'total_threats': 0,
                'avg_cluster_size': 0.0,
                'max_cluster_size': 0,
                'min_cluster_size': 0,
                'cluster_details': []
            }

        cluster_sizes = [c['cluster_size'] for c in self.clusters]
        total_threats = sum(cluster_sizes)

        return {
            'total_clusters': len(self.clusters),
            'total_threats': total_threats,
            'avg_cluster_size': total_threats / len(self.clusters) if self.clusters else 0,
            'max_cluster_size': max(cluster_sizes) if cluster_sizes else 0,
            'min_cluster_size': min(cluster_sizes) if cluster_sizes else 0,
            'cluster_details': [
                {
                    'cluster_id': c['cluster_id'],
                    'size': c['cluster_size'],
                    'silhouette_score': c.get('silhouette_score', 0.0)
                }
                for c in self.clusters
            ]
        }

    def _calculate_centroid(self, threats: List[Dict]) -> List[float]:
        """Calculate centroid of threat cluster."""
        if not threats:
            return []

        feature_sum = {}
        for threat in threats:
            features = self.extract_threat_features(threat)
            for key, value in features.items():
                if isinstance(value, (int, float)):
                    if key not in feature_sum:
                        feature_sum[key] = 0
                    feature_sum[key] += value

        centroid = []
        for key in sorted(feature_sum.keys()):
            centroid.append(feature_sum[key] / len(threats))

        return centroid

    def _calculate_silhouette(self, cluster: List[Dict], all_threats: List[Dict]) -> float:
        """Calculate silhouette coefficient for cluster quality."""
        if len(cluster) <= 1:
            return 0.0

        # Simplified silhouette: measure cohesion vs separation
        intra_distances = []
        for i, threat1 in enumerate(cluster):
            for threat2 in cluster[i+1:]:
                features1 = self.extract_threat_features(threat1)
                features2 = self.extract_threat_features(threat2)
                dist = self.calculate_feature_distance(features1, features2)
                intra_distances.append(dist)

        avg_intra = sum(intra_distances) / len(intra_distances) if intra_distances else 0.0

        # Average distance to threats outside cluster
        inter_distances = []
        for threat in cluster:
            for other in all_threats:
                if other not in cluster:
                    features1 = self.extract_threat_features(threat)
                    features2 = self.extract_threat_features(other)
                    dist = self.calculate_feature_distance(features1, features2)
                    inter_distances.append(dist)

        avg_inter = sum(inter_distances) / len(inter_distances) if inter_distances else 1.0

        if avg_inter == 0:
            return 0.0

        silhouette = (avg_inter - avg_intra) / max(avg_intra, avg_inter)
        return max(0.0, silhouette)

    def _encode_threat_type(self, threat_type: str) -> List[float]:
        """Encode threat type as vector."""
        common_types = [
            'Unauthorized EC2',
            'Public Bucket',
            'Unauthorized Access',
            'Lateral Movement',
            'Credential Compromise',
            'Network Breach'
        ]

        vector = [1.0 if threat_type == t else 0.0 for t in common_types]
        if len(vector) < 6:
            vector.extend([0.0] * (6 - len(vector)))

        return vector[:6]

    def _encode_resource_types(self, resource_types: List[str]) -> List[float]:
        """Encode resource types as vector."""
        common_resources = ['ec2', 's3', 'iam', 'network', 'lambda', 'rds']
        vector = [1.0 if r in common_resources else 0.0 for r in resource_types]

        return vector[:len(common_resources)]

    def _encode_evidence(self, evidence: List[str]) -> List[float]:
        """Encode evidence patterns as vector."""
        common_evidence = [
            'suspicious_login',
            'public_access',
            'unauthorized_api',
            'credential_exposure',
            'cross_account_access',
            'data_exposure'
        ]

        vector = [1.0 if e in common_evidence else 0.0 for e in evidence]
        return vector[:len(common_evidence)]

    def _extract_timeframe(self, detected_at) -> float:
        """Extract timeframe as numeric value (hours from now)."""
        if not detected_at:
            return 0.0

        from datetime import datetime
        if isinstance(detected_at, str):
            try:
                dt = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
            except:
                return 0.0
        else:
            dt = detected_at

        now = datetime.utcnow()
        if isinstance(dt, type(now)):
            diff = (now - dt).total_seconds() / 3600.0
        else:
            diff = 0.0

        return diff

    def _euclidean_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate Euclidean distance between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        # Pad vectors to same length
        max_len = max(len(vec1), len(vec2))
        v1 = vec1 + [0.0] * (max_len - len(vec1))
        v2 = vec2 + [0.0] * (max_len - len(vec2))

        sum_squares = sum((a - b) ** 2 for a, b in zip(v1, v2))
        return math.sqrt(sum_squares) / max(max_len, 1)
