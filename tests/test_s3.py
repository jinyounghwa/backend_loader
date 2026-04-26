"""Tests for S3 checker"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.checkers.s3 import S3Checker


class TestS3Checker(unittest.TestCase):
    def setUp(self):
        self.s3_checker = S3Checker()

    @patch('guardian.checkers.s3.boto3.client')
    def test_is_bucket_public_acl_true(self, mock_boto3):
        """Test public ACL detection"""
        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        # Mock public ACL response
        mock_s3_client.get_bucket_acl.return_value = {
            'Grants': [
                {
                    'Grantee': {
                        'Type': 'Group',
                        'URI': 'http://acs.amazonaws.com/groups/s3/AllUsers'
                    },
                    'Permission': 'READ'
                }
            ]
        }

        is_public = self.s3_checker.is_bucket_public_acl('test-bucket')
        self.assertTrue(is_public)

    @patch('guardian.checkers.s3.boto3.client')
    def test_is_bucket_public_acl_false(self, mock_boto3):
        """Test private ACL detection"""
        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        # Mock private ACL response
        mock_s3_client.get_bucket_acl.return_value = {
            'Grants': [
                {
                    'Grantee': {
                        'Type': 'CanonicalUser',
                        'ID': '123456'
                    },
                    'Permission': 'FULL_CONTROL'
                }
            ]
        }

        is_public = self.s3_checker.is_bucket_public_acl('test-bucket')
        self.assertFalse(is_public)

    @patch('guardian.checkers.s3.boto3.client')
    def test_is_bucket_public_policy(self, mock_boto3):
        """Test public policy detection"""
        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        # Mock public policy response
        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': '*',
                    'Action': 's3:GetObject',
                    'Resource': 'arn:aws:s3:::test-bucket/*'
                }
            ]
        }
        mock_s3_client.get_bucket_policy.return_value = {
            'Policy': str(policy)
        }

        is_public, statement = self.s3_checker.is_bucket_public_policy('test-bucket')
        self.assertTrue(is_public)

    @patch('guardian.checkers.s3.boto3.client')
    def test_block_public_access(self, mock_boto3):
        """Test blocking public access"""
        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        mock_s3_client.put_public_access_block.return_value = {}

        success = self.s3_checker.block_public_access('test-bucket')
        self.assertTrue(success)

        # Verify the call was made with correct parameters
        mock_s3_client.put_public_access_block.assert_called_once()


if __name__ == '__main__':
    unittest.main()
