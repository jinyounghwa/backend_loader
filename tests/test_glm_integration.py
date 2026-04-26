"""Tests for GLM integration"""
import unittest
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.responders.glm import GLMAnalyzer


class TestGLMIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Use test API key from environment or default
        api_key = os.getenv('GLM_API_KEY', '')
        self.glm = GLMAnalyzer(api_key=api_key)

    def test_glm_initialization(self):
        """Test GLM analyzer initialization"""
        self.assertIsNotNone(self.glm)
        print(f"✓ GLM initialized (API available: {self.glm.is_available})")

    def test_cost_anomaly_analysis(self):
        """Test cost anomaly analysis"""
        if not self.glm.is_available:
            self.skipTest("GLM API key not configured")

        cost_data = {
            'today_cost': 25.50,
            'threshold': 10.0,
            'yesterday_cost': 5.0,
            'monthly_cost': 250.0,
            'increase_percent': 410.0
        }

        result = self.glm.analyze_cost_anomaly(cost_data)
        self.assertTrue(result['success'])
        self.assertIn('analysis', result)
        print(f"✓ Cost analysis complete: {json.dumps(result, indent=2)}")

    def test_ec2_anomaly_analysis(self):
        """Test EC2 anomaly analysis"""
        if not self.glm.is_available:
            self.skipTest("GLM API key not configured")

        ec2_data = {
            'is_anomaly': True,
            'unauthorized_region_instances': {
                'eu-west-1': [
                    {'InstanceId': 'i-12345678', 'InstanceType': 't3.micro'}
                ]
            },
            'exposed_instances': [
                {
                    'instance_id': 'i-87654321',
                    'region': 'us-east-1',
                    'exposed_rules': [
                        {
                            'group_id': 'sg-12345',
                            'from_port': 22,
                            'to_port': 22,
                            'protocol': 'tcp'
                        }
                    ]
                }
            ],
            'new_instances': [
                {
                    'instance_id': 'i-newinstance',
                    'region': 'us-east-1',
                    'instance_type': 't2.small'
                }
            ],
            'anomalies': [
                'Instances in unauthorized regions',
                'Exposed security groups'
            ]
        }

        result = self.glm.analyze_ec2_anomalies(ec2_data)
        self.assertTrue(result['success'])
        self.assertIn('analysis', result)
        print(f"✓ EC2 analysis complete: {json.dumps(result, indent=2)}")

    def test_s3_anomaly_analysis(self):
        """Test S3 anomaly analysis"""
        if not self.glm.is_available:
            self.skipTest("GLM API key not configured")

        s3_data = {
            'is_anomaly': True,
            'public_buckets': [
                {
                    'bucket_name': 'public-bucket-1',
                    'public_reasons': ['Public ACL', 'Public Bucket Policy']
                },
                {
                    'bucket_name': 'public-bucket-2',
                    'public_reasons': ['Public Access Block Disabled']
                }
            ],
            'new_buckets': [
                {
                    'bucket_name': 'new-bucket-2024',
                    'creation_date': '2024-01-15T10:30:00'
                }
            ],
            'anomalies': [
                'Public buckets detected',
                'New buckets created'
            ]
        }

        result = self.glm.analyze_s3_anomalies(s3_data)
        self.assertTrue(result['success'])
        self.assertIn('analysis', result)
        print(f"✓ S3 analysis complete: {json.dumps(result, indent=2)}")

    def test_remediation_steps(self):
        """Test remediation steps generation"""
        if not self.glm.is_available:
            self.skipTest("GLM API key not configured")

        steps = self.glm.get_remediation_steps(
            'ec2_exposure',
            {'instance_id': 'i-12345678', 'port': 22}
        )

        self.assertIsInstance(steps, list)
        self.assertGreater(len(steps), 0)
        print(f"✓ Remediation steps generated: {len(steps)} steps")

    def test_summary_report(self):
        """Test summary report generation"""
        if not self.glm.is_available:
            self.skipTest("GLM API key not configured")

        all_checks = {
            'cost': {
                'is_anomaly': True,
                'today_cost': 25.50,
                'monthly_cost': 250.0
            },
            'ec2': {
                'is_anomaly': True,
                'anomalies': ['Exposed security group'],
                'exposed_instances': [
                    {'instance_id': 'i-12345'}
                ]
            },
            's3': {
                'is_anomaly': True,
                'public_buckets': [
                    {'bucket_name': 'public-bucket'}
                ],
                'new_buckets': []
            }
        }

        result = self.glm.generate_summary_report(all_checks)
        self.assertTrue(result['success'])
        self.assertIn('report', result)
        print(f"✓ Summary report generated: {json.dumps(result, indent=2)}")


class TestGLMWithoutAPI(unittest.TestCase):
    """Test GLM analyzer without API key"""

    def setUp(self):
        """Set up test fixtures without API key"""
        self.glm = GLMAnalyzer(api_key='')

    def test_glm_graceful_degradation(self):
        """Test that GLM analyzer handles missing API key gracefully"""
        self.assertFalse(self.glm.is_available)

        cost_data = {
            'today_cost': 25.50,
            'threshold': 10.0,
            'yesterday_cost': 5.0,
            'monthly_cost': 250.0,
            'increase_percent': 410.0
        }

        result = self.glm.analyze_cost_anomaly(cost_data)
        self.assertFalse(result['success'])
        print("✓ GLM gracefully handles missing API key")


if __name__ == '__main__':
    unittest.main()
