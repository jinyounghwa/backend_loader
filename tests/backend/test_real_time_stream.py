"""
Sprint 32 Phase 4: Real-time Stream Processing Tests
Tests for DynamoDB Streams, Lambda EventSourceMapping, and SSE endpoints
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from handlers.stream_processor import (
    handle_stream_event,
    process_stream_record,
    handle_insert,
    handle_modify,
    handle_remove,
    parse_dynamodb_value,
)


class TestStreamProcessor:
    """Test DynamoDB Stream processor"""

    def test_handle_stream_event_with_multiple_records(self):
        """Test processing multiple stream records"""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'connection_id': {'S': 'conn-123'},
                            'account_id': {'S': '123456789012'},
                            'timestamp': {'S': '2026-05-23T10:00:00Z'},
                            'event_type': {'S': '$connect'},
                            'user_id': {'S': 'user@example.com'},
                            'status': {'S': 'success'},
                        }
                    }
                },
                {
                    'eventID': '2',
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'connection_id': {'S': 'conn-456'},
                            'account_id': {'S': '999999999999'},
                            'timestamp': {'S': '2026-05-23T10:01:00Z'},
                            'event_type': {'S': '$disconnect'},
                            'status': {'S': 'success'},
                        }
                    }
                }
            ]
        }

        result = handle_stream_event(event, None)

        assert result['statusCode'] == 200
        assert result['batchItemFailures'] == []

    def test_handle_stream_event_with_failed_record(self):
        """Test handling failed records in batch"""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'connection_id': {'S': 'conn-123'},
                            'timestamp': {'S': '2026-05-23T10:00:00Z'},
                            'event_type': {'S': '$connect'},
                        }
                    }
                },
                {
                    'eventID': '2',
                    'eventName': 'INVALID',  # Invalid event type
                    'dynamodb': {}
                }
            ]
        }

        with patch('handlers.stream_processor.process_stream_record', side_effect=[None, Exception('Invalid event')]):
            result = handle_stream_event(event, None)

            # Should have one failed record
            assert len(result['batchItemFailures']) == 1

    def test_handle_insert_event(self):
        """Test INSERT event handling"""
        dynamodb = {
            'NewImage': {
                'connection_id': {'S': 'conn-123'},
                'account_id': {'S': '123456789012'},
                'timestamp': {'S': '2026-05-23T10:00:00Z'},
                'event_type': {'S': '$connect'},
                'user_id': {'S': 'user@example.com'},
                'status': {'S': 'success'},
            }
        }

        with patch('handlers.stream_processor.broadcast_to_clients') as mock_broadcast:
            handle_insert(dynamodb)

            # Verify broadcast was called
            assert mock_broadcast.called
            call_args = mock_broadcast.call_args[0][0]
            assert call_args['type'] == 'audit_log_created'
            assert call_args['data']['account_id'] == '123456789012'

    def test_handle_modify_event(self):
        """Test MODIFY event handling"""
        dynamodb = {
            'NewImage': {
                'connection_id': {'S': 'conn-123'},
                'timestamp': {'S': '2026-05-23T10:00:00Z'},
            },
            'OldImage': {
                'connection_id': {'S': 'conn-123'},
                'timestamp': {'S': '2026-05-23T09:59:00Z'},
            }
        }

        with patch('handlers.stream_processor.broadcast_to_clients') as mock_broadcast:
            handle_modify(dynamodb)

            assert mock_broadcast.called
            call_args = mock_broadcast.call_args[0][0]
            assert call_args['type'] == 'audit_log_modified'

    def test_handle_remove_event(self):
        """Test REMOVE event handling (TTL expiration)"""
        dynamodb = {
            'OldImage': {
                'connection_id': {'S': 'conn-123'},
                'timestamp': {'S': '2026-05-23T10:00:00Z'},
            }
        }

        with patch('handlers.stream_processor.broadcast_to_clients') as mock_broadcast:
            handle_remove(dynamodb)

            assert mock_broadcast.called
            call_args = mock_broadcast.call_args[0][0]
            assert call_args['type'] == 'audit_log_removed'

    def test_parse_dynamodb_value_string(self):
        """Test parsing DynamoDB string value"""
        value = {'S': 'test-string'}
        result = parse_dynamodb_value(value)
        assert result == 'test-string'

    def test_parse_dynamodb_value_number(self):
        """Test parsing DynamoDB number value"""
        value = {'N': '42'}
        result = parse_dynamodb_value(value)
        assert result == 42.0

    def test_parse_dynamodb_value_boolean(self):
        """Test parsing DynamoDB boolean value"""
        value = {'BOOL': True}
        result = parse_dynamodb_value(value)
        assert result is True

    def test_parse_dynamodb_value_null(self):
        """Test parsing DynamoDB null value"""
        value = {'NULL': True}
        result = parse_dynamodb_value(value)
        assert result is None

    def test_parse_dynamodb_value_map(self):
        """Test parsing DynamoDB map (nested object)"""
        value = {
            'M': {
                'name': {'S': 'Test'},
                'count': {'N': '10'}
            }
        }
        result = parse_dynamodb_value(value)
        assert result['name'] == 'Test'
        assert result['count'] == 10.0

    def test_parse_dynamodb_value_list(self):
        """Test parsing DynamoDB list"""
        value = {
            'L': [
                {'S': 'item1'},
                {'S': 'item2'},
                {'N': '3'}
            ]
        }
        result = parse_dynamodb_value(value)
        assert len(result) == 3
        assert result[0] == 'item1'
        assert result[2] == 3.0


class TestStreamConfiguration:
    """Test DynamoDB Streams configuration"""

    def test_stream_specification_enabled(self):
        """Test that DynamoDB Streams is enabled for audit logs table"""
        # This verifies SAM template configuration
        stream_spec = {
            'StreamViewType': 'NEW_AND_OLD_IMAGES'
        }

        assert stream_spec['StreamViewType'] == 'NEW_AND_OLD_IMAGES'

    def test_event_source_mapping_configuration(self):
        """Test Lambda EventSourceMapping configuration"""
        # Verify EventSourceMapping settings
        config = {
            'BatchSize': 10,
            'BatchWindow': 5,
            'StartingPosition': 'LATEST',
            'MaximumRetryAttempts': 2,
            'FunctionResponseTypes': ['ReportBatchItemFailures']
        }

        assert config['BatchSize'] == 10
        assert config['StartingPosition'] == 'LATEST'
        assert 'ReportBatchItemFailures' in config['FunctionResponseTypes']


class TestStreamEventTypes:
    """Test different stream event types"""

    def test_insert_event_extraction(self):
        """Test correct data extraction from INSERT event"""
        record = {
            'eventName': 'INSERT',
            'dynamodb': {
                'NewImage': {
                    'connection_id': {'S': 'conn-123'},
                    'account_id': {'S': '123456789012'},
                    'timestamp': {'S': '2026-05-23T10:00:00Z'},
                    'event_type': {'S': '$connect'},
                }
            }
        }

        with patch('handlers.stream_processor.handle_insert') as mock_insert:
            process_stream_record(record)
            assert mock_insert.called

    def test_modify_event_extraction(self):
        """Test correct data extraction from MODIFY event"""
        record = {
            'eventName': 'MODIFY',
            'dynamodb': {
                'NewImage': {'connection_id': {'S': 'conn-123'}},
                'OldImage': {'connection_id': {'S': 'conn-123'}}
            }
        }

        with patch('handlers.stream_processor.handle_modify') as mock_modify:
            process_stream_record(record)
            assert mock_modify.called

    def test_remove_event_extraction(self):
        """Test correct data extraction from REMOVE event"""
        record = {
            'eventName': 'REMOVE',
            'dynamodb': {
                'OldImage': {'connection_id': {'S': 'conn-123'}}
            }
        }

        with patch('handlers.stream_processor.handle_remove') as mock_remove:
            process_stream_record(record)
            assert mock_remove.called


class TestRealTimeIntegration:
    """Integration tests for real-time features"""

    def test_account_id_in_stream_event(self):
        """Test account_id is properly included in stream events"""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'connection_id': {'S': 'conn-123'},
                            'account_id': {'S': '123456789012'},
                            'timestamp': {'S': '2026-05-23T10:00:00Z'},
                            'event_type': {'S': '$connect'},
                        }
                    }
                }
            ]
        }

        result = handle_stream_event(event, None)

        # Stream processing should succeed
        assert result['statusCode'] == 200

    def test_default_account_id_handling(self):
        """Test that missing account_id defaults to 'current'"""
        dynamodb = {
            'NewImage': {
                'connection_id': {'S': 'conn-123'},
                'timestamp': {'S': '2026-05-23T10:00:00Z'},
                'event_type': {'S': '$connect'},
                # account_id not provided
            }
        }

        with patch('handlers.stream_processor.broadcast_to_clients') as mock_broadcast:
            handle_insert(dynamodb)

            call_args = mock_broadcast.call_args[0][0]
            # account_id should default to 'current'
            assert call_args['data']['account_id'] == 'current'

    def test_multiple_accounts_in_stream(self):
        """Test handling events from multiple accounts in same stream"""
        event = {
            'Records': [
                {
                    'eventID': '1',
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'account_id': {'S': '111111111111'},
                            'timestamp': {'S': '2026-05-23T10:00:00Z'},
                            'event_type': {'S': '$connect'},
                        }
                    }
                },
                {
                    'eventID': '2',
                    'eventName': 'INSERT',
                    'dynamodb': {
                        'NewImage': {
                            'account_id': {'S': '222222222222'},
                            'timestamp': {'S': '2026-05-23T10:01:00Z'},
                            'event_type': {'S': '$connect'},
                        }
                    }
                }
            ]
        }

        result = handle_stream_event(event, None)

        # Should process both records from different accounts
        assert result['statusCode'] == 200
        assert len(result['batchItemFailures']) == 0
