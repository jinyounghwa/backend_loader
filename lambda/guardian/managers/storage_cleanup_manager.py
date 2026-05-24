"""스토리지 정리 매니저"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class StorageCleanupManager:
    """EBS 볼륨과 스냅샷 정리 관리자"""

    def __init__(self, ec2_client, dynamodb_table):
        """
        Args:
            ec2_client: boto3 EC2 client
            dynamodb_table: DynamoDB table for cleanup logs
        """
        self.ec2 = ec2_client
        self.table = dynamodb_table

    def delete_unattached_volumes(self, account_id: str, dry_run: bool = True) -> Dict:
        """
        미연결 EBS 볼륨 삭제

        Args:
            account_id: AWS Account ID
            dry_run: True면 미리보기만, False면 실제 삭제

        Returns:
            정리 결과 (삭제된 볼륨 수, 절감액)
        """
        try:
            response = self.ec2.describe_volumes()
            volumes_to_delete = []

            for volume in response.get('Volumes', []):
                if volume['State'] == 'available':  # Not attached
                    create_time = volume.get('CreateTime')
                    if isinstance(create_time, str):
                        create_time = datetime.fromisoformat(create_time.replace('Z', '+00:00'))

                    age_days = (datetime.now(timezone.utc) - create_time).days

                    if age_days >= 7:  # 7일 이상 미사용
                        volumes_to_delete.append({
                            'volume_id': volume['VolumeId'],
                            'size_gb': volume['Size'],
                            'age_days': age_days,
                            'estimated_savings': volume['Size'] * 0.10
                        })

            # Dry-run or actual delete
            deleted_count = 0
            total_savings = 0.0

            if dry_run:
                deleted_count = len(volumes_to_delete)
                total_savings = sum(v['estimated_savings'] for v in volumes_to_delete)
                logger.info(f"Dry-run: Would delete {deleted_count} volumes, saving ${total_savings:.2f}/month")
            else:
                for volume in volumes_to_delete:
                    try:
                        self.ec2.delete_volume(VolumeId=volume['volume_id'])
                        deleted_count += 1
                        total_savings += volume['estimated_savings']
                    except Exception as e:
                        logger.error(f"Failed to delete volume {volume['volume_id']}: {str(e)}")

                # Log to DynamoDB
                if deleted_count > 0:
                    self.table.put_item(Item={
                        'action': 'delete_unattached_volumes',
                        'account_id': account_id,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'deleted_count': deleted_count,
                        'total_savings': total_savings
                    })

            logger.info(f"Unattached volumes cleanup: {deleted_count} deleted, ${total_savings:.2f} saved")

            return {
                'deleted_count': deleted_count,
                'total_savings': total_savings,
                'dry_run': dry_run
            }

        except Exception as e:
            logger.error(f"Failed to delete unattached volumes: {str(e)}")
            return {'deleted_count': 0, 'total_savings': 0.0, 'error': str(e)}

    def delete_old_snapshots(self, account_id: str, days_threshold: int = 90) -> Dict:
        """
        오래된 스냅샷 삭제

        Args:
            account_id: AWS Account ID
            days_threshold: 스냅샷 나이 임계값 (일)

        Returns:
            정리 결과
        """
        try:
            response = self.ec2.describe_snapshots()
            snapshots_to_delete = []

            for snapshot in response.get('Snapshots', []):
                if snapshot['State'] == 'completed':
                    start_time = snapshot.get('StartTime')
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

                    age_days = (datetime.now(timezone.utc) - start_time).days

                    if age_days > days_threshold:
                        snapshots_to_delete.append({
                            'snapshot_id': snapshot['SnapshotId'],
                            'size_gb': snapshot['VolumeSize'],
                            'age_days': age_days,
                            'estimated_savings': snapshot['VolumeSize'] * 0.023
                        })

            deleted_count = 0
            total_savings = 0.0

            for snapshot in snapshots_to_delete:
                try:
                    self.ec2.delete_snapshot(SnapshotId=snapshot['snapshot_id'])
                    deleted_count += 1
                    total_savings += snapshot['estimated_savings']
                except Exception as e:
                    logger.error(f"Failed to delete snapshot {snapshot['snapshot_id']}: {str(e)}")

            if deleted_count > 0:
                self.table.put_item(Item={
                    'action': 'delete_old_snapshots',
                    'account_id': account_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'deleted_count': deleted_count,
                    'total_savings': total_savings
                })

            logger.info(f"Old snapshots cleanup: {deleted_count} deleted, ${total_savings:.2f} saved")

            return {
                'deleted_count': deleted_count,
                'total_savings': total_savings,
                'threshold_days': days_threshold
            }

        except Exception as e:
            logger.error(f"Failed to delete old snapshots: {str(e)}")
            return {'deleted_count': 0, 'total_savings': 0.0, 'error': str(e)}

    def cleanup_orphaned_snapshots(self, account_id: str) -> Dict:
        """
        소스 볼륨이 없는 고아 스냅샷 정리

        Args:
            account_id: AWS Account ID

        Returns:
            정리 결과
        """
        try:
            # Get all snapshots
            snapshots_response = self.ec2.describe_snapshots()
            all_snapshots = snapshots_response.get('Snapshots', [])

            # Get all volumes
            volumes_response = self.ec2.describe_volumes()
            volume_ids = {v['VolumeId'] for v in volumes_response.get('Volumes', [])}

            # Find orphaned snapshots
            orphaned = []
            for snapshot in all_snapshots:
                source_volume = snapshot.get('VolumeId')
                if source_volume and source_volume not in volume_ids:
                    orphaned.append({
                        'snapshot_id': snapshot['SnapshotId'],
                        'size_gb': snapshot['VolumeSize'],
                        'estimated_savings': snapshot['VolumeSize'] * 0.023
                    })

            deleted_count = 0
            total_savings = 0.0

            for snapshot in orphaned:
                try:
                    self.ec2.delete_snapshot(SnapshotId=snapshot['snapshot_id'])
                    deleted_count += 1
                    total_savings += snapshot['estimated_savings']
                except Exception as e:
                    logger.error(f"Failed to delete orphaned snapshot {snapshot['snapshot_id']}: {str(e)}")

            if deleted_count > 0:
                self.table.put_item(Item={
                    'action': 'cleanup_orphaned_snapshots',
                    'account_id': account_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'deleted_count': deleted_count,
                    'total_savings': total_savings
                })

            logger.info(f"Orphaned snapshots cleanup: {deleted_count} deleted, ${total_savings:.2f} saved")

            return {
                'deleted_count': deleted_count,
                'total_savings': total_savings,
                'orphaned_count': len(orphaned)
            }

        except Exception as e:
            logger.error(f"Failed to cleanup orphaned snapshots: {str(e)}")
            return {'deleted_count': 0, 'total_savings': 0.0, 'error': str(e)}

    def estimate_storage_savings(self, account_id: str) -> Dict:
        """
        정리로 절감될 스토리지 비용 예상

        Args:
            account_id: AWS Account ID

        Returns:
            절감액 예상 정보
        """
        try:
            volume_savings = 0.0
            snapshot_savings = 0.0

            # Estimate unattached volume savings
            volumes_response = self.ec2.describe_volumes()
            for volume in volumes_response.get('Volumes', []):
                if volume['State'] == 'available':
                    create_time = volume.get('CreateTime')
                    if isinstance(create_time, str):
                        create_time = datetime.fromisoformat(create_time.replace('Z', '+00:00'))

                    age_days = (datetime.now(timezone.utc) - create_time).days
                    if age_days >= 7:
                        volume_savings += volume['Size'] * 0.10

            # Estimate old snapshot savings
            snapshots_response = self.ec2.describe_snapshots()
            for snapshot in snapshots_response.get('Snapshots', []):
                if snapshot['State'] == 'completed':
                    start_time = snapshot.get('StartTime')
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

                    age_days = (datetime.now(timezone.utc) - start_time).days
                    if age_days > 90:
                        snapshot_savings += snapshot['VolumeSize'] * 0.023

            total_savings = volume_savings + snapshot_savings

            logger.info(f"Storage savings estimate: ${total_savings:.2f}/month (volumes: ${volume_savings:.2f}, snapshots: ${snapshot_savings:.2f})")

            return {
                'total_savings': total_savings,
                'volume_savings': volume_savings,
                'snapshot_savings': snapshot_savings,
                'currency': 'USD',
                'period': 'monthly'
            }

        except Exception as e:
            logger.error(f"Failed to estimate storage savings: {str(e)}")
            return {'total_savings': 0.0, 'error': str(e)}
