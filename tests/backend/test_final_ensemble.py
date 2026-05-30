"""Final ensemble & real-time updates tests for AWS Guardian."""

import pytest


class TestEnsemblePredictor:
    """Test ensemble prediction model."""

    def test_create_ensemble_model(self):
        """✅ Create ensemble predictor."""
        from guardian.ml.final_ensemble import EnsemblePredictor

        predictor = EnsemblePredictor()

        result = predictor.create({
            'models': ['arima', 'prophet', 'isolation_forest'],
            'weights': [0.4, 0.35, 0.25]
        })

        assert 'ensemble_id' in result
        assert 'models' in result or 'model_count' in result

    def test_ensemble_prediction(self):
        """✅ Make ensemble predictions."""
        from guardian.ml.final_ensemble import EnsemblePredictor

        predictor = EnsemblePredictor()

        result = predictor.predict({
            'ensemble_id': 'ens_123',
            'input_data': [100, 102, 101, 103, 105, 107],
            'horizon': 5
        })

        assert 'predictions' in result
        assert 'confidence_interval' in result or 'variance' in result

    def test_ensemble_with_voting(self):
        """✅ Ensemble voting strategy."""
        from guardian.ml.final_ensemble import EnsemblePredictor

        predictor = EnsemblePredictor()

        result = predictor.predict({
            'models': [
                {'name': 'model_1', 'output': 0.85},
                {'name': 'model_2', 'output': 0.90},
                {'name': 'model_3', 'output': 0.87}
            ],
            'voting_type': 'soft'
        })

        assert 'ensemble_prediction' in result or 'final_prediction' in result


class TestRealtimeWebSocket:
    """Test real-time WebSocket streaming."""

    def test_websocket_connection(self):
        """✅ Establish WebSocket connection."""
        from guardian.ml.final_ensemble import RealtimeWebSocket

        ws = RealtimeWebSocket()

        result = ws.connect({
            'url': 'ws://localhost:8000/threats',
            'auth_token': 'token_123'
        })

        assert 'connection_id' in result
        assert 'status' in result

    def test_stream_threat_updates(self):
        """✅ Stream threat updates in real-time."""
        from guardian.ml.final_ensemble import RealtimeWebSocket

        ws = RealtimeWebSocket()

        result = ws.stream({
            'connection_id': 'ws_123',
            'event_type': 'threat_detected',
            'data': {
                'threat_id': 'threat_001',
                'severity': 0.9,
                'timestamp': '2026-05-30T10:30:00Z'
            }
        })

        assert 'sent' in result or 'message_id' in result
        assert 'status' in result

    def test_websocket_backpressure(self):
        """✅ Handle backpressure in WebSocket."""
        from guardian.ml.final_ensemble import RealtimeWebSocket

        ws = RealtimeWebSocket()

        result = ws.handle_backpressure({
            'connection_id': 'ws_123',
            'queue_size': 1000,
            'max_queue': 500,
            'batch_size': 100
        })

        assert 'batches' in result or 'processed' in result
        assert 'status' in result or 'dropped' in result


class TestModelFusion:
    """Test model fusion and integration."""

    def test_fuse_model_predictions(self):
        """✅ Fuse predictions from multiple models."""
        from guardian.ml.final_ensemble import ModelFusion

        fusion = ModelFusion()

        result = fusion.fuse({
            'predictions': [
                {'model': 'arima', 'value': 0.75, 'confidence': 0.9},
                {'model': 'prophet', 'value': 0.78, 'confidence': 0.85},
                {'model': 'isolation_forest', 'value': 0.72, 'confidence': 0.8}
            ],
            'fusion_method': 'weighted_average'
        })

        assert 'fused_prediction' in result or 'final_value' in result
        assert 'confidence' in result

    def test_dynamic_weight_adjustment(self):
        """✅ Adjust ensemble weights dynamically."""
        from guardian.ml.final_ensemble import ModelFusion

        fusion = ModelFusion()

        result = fusion.adjust_weights({
            'models': ['model_1', 'model_2', 'model_3'],
            'performance_metrics': [0.92, 0.85, 0.88],
            'method': 'adaptive'
        })

        assert 'new_weights' in result or 'weights' in result
        assert sum(result.get('new_weights', result.get('weights', []))) == pytest.approx(1.0) if result.get('new_weights') or result.get('weights') else True

    def test_model_stacking(self):
        """✅ Use stacking for ensemble."""
        from guardian.ml.final_ensemble import ModelFusion

        fusion = ModelFusion()

        result = fusion.stack({
            'level_0_models': ['model_1', 'model_2', 'model_3'],
            'level_1_model': 'meta_learner',
            'training_data': [{'x': [1, 2, 3], 'y': 0.8}] * 10
        })

        assert 'stacked_model_id' in result or 'meta_model' in result


