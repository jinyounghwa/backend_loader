"""리소스 낭비 탐지 엔진"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


@dataclass
class WasteResource:
    """낭비되는 리소스 정보"""
    resource_id: str
    resource_type: str  # 'EC2', 'EBS', 'ElasticIP', 'RDS', 'Snapshot'
    idle_days: int
    monthly_cost: float
    waste_score: int  # 0-100
    removal_safety: str  # 'safe', 'caution', 'protected'


class WasteDetector:
    """AWS 리소스 낭비 탐지 엔진"""

    def __init__(self, ec2_client, cloudwatch_client):
        """
        Args:
            ec2_client: boto3 EC2 client
            cloudwatch_client: boto3 CloudWatch client
        """
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client

    def detect_idle_resources(self, account_id: str, idle_days: int = 30) -> List[Dict]:
        """
        유휴 EC2 인스턴스 탐지

        Args:
            account_id: AWS Account ID
            idle_days: 유휴 판정 기준 (일)

        Returns:
            유휴 인스턴스 목록
        """
        try:
            response = self.ec2.describe_instances()
            idle_instances = []

            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_id = instance['InstanceId']

                    if instance['State']['Name'] != 'running':
                        continue

                    # CPU 사용률 확인
                    cpu_utilization = self._get_cpu_utilization(instance_id)

                    if cpu_utilization and cpu_utilization < 5:
                        launch_time = instance.get('LaunchTime', datetime.now(timezone.utc))
                        age_days = (datetime.now(timezone.utc) - launch_time).days

                        if age_days > idle_days:
                            idle_instances.append({
                                'instance_id': instance_id,
                                'instance_type': instance['InstanceType'],
                                'state': instance['State']['Name'],
                                'cpu_utilization': cpu_utilization,
                                'age_days': age_days,
                                'monthly_cost': self._get_instance_hourly_cost(instance['InstanceType']) * 24 * 30,
                                'priority': 'high'
                            })

            logger.info(f"Found {len(idle_instances)} idle instances")
            return idle_instances

        except Exception as e:
            logger.error(f"Idle resource detection failed: {str(e)}")
            return []

    def detect_unattached_volumes(self, account_id: str) -> List[Dict]:
        """
        연결되지 않은 EBS 볼륨 탐지

        Returns:
            미연결 볼륨 목록
        """
        try:
            response = self.ec2.describe_volumes()
            unattached = []

            for volume in response.get('Volumes', []):
                if volume['State'] == 'available':  # Not attached
                    create_time = volume.get('CreateTime', datetime.now(timezone.utc))
                    age_days = (datetime.now(timezone.utc) - create_time).days

                    monthly_cost = volume['Size'] * 0.10  # $0.10 per GB-month
                    waste_score = min(100, (age_days / 90) * 100)

                    unattached.append({
                        'volume_id': volume['VolumeId'],
                        'size_gb': volume['Size'],
                        'state': volume['State'],
                        'age_days': age_days,
                        'monthly_cost': monthly_cost,
                        'waste_score': int(waste_score),
                        'priority': 'high' if monthly_cost > 50 else 'medium'
                    })

            logger.info(f"Found {len(unattached)} unattached volumes")
            return unattached

        except Exception as e:
            logger.error(f"Unattached volume detection failed: {str(e)}")
            return []

    def detect_unallocated_elastic_ips(self, account_id: str) -> List[Dict]:
        """
        미할당 탄력적 IP 탐지

        Returns:
            미할당 IP 목록
        """
        try:
            response = self.ec2.describe_addresses()
            unallocated = []

            for address in response.get('Addresses', []):
                # No AssociationId means not associated with an instance
                if not address.get('AssociationId'):
                    monthly_cost = 0.005 * 24 * 30  # $0.005/hour
                    unallocated.append({
                        'allocation_id': address['AllocationId'],
                        'public_ip': address['PublicIp'],
                        'monthly_cost': monthly_cost,
                        'waste_score': 85,  # High waste for unused IPs
                        'priority': 'high'
                    })

            logger.info(f"Found {len(unallocated)} unallocated elastic IPs")
            return unallocated

        except Exception as e:
            logger.error(f"Unallocated elastic IP detection failed: {str(e)}")
            return []

    def detect_snapshot_waste(self, account_id: str, days: int = 90) -> List[Dict]:
        """
        오래된 스냅샷 탐지 및 낭비 분석

        Args:
            account_id: AWS Account ID
            days: 낭비 판정 기준 (일)

        Returns:
            낭비 스냅샷 목록
        """
        try:
            response = self.ec2.describe_snapshots()
            waste_snapshots = []

            for snapshot in response.get('Snapshots', []):
                if snapshot['State'] != 'completed':
                    continue

                start_time = snapshot.get('StartTime', datetime.now(timezone.utc))
                age_days = (datetime.now(timezone.utc) - start_time).days

                if age_days > days:
                    monthly_cost = snapshot['VolumeSize'] * 0.023  # $0.023 per GB-month
                    waste_score = min(100, (age_days / 180) * 100)

                    waste_snapshots.append({
                        'snapshot_id': snapshot['SnapshotId'],
                        'volume_size': snapshot['VolumeSize'],
                        'age_days': age_days,
                        'monthly_cost': monthly_cost,
                        'waste_score': int(waste_score),
                        'priority': 'medium' if age_days < 180 else 'high'
                    })

            logger.info(f"Found {len(waste_snapshots)} waste snapshots")
            return waste_snapshots

        except Exception as e:
            logger.error(f"Snapshot waste detection failed: {str(e)}")
            return []

    def calculate_waste_score(self, resource_type: str, idle_days: int) -> int:
        """
        리소스 낭비도 점수화 (0-100)

        점수 = (idle_days / reference_days) * 100

        Args:
            resource_type: 리소스 유형
            idle_days: 유휴 기간 (일)

        Returns:
            낭비 점수 (0-100)
        """
        # Reference idle days for each resource type
        reference_days = {
            'EC2': 90,
            'EBS': 120,
            'RDS': 60,
            'ElasticIP': 14,
            'Snapshot': 180,
        }

        ref_days = reference_days.get(resource_type, 90)
        score = min(100, int((idle_days / ref_days) * 100))

        return max(0, score)

    def get_removal_candidates(self, account_id: str, days: int = 30) -> List[Dict]:
        """
        안전하게 제거 가능한 리소스 목록

        Args:
            account_id: AWS Account ID
            days: 유휴 기간 기준

        Returns:
            제거 후보 리소스 목록
        """
        candidates = []

        # Combine all waste detection
        idle_resources = self.detect_idle_resources(account_id, idle_days=days)
        unattached_volumes = self.detect_unattached_volumes(account_id)
        unallocated_ips = self.detect_unallocated_elastic_ips(account_id)
        waste_snapshots = self.detect_snapshot_waste(account_id, days=days)

        # Filter for safety
        for resource in idle_resources:
            if self.is_safe_to_remove(resource):
                candidates.append(resource)

        for volume in unattached_volumes:
            if self.is_safe_to_remove(volume):
                candidates.append(volume)

        for ip in unallocated_ips:
            if self.is_safe_to_remove(ip):
                candidates.append(ip)

        for snapshot in waste_snapshots:
            if self.is_safe_to_remove(snapshot):
                candidates.append(snapshot)

        # Sort by potential savings
        candidates.sort(key=lambda x: x.get('monthly_cost', 0), reverse=True)

        logger.info(f"Found {len(candidates)} safe removal candidates")
        return candidates

    def is_safe_to_remove(self, resource: Dict) -> bool:
        """
        리소스 제거 안전성 확인

        Args:
            resource: 리소스 정보

        Returns:
            제거 가능 여부
        """
        # Don't remove resources with important tags
        tags = resource.get('tags', {})
        protected_tags = ['Environment', 'Managed', 'Terraform', 'Production']

        for tag_key in protected_tags:
            if tag_key in tags:
                return False

        # Don't remove resources with active backups
        if resource.get('has_backup'):
            return False

        # Don't remove resources with specific characteristics
        if resource.get('state') == 'stopped':
            return False  # Stopped instances might be intentionally halted

        return True

    def _get_cpu_utilization(self, instance_id: str) -> Optional[float]:
        """인스턴스 CPU 사용률 조회 (시뮬레이션)"""
        return 3.5  # 시뮬레이션 값

    def _get_instance_hourly_cost(self, instance_type: str) -> float:
        """EC2 인스턴스 시간당 비용"""
        cost_map = {
            't3.small': 0.0208,
            't3.medium': 0.0416,
            't3.large': 0.0832,
            't3.xlarge': 0.1664,
            'c5.large': 0.085,
            'c5.xlarge': 0.17,
        }
        return cost_map.get(instance_type, 0.05)
