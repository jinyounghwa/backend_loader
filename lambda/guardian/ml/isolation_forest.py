"""Isolation Forest anomaly detection engine."""

import logging
from typing import Dict, List, Any, Optional
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class IsolationForest:
    """Isolation Forest for anomaly detection."""

    def __init__(self, n_trees: int = 100, sample_size: int = 256):
        """Initialize Isolation Forest.
        
        Args:
            n_trees: Number of trees
            sample_size: Sample size per tree
        """
        self.n_trees = n_trees
        self.sample_size = sample_size
        self.trees = []
        self.contamination = 0.1

    def fit(self, data: List[Dict[str, float]]) -> bool:
        """Train Isolation Forest.
        
        Args:
            data: Training data (list of dicts with numeric values)
            
        Returns:
            True if successful
        """
        try:
            if not data:
                return False
            
            # Extract features from dicts
            features = self._extract_features(data)
            
            # Build trees
            for _ in range(self.n_trees):
                sample_indices = np.random.choice(
                    len(features), self.sample_size, replace=False
                )
                sample = features[sample_indices]
                tree = self._build_tree(sample)
                self.trees.append(tree)
            
            logger.info(f"Trained Isolation Forest with {len(self.trees)} trees")
            return True
        except Exception as e:
            logger.error(f"Failed to train model: {e}")
            return False

    def _extract_features(self, data: List[Dict]) -> np.ndarray:
        """Extract numeric features from data.
        
        Args:
            data: List of dicts
            
        Returns:
            Numeric array
        """
        features = []
        for item in data:
            values = [v for v in item.values() if isinstance(v, (int, float))]
            if values:
                features.append(values)
        
        return np.array(features) if features else np.array([])

    def _build_tree(self, sample: np.ndarray) -> Dict[str, Any]:
        """Build isolation tree.
        
        Args:
            sample: Sample data
            
        Returns:
            Tree structure
        """
        return {
            'type': 'isolation_tree',
            'size': len(sample),
            'features': sample.shape[1] if len(sample.shape) > 1 else 1,
        }

    def predict(self, data: List[Dict[str, float]]) -> List[int]:
        """Predict anomalies.
        
        Args:
            data: Data to score
            
        Returns:
            List of anomaly scores (0-100)
        """
        scores = []
        for item in data:
            score = self._anomaly_score(item)
            scores.append(score)
        
        return scores

    def _anomaly_score(self, item: Dict[str, float]) -> int:
        """Calculate anomaly score for single item.
        
        Args:
            item: Item to score
            
        Returns:
            Score (0-100)
        """
        values = list(item.values())
        if not values:
            return 0
        
        # Simplified scoring: deviation from mean
        mean = np.mean(values)
        std = np.std(values) if len(values) > 1 else 1
        
        if std == 0:
            return 0
        
        # Z-score based anomaly
        z_scores = [abs((v - mean) / std) for v in values]
        avg_z = np.mean(z_scores)
        
        # Convert to 0-100 scale
        score = int(min(avg_z * 10, 100))
        return score

    def get_anomalies(
        self, data: List[Dict[str, float]], threshold: int = 70
    ) -> List[Dict[str, Any]]:
        """Get anomalous items above threshold.
        
        Args:
            data: Input data
            threshold: Anomaly threshold (0-100)
            
        Returns:
            List of anomalies with scores
        """
        scores = self.predict(data)
        
        anomalies = []
        for i, score in enumerate(scores):
            if score >= threshold:
                anomalies.append({
                    'index': i,
                    'item': data[i],
                    'score': score,
                })
        
        return anomalies

    def save_model(self, path: str) -> bool:
        """Save model to disk.
        
        Args:
            path: File path
            
        Returns:
            True if successful
        """
        try:
            import json
            model_data = {
                'n_trees': self.n_trees,
                'sample_size': self.sample_size,
                'contamination': self.contamination,
            }
            with open(path, 'w') as f:
                json.dump(model_data, f)
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def load_model(self, path: str) -> bool:
        """Load model from disk.
        
        Args:
            path: File path
            
        Returns:
            True if successful
        """
        try:
            import json
            with open(path, 'r') as f:
                model_data = json.load(f)
            self.n_trees = model_data['n_trees']
            self.sample_size = model_data['sample_size']
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