class TestStreamingAnalytics:
    """Test streaming data analytics."""

    def test_stream_aggregation(self):
        """✅ Aggregate metrics over streams."""
        from guardian.ml.final_ensemble import StreamingAnalytics

        analytics = StreamingAnalytics()

        result = analytics.aggregate({
            'stream_events': [
                {'value': 100, 'timestamp': '2026-05-30T10:00:00Z'},
                {'value': 105, 'timestamp': '2026-05-30T10:01:00Z'},
                {'value': 102, 'timestamp': '2026-05-30T10:02:00Z'}
            ],
            'window_size': 60,
            'aggregations': ['mean', 'variance', 'max']
        })

        assert 'mean' in result or 'aggregated' in result
        assert 'variance' in result or result.get('aggregated') is not None

    def test_stream_anomaly_detection(self):
        """✅ Detect anomalies in stream."""
        from guardian.ml.final_ensemble import StreamingAnalytics

        analytics = StreamingAnalytics()

        result = analytics.detect_anomalies({
            'stream': [100, 102, 101, 99, 101, 100, 500, 101, 102],
            'method': 'isolation_forest',
            'contamination': 0.1
        })

        assert 'anomalies' in result or 'anomaly_indices' in result
        assert len(result.get('anomalies', result.get('anomaly_indices', []))) > 0

    def test_sliding_window_analysis(self):
        """✅ Analyze data with sliding windows."""
        from guardian.ml.final_ensemble import StreamingAnalytics

        analytics = StreamingAnalytics()

        result = analytics.sliding_window({
            'data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'window_size': 3,
            'step': 1,
            'function': 'mean'
        })

        assert 'windows' in result or 'results' in result


class TestFinalEnsembleIntegration:
    """End-to-end final ensemble workflows."""

    def test_full_ensemble_pipeline(self):
        """✅ Complete pipeline: create → train → predict → update."""
        from guardian.ml.final_ensemble import (
            EnsemblePredictor,
            ModelFusion,
            StreamingAnalytics
        )

        predictor = EnsemblePredictor()
        fusion = ModelFusion()
        analytics = StreamingAnalytics()

        # Create ensemble
        ensemble = predictor.create({
            'models': ['arima', 'prophet'],
            'weights': [0.5, 0.5]
        })
        assert 'ensemble_id' in ensemble

        # Get predictions
        predictions = predictor.predict({
            'ensemble_id': ensemble['ensemble_id'],
            'input_data': [100, 102, 101]
        })
        assert 'predictions' in predictions

        # Fuse with dynamic weights
        fused = fusion.fuse({
            'predictions': [
                {'model': 'arima', 'value': predictions['predictions'][0]},
                {'model': 'prophet', 'value': predictions['predictions'][0]}
            ]
        })
        assert 'fused_prediction' in fused or 'final_value' in fused

    def test_realtime_streaming_ensemble(self):
        """✅ Real-time ensemble with WebSocket streaming."""
        from guardian.ml.final_ensemble import (
            EnsemblePredictor,
            RealtimeWebSocket
        )

        predictor = EnsemblePredictor()
        ws = RealtimeWebSocket()

        # Connect
        conn = ws.connect({'url': 'ws://localhost:8000'})
        assert 'connection_id' in conn

        # Stream predictions
        stream_result = ws.stream({
            'connection_id': conn['connection_id'],
            'event_type': 'prediction',
            'data': {'value': 0.85}
        })
        assert 'sent' in stream_result or 'message_id' in stream_result

    def test_end_to_end_with_analytics(self):
        """✅ Full pipeline with streaming analytics."""
        from guardian.ml.final_ensemble import (
            EnsemblePredictor,
            StreamingAnalytics,
            RealtimeWebSocket
        )

        predictor = EnsemblePredictor()
        analytics = StreamingAnalytics()
        ws = RealtimeWebSocket()

        # Create ensemble
        ens = predictor.create({'models': ['model1', 'model2']})

        # Stream data
        stream_data = [100, 102, 101, 105, 104]

        # Aggregate
        agg = analytics.aggregate({
            'stream_events': [{'value': v} for v in stream_data]
        })
        assert 'mean' in agg or 'aggregated' in agg

        # Connect and stream
        conn = ws.connect({'url': 'ws://localhost:8000'})
        assert 'connection_id' in conn

    def test_full_production_workflow(self):
        """✅ Complete production-ready workflow."""
        from guardian.ml.final_ensemble import (
            EnsemblePredictor,
            ModelFusion,
            StreamingAnalytics,
            RealtimeWebSocket
        )

        # Initialize all components
        predictor = EnsemblePredictor()
        fusion = ModelFusion()
        analytics = StreamingAnalytics()
        ws = RealtimeWebSocket()

        # Create ensemble
        ensemble = predictor.create({'models': ['m1', 'm2', 'm3']})
        assert 'ensemble_id' in ensemble

        # Setup streaming
        conn = ws.connect({'url': 'ws://localhost'})
        assert 'connection_id' in conn

        # Process stream
        agg = analytics.aggregate({'stream_events': [{'value': 100}]})
        assert 'mean' in agg or 'aggregated' in agg

        # Make prediction
        pred = predictor.predict({'ensemble_id': ensemble['ensemble_id'], 'input_data': [100]})
        assert 'predictions' in pred

        # Fuse and update
        fused = fusion.adjust_weights({'models': ['m1', 'm2', 'm3'], 'performance_metrics': [0.9, 0.85, 0.88]})
        assert 'new_weights' in fused or 'weights' in fused
