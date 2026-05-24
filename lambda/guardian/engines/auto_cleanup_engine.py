"""자동 리소스 정리 엔진"""

import logging
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


@dataclass
class CleanupTarget:
    """정리 대상 리소스"""
    resource_id: str
    resource_type: str  # 'EBS_VOLUME', 'SNAPSHOT', 'ELASTIC_IP', 'SECURITY_GROUP'
    reason: str
    estimated_savings: float
    created_date: str
    last_modified: str


class AutoCleanupEngine:
    """AWS 리소스 자동 정리 엔진"""

    def __init__(self, ec2_client, s3_client, dynamodb_table):
        """
        Args:
            ec2_client: boto3 EC2 client
            s3_client: boto3 S3 client
            dynamodb_table: DynamoDB table for cleanup logs
        """
        self.ec2 = ec2_client
        self.s3 = s3_client
        self.table = dynamodb_table
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def identify_cleanup_targets(self, account_id: str) -> List[Dict]:
        """
        정리 대상 리소스 식별

        Args:
            account_id: AWS Account ID

        Returns:
            정리 대상 리소스 목록
        """
        targets = []

        try:
            # Unattached volumes
            targets.extend(self._find_unattached_volumes(account_id))

            # Old snapshots
            targets.extend(self._find_old_snapshots(account_id))

            # Unallocated elastic IPs
            targets.extend(self._find_unallocated_ips(account_id))

            # Empty security groups
            targets.extend(self._find_empty_security_groups(account_id))

            # Long-stopped instances
            targets.extend(self._find_long_stopped_instances(account_id))

            logger.info(f"Identified {len(targets)} cleanup targets for {account_id}")
            return targets

        except Exception as e:
            logger.error(f"Cleanup target identification failed: {str(e)}")
            return []

    def execute_cleanup(self, resource_id: str, resource_type: str, dry_run: bool = True) -> Dict:
        """
        리소스 정리 실행

        Args:
            resource_id: 리소스 ID
            resource_type: 리소스 타입
            dry_run: True면 미리보기만, False면 실제 삭제

        Returns:
            정리 결과
        """
        cleanup_id = str(uuid.uuid4())

        try:
            result = {
                'cleanup_id': cleanup_id,
                'resource_id': resource_id,
                'resource_type': resource_type,
                'action': 'delete',
                'dry_run': dry_run,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'pending'
            }

            if dry_run:
                # Dry-run: 미리보기만 제공
                result['status'] = 'preview'
                result['message'] = f"Would delete {resource_type} {resource_id}"
                logger.info(f"Cleanup dry-run: {resource_id}")
                return result

            # Actual cleanup
            if resource_type == 'EBS_VOLUME':
                self.ec2.delete_volume(VolumeId=resource_id)
            elif resource_type == 'SNAPSHOT':
                self.ec2.delete_snapshot(SnapshotId=resource_id)
            elif resource_type == 'ELASTIC_IP':
                self.ec2.release_address(AllocationId=resource_id)
            elif resource_type == 'SECURITY_GROUP':
                self.ec2.delete_security_group(GroupId=resource_id)
            elif resource_type == 'INSTANCE':
                self.ec2.terminate_instances(InstanceIds=[resource_id])

            result['status'] = 'success'
            result['message'] = f"Successfully deleted {resource_type} {resource_id}"

            # Log to DynamoDB
            self.table.put_item(Item=result)
            logger.info(f"Cleanup completed: {resource_id}")

            return result

        except Exception as e:
            logger.error(f"Cleanup failed for {resource_id}: {str(e)}")
            result = {
                'cleanup_id': cleanup_id,
                'resource_id': resource_id,
                'resource_type': resource_type,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            return result

    def schedule_cleanup_job(self, account_id: str, schedule: str) -> str:
        """
        정기적 정리 작업 스케줄링

        Args:
            account_id: AWS Account ID
            schedule: 'daily', 'weekly', 'monthly'

        Returns:
            작업 ID
        """
        try:
            job_id = str(uuid.uuid4())

            item = {
                'job_id': job_id,
                'account_id': account_id,
                'schedule': schedule,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'active',
                'last_run': None,
                'next_run': self._calculate_next_run(schedule)
            }

            self.table.put_item(Item=item)
            logger.info(f"Cleanup job scheduled: {job_id} ({schedule})")

            return job_id

        except Exception as e:
            logger.error(f"Schedule cleanup failed: {str(e)}")
            return ""

    def get_cleanup_history(self, account_id: str, days: int = 30) -> List[Dict]:
        """
        정리 작업 이력 조회

        Args:
            account_id: AWS Account ID
            days: 조회 기간 (일)

        Returns:
            정리 이력 목록
        """
        try:
            response = self.table.query(
                KeyConditionExpression='account_id = :acc',
                ExpressionAttributeValues={':acc': account_id},
                Limit=100
            )

            history = response.get('Items', [])

            # Filter by date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            filtered = []

            for item in history:
                timestamp = datetime.fromisoformat(item.get('timestamp', ''))
                if timestamp >= cutoff_date:
                    filtered.append(item)

            logger.info(f"Retrieved {len(filtered)} cleanup records for {account_id}")
            return filtered

        except Exception as e:
            logger.error(f"Failed to retrieve cleanup history: {str(e)}")
            return []

    def _find_unattached_volumes(self, account_id: str) -> List[Dict]:
        """미연결 볼륨 찾기"""
        try:
            response = self.ec2.describe_volumes()
            targets = []

            for volume in response.get('Volumes', []):
                if volume['State'] == 'available':  # Not attached
                    create_time = volume.get('CreateTime', datetime.now(timezone.utc))
                    age_days = (datetime.now(timezone.utc) - create_time).days

                    if age_days > 7:  # 7일 이상 미사용
                        targets.append({
                            'resource_id': volume['VolumeId'],
                            'resource_type': 'EBS_VOLUME',
                            'reason': f'Unattached for {age_days} days',
                            'estimated_savings': volume['Size'] * 0.10,  # $0.10/GB-month
                            'created_date': volume.get('CreateTime', '').isoformat() if hasattr(volume.get('CreateTime'), 'isoformat') else str(volume.get('CreateTime'))
                        })

            return targets

        except Exception as e:
            logger.error(f"Failed to find unattached volumes: {str(e)}")
            return []

    def _find_old_snapshots(self, account_id: str) -> List[Dict]:
        """오래된 스냅샷 찾기"""
        try:
            response = self.ec2.describe_snapshots()
            targets = []

            for snapshot in response.get('Snapshots', []):
                if snapshot['State'] == 'completed':
                    start_time = snapshot.get('StartTime', datetime.now(timezone.utc))
                    age_days = (datetime.now(timezone.utc) - start_time).days

                    if age_days > 90:  # 90일 이상
                        targets.append({
                            'resource_id': snapshot['SnapshotId'],
                            'resource_type': 'SNAPSHOT',
                            'reason': f'Old snapshot ({age_days} days)',
                            'estimated_savings': snapshot['VolumeSize'] * 0.023,  # $0.023/GB-month
                            'created_date': snapshot.get('StartTime', '').isoformat() if hasattr(snapshot.get('StartTime'), 'isoformat') else str(snapshot.get('StartTime'))
                        })

            return targets

        except Exception as e:
            logger.error(f"Failed to find old snapshots: {str(e)}")
            return []

    def _find_unallocated_ips(self, account_id: str) -> List[Dict]:
        """미할당 탄력적 IP 찾기"""
        try:
            response = self.ec2.describe_addresses()
            targets = []

            for address in response.get('Addresses', []):
                if not address.get('AssociationId'):  # Not associated
                    targets.append({
                        'resource_id': address['AllocationId'],
                        'resource_type': 'ELASTIC_IP',
                        'reason': 'Unallocated elastic IP',
                        'estimated_savings': 0.005 * 24 * 30,  # $0.005/hour
                        'created_date': ''
                    })

            return targets

        except Exception as e:
            logger.error(f"Failed to find unallocated IPs: {str(e)}")
            return []

    def _find_empty_security_groups(self, account_id: str) -> List[Dict]:
        """빈 보안 그룹 찾기"""
        try:
            response = self.ec2.describe_security_groups()
            targets = []

            for sg in response.get('SecurityGroups', []):
                # Skip default security group
                if sg['GroupName'] == 'default':
                    continue

                # Check if empty (no instances)
                if not self._has_instances_in_sg(sg['GroupId']):
                    targets.append({
                        'resource_id': sg['GroupId'],
                        'resource_type': 'SECURITY_GROUP',
                        'reason': 'Empty security group (no instances)',
                        'estimated_savings': 0.0,
                        'created_date': ''
                    })

            return targets

        except Exception as e:
            logger.error(f"Failed to find empty security groups: {str(e)}")
            return []

    def _find_long_stopped_instances(self, account_id: str) -> List[Dict]:
        """오래 중지된 인스턴스 찾기"""
        try:
            response = self.ec2.describe_instances()
            targets = []

            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    if instance['State']['Name'] == 'stopped':
                        launch_time = instance.get('LaunchTime', datetime.now(timezone.utc))
                        stopped_days = (datetime.now(timezone.utc) - launch_time).days

                        if stopped_days > 30:
                            targets.append({
                                'resource_id': instance['InstanceId'],
                                'resource_type': 'INSTANCE',
                                'reason': f'Stopped for {stopped_days} days',
                                'estimated_savings': 0.0,
                                'created_date': instance.get('LaunchTime', '').isoformat() if hasattr(instance.get('LaunchTime'), 'isoformat') else str(instance.get('LaunchTime'))
                            })

            return targets

        except Exception as e:
            logger.error(f"Failed to find long-stopped instances: {str(e)}")
            return []

    def _has_instances_in_sg(self, group_id: str) -> bool:
        """보안 그룹에 인스턴스가 있는지 확인"""
        try:
            response = self.ec2.describe_instances(
                Filters=[
                    {
                        'Name': 'instance.group-id',
                        'Values': [group_id]
                    }
                ]
            )
            return len(response.get('Reservations', [])) > 0
        except Exception:
            return False

    def _calculate_next_run(self, schedule: str) -> str:
        """다음 실행 시간 계산"""
        now = datetime.now(timezone.utc)

        if schedule == 'daily':
            next_run = now + timedelta(days=1)
        elif schedule == 'weekly':
            next_run = now + timedelta(weeks=1)
        elif schedule == 'monthly':
            next_run = now + timedelta(days=30)
        else:
            next_run = now + timedelta(days=1)

        return next_run.isoformat()
