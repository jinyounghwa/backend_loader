"""Tests for S3 checker - LocalStack integration tests"""
import unittest
import os
import sys
import boto3
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.checkers.s3 import S3Checker
from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider


class TestS3Checker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        kwargs = Config.get_boto3_kwargs()
        cls.s3_client = boto3.client('s3', **kwargs)

        cls.private_bucket = 'guardian-test-private'
        cls.test_bucket = 'guardian-test-integ'

        for bucket in [cls.private_bucket, cls.test_bucket]:
            try:
                cls.s3_client.create_bucket(Bucket=bucket)
            except cls.s3_client.exceptions.BucketAlreadyOwnedByYou:
                pass
            except Exception as e:
                if 'BucketAlreadyExists' not in str(e):
                    print(f"Setup warning for {bucket}: {e}")

        # Ensure private bucket is actually private
        try:
            cls.s3_client.put_public_access_block(
                Bucket=cls.private_bucket,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
        except Exception as e:
            print(f"Setup warning: Could not set public access block for {cls.private_bucket}: {e}")

    @classmethod
    def tearDownClass(cls):
        for bucket in [cls.private_bucket, cls.test_bucket]:
            try:
                objects = cls.s3_client.list_objects_v2(Bucket=bucket)
                if 'Contents' in objects:
                    for obj in objects['Contents']:
                        cls.s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
                cls.s3_client.delete_bucket(Bucket=bucket)
            except Exception:
                pass

    def setUp(self):
        # Clear client cache to ensure fresh instances
        AWSClientProvider.clear_cache()
        self.s3_checker = S3Checker()

    def tearDown(self):
        # Clear cache after each test
        AWSClientProvider.clear_cache()

    def test_private_bucket_not_public_acl(self):
        is_public = self.s3_checker.is_bucket_public_acl(self.private_bucket)
        self.assertFalse(is_public)

    def test_public_acl_detection_logic(self):
        self.s3_checker.s3_client.get_bucket_acl = MagicMock(return_value={
            'Grants': [
                {
                    'Grantee': {
                        'Type': 'Group',
                        'URI': 'http://acs.amazonaws.com/groups/s3/AllUsers'
                    },
                    'Permission': 'READ'
                }
            ]
        })
        is_public = self.s3_checker.is_bucket_public_acl('any-bucket')
        self.assertTrue(is_public)

    def test_authenticated_users_acl_detected(self):
        self.s3_checker.s3_client.get_bucket_acl = MagicMock(return_value={
            'Grants': [
                {
                    'Grantee': {
                        'Type': 'Group',
                        'URI': 'http://acs.amazonaws.com/groups/s3/AuthenticatedUsers'
                    },
                    'Permission': 'READ'
                }
            ]
        })
        is_public = self.s3_checker.is_bucket_public_acl('any-bucket')
        self.assertTrue(is_public)

    def test_bucket_without_policy_not_public(self):
        is_public, statement = self.s3_checker.is_bucket_public_policy(self.private_bucket)
        self.assertFalse(is_public)
        self.assertEqual(statement, {})

    def test_public_policy_detection_logic(self):
        self.s3_checker.s3_client.get_bucket_policy = MagicMock(return_value={
            'Policy': '{"Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::bucket/*"}]}'
        })
        is_public, statement = self.s3_checker.is_bucket_public_policy('any-bucket')
        self.assertTrue(is_public)
        self.assertEqual(statement['Effect'], 'Allow')

    def test_block_public_access(self):
        success = self.s3_checker.block_public_access(self.private_bucket)
        self.assertTrue(success)

        kwargs = Config.get_boto3_kwargs()
        s3 = boto3.client('s3', **kwargs)
        result = s3.get_public_access_block(Bucket=self.private_bucket)
        config = result['PublicAccessBlockConfiguration']
        self.assertTrue(config['BlockPublicAcls'])
        self.assertTrue(config['IgnorePublicAcls'])
        self.assertTrue(config['BlockPublicPolicy'])
        self.assertTrue(config['RestrictPublicBuckets'])

    def test_check_s3_anomalies_structure(self):
        is_anomaly, data = self.s3_checker.check_s3_anomalies()
        self.assertIsInstance(is_anomaly, bool)
        for key in ['is_anomaly', 'public_buckets', 'new_buckets', 'anomalies', 'timestamp']:
            self.assertIn(key, data)


if __name__ == '__main__':
    unittest.main()
