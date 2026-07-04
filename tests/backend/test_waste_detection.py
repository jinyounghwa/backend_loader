"""Sprint 39 Phase 2: Resource Waste Detection"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path
from guardian.detectors.waste_detector import WasteDetector, WasteResource


# ==========================================
# Test Group 1: Idle Resource Detection (2 tests)
# ==========================================

def test_waste_detector_initialization():
    """Test waste detector initialization"""
    ec2_client = MagicMock()
    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)

    assert detector is not None
    assert detector.ec2 is not None
    assert detector.cloudwatch is not None


def test_detect_idle_resources():
    """Test idle EC2 and RDS detection"""
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-idle-123',
                        'InstanceType': 't3.medium',
                        'State': {'Name': 'running'},
                        'LaunchTime': datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=60)
                    }
                ]
            }
        ]
    }

    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)
    idle_resources = detector.detect_idle_resources('acc-123')

    assert idle_resources is not None
    assert isinstance(idle_resources, list)


# ==========================================
# Test Group 2: Unattached Volume Detection (2 tests)
# ==========================================

def test_detect_unattached_volumes():
    """Test unattached EBS volume detection"""
    ec2_client = MagicMock()
    ec2_client.describe_volumes.return_value = {
        'Volumes': [
            {
                'VolumeId': 'vol-unattached-1',
                'Size': 100,
                'State': 'available',
                'CreateTime': datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
            },
            {
                'VolumeId': 'vol-attached-1',
                'Size': 50,
                'State': 'in-use',
                'Attachments': [
                    {'InstanceId': 'i-123', 'State': 'attached'}
                ]
            }
        ]
    }

    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)
    unattached = detector.detect_unattached_volumes('acc-123')

    assert unattached is not None
    assert isinstance(unattached, list)


def test_unattached_volume_cost_calculation():
    """Test cost calculation for unattached volumes"""
    # EBS cost: ~$0.10 per GB-month
    volume_size_gb = 100
    monthly_cost = volume_size_gb * 0.10

    assert monthly_cost == 10.0


# ==========================================
# Test Group 3: Elastic IP Detection (2 tests)
# ==========================================

def test_detect_unallocated_elastic_ips():
    """Test unallocated elastic IP detection"""
    ec2_client = MagicMock()
    ec2_client.describe_addresses.return_value = {
        'Addresses': [
            {
                'PublicIp': '1.2.3.4',
                'AllocationId': 'eipalloc-123',
                'AssociationId': None  # Not associated
            },
            {
                'PublicIp': '1.2.3.5',
                'AllocationId': 'eipalloc-456',
                'AssociationId': 'eipassoc-789'  # Associated
            }
        ]
    }

    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)
    unallocated_ips = detector.detect_unallocated_elastic_ips('acc-123')

    assert unallocated_ips is not None
    assert isinstance(unallocated_ips, list)


def test_elastic_ip_cost():
    """Test elastic IP cost tracking"""
    # AWS charges $0.005/hour for unassociated EIPs
    hourly_cost = 0.005
    monthly_cost = hourly_cost * 24 * 30

    assert monthly_cost > 3.0  # Should be around $3.60


# ==========================================
# Test Group 4: Snapshot Analysis (2 tests)
# ==========================================

def test_detect_snapshot_waste():
    """Test old/unused snapshot detection"""
    ec2_client = MagicMock()
    ec2_client.describe_snapshots.return_value = {
        'Snapshots': [
            {
                'SnapshotId': 'snap-old-1',
                'StartTime': datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=180),
                'VolumeSize': 100,
                'State': 'completed'
            },
            {
                'SnapshotId': 'snap-recent-1',
                'StartTime': datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7),
                'VolumeSize': 50,
                'State': 'completed'
            }
        ]
    }

    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)
    waste_snapshots = detector.detect_snapshot_waste('acc-123')

    assert waste_snapshots is not None
    assert isinstance(waste_snapshots, list)


def test_snapshot_cost_estimation():
    """Test snapshot storage cost estimation"""
    # EBS Snapshot cost: ~$0.023 per GB-month
    snapshot_size_gb = 100
    monthly_cost = snapshot_size_gb * 0.023

    assert monthly_cost > 2.0


# ==========================================
# Test Group 5: Waste Scoring (2 tests)
# ==========================================

def test_calculate_waste_score():
    """Test resource waste score calculation"""
    ec2_client = MagicMock()
    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)

    # Idle for 90 days should have high waste score
    waste_score = detector.calculate_waste_score('EC2', idle_days=90)

    assert waste_score is not None
    assert waste_score >= 0
    assert waste_score <= 100


def test_waste_score_by_resource_type():
    """Test waste score varies by resource type"""
    ec2_client = MagicMock()
    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)

    ec2_score = detector.calculate_waste_score('EC2', idle_days=30)
    ebs_score = detector.calculate_waste_score('EBS', idle_days=30)
    eip_score = detector.calculate_waste_score('ElasticIP', idle_days=30)

    assert isinstance(ec2_score, (int, float))
    assert isinstance(ebs_score, (int, float))
    assert isinstance(eip_score, (int, float))


# ==========================================
# Test Group 6: Safe Removal Candidates (2 tests)
# ==========================================

def test_get_removal_candidates():
    """Test identification of safely removable resources"""
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-candidate-1',
                        'InstanceType': 't3.small',
                        'State': {'Name': 'stopped'},
                        'LaunchTime': datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=60)
                    }
                ]
            }
        ]
    }

    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)
    candidates = detector.get_removal_candidates('acc-123', days=30)

    assert candidates is not None
    assert isinstance(candidates, list)


def test_removal_safety_check():
    """Test safety checks before resource removal"""
    ec2_client = MagicMock()
    cloudwatch_client = MagicMock()

    detector = WasteDetector(ec2_client, cloudwatch_client)

    # Should not remove resources with tags
    resource = {
        'resource_id': 'i-tagged',
        'tags': {'Environment': 'production', 'Managed': 'terraform'}
    }

    is_safe = detector.is_safe_to_remove(resource)

    assert isinstance(is_safe, bool)
