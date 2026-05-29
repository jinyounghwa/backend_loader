import json
import boto3
from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid

try:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except ImportError:
    np = None
    KMeans = None
    StandardScaler = None


class AnomalyClusteringEngine:
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.threats_table = self.dynamodb.Table('guardian-threats')
        self.clusters = {}

    def cluster_threats(self, threats: List[Dict], n_clusters: int = 5) -> Dict:
        """
        위협 목록을 K-Means 클러스터링

        Args:
            threats: 위협 객체 목록
            n_clusters: 클러스터 개수

        Returns:
            {
                'clusters': [...],
                'silhouette_score': float
            }
        """
        if not threats or len(threats) < 2:
            return {'clusters': [], 'silhouette_score': 0.0}

        feature_vectors = self._extract_features(threats)

        if len(feature_vectors) < n_clusters:
            n_clusters = max(1, len(feature_vectors) - 1)

        try:
            if KMeans is None:
                return self._fallback_clustering(threats, n_clusters)

            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(feature_vectors)

            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(scaled_features)

            clusters = self._group_threats_by_cluster(threats, labels, kmeans.cluster_centers_)
            silhouette_score = self._calculate_silhouette_score(scaled_features, labels)

            return {
                'clusters': clusters,
                'silhouette_score': float(silhouette_score),
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                'threat_count': len(threats),
                'cluster_count': len(clusters)
            }
        except Exception:
            return self._fallback_clustering(threats)

    def get_similar_threats(self, threat_id: str, all_threats: List[Dict],
                           similarity_threshold: float = 0.7) -> Dict:
        """특정 위협과 유사한 다른 위협들 반환"""
        threat = next((t for t in all_threats if t.get('threat_id') == threat_id), None)

        if not threat:
            return {'similar_threats': [], 'threat_id': threat_id}

        threat_vector = self._extract_threat_features(threat)
        similar_threats = []

        for other_threat in all_threats:
            if other_threat.get('threat_id') == threat_id:
                continue

            other_vector = self._extract_threat_features(other_threat)
            similarity = self._calculate_cosine_similarity(threat_vector, other_vector)

            if similarity >= similarity_threshold:
                similar_threats.append({
                    'threat_id': other_threat.get('threat_id'),
                    'threat_type': other_threat.get('threat_type'),
                    'severity': other_threat.get('severity', 0),
                    'similarity': float(similarity),
                    'timestamp': other_threat.get('timestamp')
                })

        similar_threats.sort(key=lambda t: t['similarity'], reverse=True)

        return {
            'threat_id': threat_id,
            'similar_threats': similar_threats,
            'threshold': similarity_threshold,
            'count': len(similar_threats)
        }

    def update_cluster_centroids(self, clusters: List[Dict]) -> Dict:
        """클러스터 중심점 업데이트"""
        updated_clusters = []

        for cluster in clusters:
            threat_ids = cluster.get('threats', [])

            if threat_ids:
                avg_severity = cluster.get('avg_severity', 0)
                avg_impact = cluster.get('avg_impact', 0)

                updated_clusters.append({
                    'id': cluster.get('id'),
                    'threats': threat_ids,
                    'centroid': [avg_severity, avg_impact],
                    'cohesion': cluster.get('cohesion', 0.0),
                    'updated_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                })

        return {
            'clusters': updated_clusters,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'cluster_count': len(updated_clusters)
        }

    def _extract_features(self, threats: List[Dict]):
        """위협들로부터 특성 벡터 추출"""
        features = []

        for threat in threats:
            threat_features = self._extract_threat_features(threat)
            features.append(threat_features)

        if np is not None:
            return np.array(features)
        else:
            return features

    def _extract_threat_features(self, threat: Dict) -> List[float]:
        """단일 위협의 특성 벡터 추출"""
        severity = float(threat.get('severity', 0))
        account_risk = float(threat.get('account_risk_score', 0.5))
        event_frequency = float(threat.get('event_frequency', 0))
        resource_impact = float(threat.get('resource_impact_count', 0))
        response_time = float(threat.get('response_time_seconds', 0))
        remediation_rate = float(threat.get('remediation_success_rate', 0.5))

        return [severity, account_risk, event_frequency, resource_impact, response_time, remediation_rate]

    def _group_threats_by_cluster(self, threats: List[Dict], labels, centroids) -> List[Dict]:
        """클러스터별로 위협 그룹화"""
        clusters = {}

        for threat, label in zip(threats, labels):
            if label not in clusters:
                if np is not None and hasattr(centroids[label], 'tolist'):
                    centroid = centroids[label].tolist()
                else:
                    centroid = list(centroids[label]) if label < len(centroids) else []

                clusters[label] = {
                    'id': str(uuid.uuid4()),
                    'threats': [],
                    'threat_ids': [],
                    'centroid': centroid
                }

            clusters[label]['threats'].append(threat)
            clusters[label]['threat_ids'].append(threat.get('threat_id', ''))

        result_clusters = []

        for cluster_id, cluster_data in clusters.items():
            threats_in_cluster = cluster_data['threats']
            representative = max(threats_in_cluster, key=lambda t: t.get('severity', 0))

            avg_severity = np.mean([t.get('severity', 0) for t in threats_in_cluster])
            avg_impact = np.mean([t.get('resource_impact_count', 0) for t in threats_in_cluster])
            cohesion = self._calculate_cluster_cohesion(threats_in_cluster, cluster_data['centroid'])

            result_clusters.append({
                'id': cluster_data['id'],
                'threats': cluster_data['threat_ids'],
                'threat_count': len(threats_in_cluster),
                'centroid': cluster_data['centroid'],
                'cohesion': float(cohesion),
                'avg_severity': float(avg_severity),
                'avg_impact': float(avg_impact),
                'representative_threat': representative.get('threat_id', '')
            })

        return sorted(result_clusters, key=lambda c: c['cohesion'], reverse=True)

    def _calculate_cluster_cohesion(self, threats: List[Dict], centroid: List[float]) -> float:
        """클러스터 응집도 계산"""
        if not threats:
            return 0.0

        distances = []

        for threat in threats:
            threat_vector = self._extract_threat_features(threat)
            if np is not None:
                threat_vector = np.array(threat_vector)
                centroid_vector = np.array(centroid)
                distance = np.linalg.norm(threat_vector - centroid_vector)
            else:
                # Pure Python Euclidean distance
                distance = sum((tv - cv) ** 2 for tv, cv in zip(threat_vector, centroid)) ** 0.5

            distances.append(distance)

        avg_distance = sum(distances) / len(distances) if distances else 0.0
        max_distance = max(distances) if distances else 1.0

        cohesion = 1.0 - (avg_distance / (max_distance + 1.0))
        return float(max(0.0, cohesion))

    def _calculate_silhouette_score(self, features, labels) -> float:
        """실루엣 점수 계산"""
        try:
            if np is not None:
                from sklearn.metrics import silhouette_score
                score = silhouette_score(features, labels)
                return float(score)
        except Exception:
            pass

        # Fallback: return 0.0 for now
        return 0.0

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        if np is not None:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            dot_product = np.dot(vec1, vec2)
        else:
            # Pure Python implementation
            norm1 = sum(v ** 2 for v in vec1) ** 0.5
            norm2 = sum(v ** 2 for v in vec2) ** 0.5
            dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(max(0.0, similarity))

    def _fallback_clustering(self, threats: List[Dict], n_clusters: int = 5) -> Dict:
        """K-Means 사용 불가 시 통계 기반 클러스터링"""
        if len(threats) < 2:
            return {
                'clusters': [{
                    'id': str(uuid.uuid4()),
                    'threats': [t.get('threat_id', '') for t in threats],
                    'threat_count': len(threats),
                    'cohesion': 1.0,
                    'avg_severity': float(threats[0].get('severity', 0)) if threats else 0.0
                }],
                'silhouette_score': 0.0
            }

        sorted_threats = sorted(threats, key=lambda t: t.get('severity', 0), reverse=True)
        # Respect the requested number of clusters
        actual_clusters = min(n_clusters, len(sorted_threats))

        clusters_dict = {}
        for i, threat in enumerate(sorted_threats):
            cluster_id = i % actual_clusters
            if cluster_id not in clusters_dict:
                clusters_dict[cluster_id] = []
            clusters_dict[cluster_id].append(threat)

        clusters = []
        for cluster_id in sorted(clusters_dict.keys()):
            cluster_threats = clusters_dict[cluster_id]

            severity_values = [t.get('severity', 0) for t in cluster_threats]
            if np is not None:
                avg_severity = np.mean(severity_values)
            else:
                avg_severity = sum(severity_values) / len(severity_values) if severity_values else 0.0

            clusters.append({
                'id': str(uuid.uuid4()),
                'threats': [t.get('threat_id', '') for t in cluster_threats],
                'threat_count': len(cluster_threats),
                'cohesion': 0.6,
                'avg_severity': float(avg_severity)
            })

        return {
            'clusters': clusters,
            'silhouette_score': 0.0
        }
