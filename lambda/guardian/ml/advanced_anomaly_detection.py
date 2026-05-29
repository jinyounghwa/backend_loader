"""Advanced anomaly detection: GMM + LOF"""

import json
import math
from typing import List, Dict, Tuple
import numpy as np


class GaussianMixtureDetector:
    """Gaussian Mixture Model for multi-modal anomaly detection."""

    def __init__(self, n_components: int = 3):
        self.n_components = n_components
        self.means = []
        self.covariances = []
        self.weights = []

    def fit(self, data: List[Dict]) -> None:
        """Fit GMM on data (simplified EM algorithm)."""
        if not data:
            return

        # Extract numeric values
        values = []
        for item in data:
            if isinstance(item, dict):
                val = item.get('value', 0)
            else:
                val = float(item) if item else 0
            values.append(val)

        values = np.array(values)

        # Initialize: k-means++ centers
        if len(values) < self.n_components:
            self.n_components = len(values)

        indices = np.random.choice(len(values), self.n_components, replace=False)
        self.means = [float(values[i]) for i in indices]

        # Simple EM: assign to nearest mean
        for _ in range(5):  # 5 iterations
            # E-step: assign points
            assignments = [None] * len(values)
            for i, v in enumerate(values):
                distances = [abs(v - m) for m in self.means]
                assignments[i] = distances.index(min(distances))

            # M-step: update means
            new_means = []
            for k in range(self.n_components):
                cluster_vals = [values[i] for i in range(len(values)) if assignments[i] == k]
                if cluster_vals:
                    new_means.append(float(np.mean(cluster_vals)))
                else:
                    new_means.append(self.means[k])
            self.means = new_means

        # Calculate covariances and weights
        self.covariances = [float(np.std(values)) for _ in range(self.n_components)]
        self.weights = [1.0 / self.n_components] * self.n_components

    def predict(self, data: List[Dict]) -> List[float]:
        """Predict anomaly scores (0-100)."""
        if not self.means:
            return [0.0] * len(data)

        scores = []
        for item in data:
            if isinstance(item, dict):
                value = item.get('value', 0)
            else:
                value = float(item) if item else 0

            # Calculate likelihood for each component
            likelihoods = []
            for mean, cov, weight in zip(self.means, self.covariances, self.weights):
                cov = max(cov, 0.1)  # Avoid division by zero
                likelihood = weight * math.exp(-0.5 * ((value - mean) / cov) ** 2) / (cov * math.sqrt(2 * math.pi))
                likelihoods.append(likelihood)

            # Anomaly score: inverse of max likelihood
            max_likelihood = max(likelihoods) if likelihoods else 0.001
            score = max(0.0, min(100.0, 100.0 * (1.0 - max_likelihood)))
            scores.append(score)

        return scores


class LocalOutlierDetector:
    """Local Outlier Factor for density-based anomaly detection."""

    def __init__(self, k: int = 5):
        self.k = k
        self.data = []
        self.local_densities = []

    def fit(self, data: List[Dict]) -> None:
        """Fit LOF model."""
        self.data = []
        for item in data:
            if isinstance(item, dict):
                val = item.get('value', 0)
            else:
                val = float(item) if item else 0
            self.data.append(val)

    def predict(self, data: List[Dict]) -> List[float]:
        """Predict anomaly scores using local outlier factor."""
        if not self.data:
            return [0.0] * len(data)

        scores = []
        for item in data:
            if isinstance(item, dict):
                value = item.get('value', 0)
            else:
                value = float(item) if item else 0

            # Calculate k-distance
            distances = [abs(value - d) for d in self.data]
            distances.sort()
            k_distance = distances[min(self.k, len(distances) - 1)]

            # Local reachability density
            reachability_distances = []
            for i, d in enumerate(distances[:self.k]):
                neighbor_distances = [abs(self.data[j] - self.data[i]) for j in range(len(self.data))]
                neighbor_distances.sort()
                neighbor_k_distance = neighbor_distances[min(self.k, len(neighbor_distances) - 1)]
                reach_dist = max(d, neighbor_k_distance)
                reachability_distances.append(reach_dist)

            lrd = self.k / max(sum(reachability_distances), 0.1) if reachability_distances else 1.0
            lrd = max(lrd, 0.001)

            # Calculate local reachability density of neighbors
            avg_neighbor_lrd = 0.0
            neighbor_count = 0
            for i, d in enumerate(distances[:self.k]):
                neighbor_distances = [abs(self.data[j] - self.data[i]) for j in range(len(self.data))]
                neighbor_distances.sort()
                neighbor_reachability = []
                for neighbor_d in neighbor_distances[:self.k]:
                    neighbor_distances_2 = [abs(self.data[j] - self.data[i]) for j in range(len(self.data))]
                    neighbor_distances_2.sort()
                    neighbor_k_dist_2 = neighbor_distances_2[min(self.k, len(neighbor_distances_2) - 1)]
                    neighbor_reachability.append(max(neighbor_d, neighbor_k_dist_2))

                neighbor_lrd = self.k / max(sum(neighbor_reachability), 0.1) if neighbor_reachability else 1.0
                avg_neighbor_lrd += neighbor_lrd
                neighbor_count += 1

            if neighbor_count > 0:
                avg_neighbor_lrd /= neighbor_count

            # LOF score
            lof = avg_neighbor_lrd / lrd if lrd > 0 else 1.0
            # Convert LOF to 0-100 scale
            score = max(0.0, min(100.0, (lof - 1.0) * 50))
            scores.append(score)

        return scores


class AnomalyDetectorEnsemble:
    """Ensemble of multiple anomaly detectors."""

    def __init__(self):
        self.gmm = GaussianMixtureDetector(n_components=3)
        self.lof = LocalOutlierDetector(k=5)

    def fit(self, data: List[Dict]) -> None:
        """Train all detectors."""
        self.gmm.fit(data)
        self.lof.fit(data)

    def predict(self, data: List[Dict]) -> List[float]:
        """Ensemble prediction (average of detectors)."""
        gmm_scores = self.gmm.predict(data)
        lof_scores = self.lof.predict(data)

        ensemble_scores = []
        for i in range(len(data)):
            # Average scores with GMM weight 0.6, LOF weight 0.4
            score = 0.6 * gmm_scores[i] + 0.4 * lof_scores[i]
            ensemble_scores.append(score)

        return ensemble_scores

    def get_anomalies(self, data: List[Dict], threshold: int = 70) -> List[Dict]:
        """Get anomalies above threshold."""
        scores = self.predict(data)
        anomalies = []

        for i, (item, score) in enumerate(zip(data, scores)):
            if score >= threshold:
                anomaly = item.copy() if isinstance(item, dict) else {'value': item}
                anomaly['score'] = score
                anomaly['anomaly_index'] = i
                anomalies.append(anomaly)

        return sorted(anomalies, key=lambda x: x['score'], reverse=True)

    def get_confidence(self, score: float) -> float:
        """Get confidence level (0-1) for anomaly score."""
        return min(score / 100.0, 1.0)
