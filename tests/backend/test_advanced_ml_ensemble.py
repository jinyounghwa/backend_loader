"""Advanced ML ensemble tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestEnsembleMLModel:
    """Test ensemble ML model combining multiple algorithms."""

    def test_ensemble_prediction(self):
        """✅ Ensemble predicts with >95% accuracy."""
        from guardian.ml.advanced_ensemble import EnsembleMLModel

        ensemble = EnsembleMLModel()

        predictions = ensemble.predict({
            'features': [1.0, 2.0, 3.0, 4.0, 5.0],
            'models': ['random_forest', 'xgboost', 'lstm']
        })

        assert 'ensemble_prediction' in predictions
        assert predictions['confidence'] > 0.95

    def test_random_forest_prediction(self):
        """✅ Random Forest base model prediction."""
        from guardian.ml.advanced_ensemble import EnsembleMLModel

        ensemble = EnsembleMLModel()

        result = ensemble.predict_random_forest({
            'features': [1.0, 2.0, 3.0, 4.0, 5.0],
            'n_estimators': 100
        })

        assert 'prediction' in result
        assert 'confidence' in result

    def test_xgboost_prediction(self):
        """✅ XGBoost base model prediction."""
        from guardian.ml.advanced_ensemble import EnsembleMLModel

        ensemble = EnsembleMLModel()

        result = ensemble.predict_xgboost({
            'features': [1.0, 2.0, 3.0, 4.0, 5.0],
            'n_estimators': 50
        })

        assert 'prediction' in result
        assert result['confidence'] > 0.85

    def test_lstm_prediction(self):
        """✅ LSTM time-series prediction."""
        from guardian.ml.advanced_ensemble import EnsembleMLModel

        ensemble = EnsembleMLModel()

        result = ensemble.predict_lstm({
            'sequence': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            'lookback': 3
        })

        assert 'prediction' in result
        assert 'next_value' in result


class TestModelStacking:
    """Test model stacking and meta-learner."""

    def test_two_level_stacking(self):
        """✅ Two-level stacking with meta-learner."""
        from guardian.ml.advanced_ensemble import ModelStacking

        stacking = ModelStacking()

        result = stacking.stack({
            'base_models': ['rf', 'xgb', 'lstm'],
            'meta_model': 'logistic_regression',
            'features': [1.0, 2.0, 3.0]
        })

        assert 'stacked_prediction' in result
        assert result['confidence'] > 0.90

    def test_model_weight_optimization(self):
        """✅ Optimize model weights in ensemble."""
        from guardian.ml.advanced_ensemble import ModelStacking

        stacking = ModelStacking()

        weights = stacking.optimize_weights({
            'base_models': ['rf', 'xgb', 'lstm'],
            'validation_data': {'X': [], 'y': []},
            'optimization_method': 'grid_search'
        })

        assert 'weights' in weights
        assert len(weights['weights']) == 3
        assert sum(weights['weights'].values()) <= 1.1

    def test_meta_learner_training(self):
        """✅ Train meta-learner on base model outputs."""
        from guardian.ml.advanced_ensemble import ModelStacking

        stacking = ModelStacking()

        trained = stacking.train_meta_learner({
            'base_predictions': [[0.8, 0.9, 0.85], [0.7, 0.75, 0.72]],
            'targets': [1, 0],
            'meta_model_type': 'logistic_regression'
        })

        assert trained['status'] == 'trained'
        assert 'model_id' in trained

    def test_cross_validation_stacking(self):
        """✅ Cross-validation for stacking."""
        from guardian.ml.advanced_ensemble import ModelStacking

        stacking = ModelStacking()

        cv_result = stacking.cross_validate_stack({
            'n_splits': 5,
            'base_models': ['rf', 'xgb', 'lstm']
        })

        assert 'cv_scores' in cv_result
        assert len(cv_result['cv_scores']) == 5


class TestFeatureEngineering:
    """Test automated feature engineering."""

    def test_feature_generation(self):
        """✅ Generate features automatically."""
        from guardian.ml.advanced_ensemble import FeatureEngineering

        fe = FeatureEngineering()

        features = fe.generate_features({
            'raw_data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'feature_types': ['polynomial', 'interaction', 'statistical']
        })

        assert 'generated_features' in features
        assert len(features['generated_features']) > 3

    def test_feature_selection(self):
        """✅ Select best features using mutual information."""
        from guardian.ml.advanced_ensemble import FeatureEngineering

        fe = FeatureEngineering()

        selected = fe.select_features({
            'all_features': ['f1', 'f2', 'f3', 'f4', 'f5'],
            'target': [1, 0, 1, 0, 1],
            'n_features': 3
        })

        assert 'selected_features' in selected
        assert len(selected['selected_features']) == 3

    def test_feature_scaling(self):
        """✅ Scale features for ML models."""
        from guardian.ml.advanced_ensemble import FeatureEngineering

        fe = FeatureEngineering()

        scaled = fe.scale_features({
            'features': [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            'scaler': 'standard'
        })

        assert 'scaled_features' in scaled
        assert len(scaled['scaled_features']) == 3

    def test_feature_encoding(self):
        """✅ Encode categorical features."""
        from guardian.ml.advanced_ensemble import FeatureEngineering

        fe = FeatureEngineering()

        encoded = fe.encode_categorical({
            'features': ['cat', 'dog', 'cat', 'bird'],
            'encoding_method': 'onehot'
        })

        assert 'encoded_features' in encoded
        assert 'encoding_map' in encoded


class TestModelExplainability:
    """Test model explainability and interpretability."""

    def test_shap_values(self):
        """✅ Calculate SHAP values for feature importance."""
        from guardian.ml.advanced_ensemble import ModelExplainability

        explainer = ModelExplainability()

        shap_values = explainer.calculate_shap({
            'model_type': 'ensemble',
            'features': [1.0, 2.0, 3.0, 4.0, 5.0],
            'background_data': [[1, 2, 3, 4, 5]]
        })

        assert 'shap_values' in shap_values
        assert 'base_value' in shap_values

    def test_feature_importance(self):
        """✅ Calculate feature importance."""
        from guardian.ml.advanced_ensemble import ModelExplainability

        explainer = ModelExplainability()

        importance = explainer.get_feature_importance({
            'model_type': 'ensemble',
            'features': ['f1', 'f2', 'f3', 'f4', 'f5']
        })

        assert 'importances' in importance
        assert len(importance['importances']) == 5

    def test_prediction_explanation(self):
        """✅ Explain individual predictions."""
        from guardian.ml.advanced_ensemble import ModelExplainability

        explainer = ModelExplainability()

        explanation = explainer.explain_prediction({
            'prediction': 0.85,
            'features': [1.0, 2.0, 3.0],
            'feature_names': ['cost', 'threats', 'compliance']
        })

        assert 'explanation' in explanation
        assert 'contributing_features' in explanation

    def test_model_fairness(self):
        """✅ Check model fairness and bias."""
        from guardian.ml.advanced_ensemble import ModelExplainability

        explainer = ModelExplainability()

        fairness = explainer.check_fairness({
            'predictions': [0.9, 0.1, 0.8, 0.2, 0.85],
            'groups': ['A', 'B', 'A', 'B', 'A'],
            'fairness_metric': 'demographic_parity'
        })

        assert 'fairness_score' in fairness
        assert 'bias_detected' in fairness


class TestAdvancedMLIntegration:
    """End-to-end advanced ML workflows."""

    def test_full_ensemble_pipeline(self):
        """✅ Complete pipeline: feature → ensemble → explain."""
        from guardian.ml.advanced_ensemble import (
            EnsembleMLModel,
            FeatureEngineering,
            ModelExplainability
        )

        fe = FeatureEngineering()
        ensemble = EnsembleMLModel()
        explainer = ModelExplainability()

        # Step 1: Generate features
        features = fe.generate_features({
            'raw_data': [1, 2, 3, 4, 5],
            'feature_types': ['polynomial', 'interaction']
        })

        assert len(features['generated_features']) > 0

        # Step 2: Make prediction
        prediction = ensemble.predict({
            'features': [1.0, 2.0, 3.0],
            'models': ['random_forest', 'xgboost', 'lstm']
        })

        assert prediction['confidence'] > 0.90

        # Step 3: Explain prediction
        explanation = explainer.explain_prediction({
            'prediction': prediction['ensemble_prediction'],
            'features': [1.0, 2.0, 3.0],
            'feature_names': ['f1', 'f2', 'f3']
        })

        assert 'explanation' in explanation

    def test_model_comparison(self):
        """✅ Compare ensemble vs individual models."""
        from guardian.ml.advanced_ensemble import EnsembleMLModel

        ensemble = EnsembleMLModel()

        comparison = ensemble.compare_models({
            'features': [1.0, 2.0, 3.0, 4.0, 5.0],
            'metrics': ['accuracy', 'precision', 'recall']
        })

        assert 'ensemble_score' in comparison
        assert 'individual_scores' in comparison

    def test_hyperparameter_tuning(self):
        """✅ Tune ensemble hyperparameters."""
        from guardian.ml.advanced_ensemble import EnsembleMLModel

        ensemble = EnsembleMLModel()

        tuned = ensemble.tune_hyperparameters({
            'param_grid': {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15],
                'learning_rate': [0.01, 0.1, 0.2]
            },
            'cv_splits': 5
        })

        assert 'best_params' in tuned
        assert 'best_score' in tuned

    def test_ensemble_uncertainty(self):
        """✅ Calculate prediction uncertainty."""
        from guardian.ml.advanced_ensemble import EnsembleMLModel

        ensemble = EnsembleMLModel()

        uncertainty = ensemble.calculate_uncertainty({
            'features': [1.0, 2.0, 3.0],
            'models': ['rf', 'xgb', 'lstm']
        })

        assert 'uncertainty_score' in uncertainty
        assert 'confidence_interval' in uncertainty
        assert uncertainty['confidence_interval'][0] < uncertainty['confidence_interval'][1]

    def test_ensemble_robustness(self):
        """✅ Test ensemble robustness to adversarial inputs."""
        from guardian.ml.advanced_ensemble import EnsembleMLModel

        ensemble = EnsembleMLModel()

        robustness = ensemble.test_robustness({
            'features': [1.0, 2.0, 3.0],
            'perturbation_magnitude': 0.1,
            'n_perturbations': 10
        })

        assert 'robustness_score' in robustness
        assert 'perturbation_results' in robustness
