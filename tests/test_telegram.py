"""Unit tests for Telegram responder"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.responders.telegram import TelegramResponder


class TestTelegramResponder(unittest.TestCase):
    """Unit tests for TelegramResponder"""

    def setUp(self):
        """Set up test fixtures"""
        self.bot_token = 'test-bot-token-12345'
        self.chat_id = '123456789'

    @patch('guardian.responders.telegram.requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        responder = TelegramResponder(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )
        result = responder.send_message('Test message')

        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch('guardian.responders.telegram.requests.post')
    def test_send_message_failure(self, mock_post):
        """Test failed message sending"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        responder = TelegramResponder(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )
        result = responder.send_message('Test message')

        self.assertFalse(result)

    @patch('guardian.responders.telegram.requests.post')
    def test_send_message_exception(self, mock_post):
        """Test message sending with exception"""
        mock_post.side_effect = Exception('Connection error')

        responder = TelegramResponder(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )
        result = responder.send_message('Test message')

        self.assertFalse(result)

    @patch('guardian.responders.telegram.requests.post')
    def test_send_cost_alert_format(self, mock_post):
        """Test cost alert message format"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        responder = TelegramResponder(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )

        cost_data = {
            'today_cost': 15.50,
            'threshold': 10.0,
            'increase_percent': 50.0,
            'date': '2024-04-26'
        }

        result = responder.send_cost_alert(cost_data)
        self.assertTrue(result)

        # Verify the message contains cost information
        call_args = mock_post.call_args
        message_data = call_args.kwargs['json']
        self.assertIn('15.50', message_data['text'])
        self.assertIn('10.0', message_data['text'])

    @patch('guardian.responders.telegram.requests.post')
    def test_send_ec2_alert_format(self, mock_post):
        """Test EC2 alert message format"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        responder = TelegramResponder(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )

        ec2_data = {
            'unauthorized_region_instances': {
                'ap-southeast-1': [{'InstanceId': 'i-12345'}]
            },
            'exposed_instances': [
                {
                    'instance_id': 'i-67890',
                    'region': 'us-east-1',
                    'exposed_rules': [{'from_port': 22, 'protocol': 'tcp'}]
                }
            ],
            'new_instances': [
                {'instance_id': 'i-99999', 'region': 'us-west-2'}
            ],
            'anomalies': [1]  # Non-empty list
        }

        result = responder.send_ec2_alert(ec2_data)
        self.assertTrue(result)

    @patch('guardian.responders.telegram.requests.post')
    def test_send_s3_alert_format(self, mock_post):
        """Test S3 alert message format"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        responder = TelegramResponder(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )

        s3_data = {
            'public_buckets': [
                {
                    'bucket_name': 'my-public-bucket',
                    'public_reasons': ['ACL allows public read', 'Bucket policy allows public write']
                }
            ],
            'new_buckets': [
                {'bucket_name': 'new-bucket'}
            ],
            'anomalies': [1]
        }

        result = responder.send_s3_alert(s3_data)
        self.assertTrue(result)

    @patch('guardian.responders.telegram.requests.post')
    def test_send_summary(self, mock_post):
        """Test daily summary message"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        responder = TelegramResponder(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )

        summary_data = {
            'total_events': 5,
            'by_type': {
                'cost': 2,
                'ec2': 2,
                's3': 1
            },
            'by_severity': {
                'critical': 2,
                'warning': 2,
                'info': 1
            }
        }

        result = responder.send_summary(summary_data)
        self.assertTrue(result)

        call_args = mock_post.call_args
        message_data = call_args.kwargs['json']
        self.assertIn('5', message_data['text'])  # Total events

    @patch('guardian.responders.telegram.requests.post')
    def test_send_auto_response_notification(self, mock_post):
        """Test auto-response notification"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        responder = TelegramResponder(
            bot_token=self.bot_token,
            chat_id=self.chat_id
        )

        result = responder.send_auto_response_notification(
            'stop_ec2',
            'i-12345678',
            'success'
        )
        self.assertTrue(result)

        result = responder.send_auto_response_notification(
            'block_s3_public',
            'my-bucket',
            'failed'
        )
        self.assertTrue(result)


class TestTelegramResponderInit(unittest.TestCase):
    """Test TelegramResponder initialization"""

    def test_init_with_env_vars(self):
        """Test initialization with environment variables"""
        os.environ['TELEGRAM_BOT_TOKEN'] = 'env-token'
        os.environ['TELEGRAM_CHAT_ID'] = 'env-chat-id'

        responder = TelegramResponder()
        self.assertEqual(responder.bot_token, 'env-token')
        self.assertEqual(responder.chat_id, 'env-chat-id')

        del os.environ['TELEGRAM_BOT_TOKEN']
        del os.environ['TELEGRAM_CHAT_ID']

    def test_init_with_explicit_params(self):
        """Test initialization with explicit parameters"""
        responder = TelegramResponder(
            bot_token='explicit-token',
            chat_id='explicit-chat-id'
        )
        self.assertEqual(responder.bot_token, 'explicit-token')
        self.assertEqual(responder.chat_id, 'explicit-chat-id')


if __name__ == '__main__':
    unittest.main()
