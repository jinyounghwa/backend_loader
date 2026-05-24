"""EC2 인스턴스 생명주기 관리자"""

import logging
import uuid
from typing import Dict, List
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class EC2LifecycleManager:
    """EC2 인스턴스 생명주기 자동 관리"""

    def __init__(self, ec2_client, cloudwatch_client, dynamodb_table):
        """
        Args:
            ec2_client: boto3 EC2 client
            cloudwatch_client: boto3 CloudWatch client
            dynamodb_table: DynamoDB table for lifecycle logs
        """
        self.ec2 = ec2_client
        self.cloudwatch = cloudwatch_client
        self.table = dynamodb_table

    def detect_idle_instances(self, account_id: str, cpu_threshold: float = 5) -> List[Dict]:
        """
        유휴 인스턴스 감지

        Args:
            account_id: AWS Account ID
            cpu_threshold: CPU 사용률 임계값 (%)

        Returns:
            유휴 인스턴스 목록
        """
        try:
            response = self.ec2.describe_instances()
            idle_instances = []

            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    if instance['State']['Name'] != 'running':
                        continue

                    instance_id = instance['InstanceId']

                    # Get CPU metrics
                    try:
                        metrics = self.cloudwatch.get_metric_statistics(
                            Namespace='AWS/EC2',
                            MetricName='CPUUtilization',
                            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                            StartTime=datetime.now(timezone.utc) - timedelta(hours=24),
                            EndTime=datetime.now(timezone.utc),
                            Period=3600,
                            Statistics=['Average']
                        )

                        datapoints = metrics.get('Datapoints', [])
                        if datapoints:
                            avg_cpu = sum(d['Average'] for d in datapoints) / len(datapoints)

                            if avg_cpu < cpu_threshold:
                                # Check if production
                                tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
                                is_production = tags.get('Environment') == 'production'

                                if not is_production:
                                    idle_instances.append({
                                        'instance_id': instance_id,
                                        'avg_cpu': avg_cpu,
                                        'threshold': cpu_threshold,
                                        'is_idle': True,
                                        'environment': tags.get('Environment', 'unknown')
                                    })
                    except Exception as e:
                        logger.error(f"Failed to get metrics for {instance_id}: {str(e)}")

            logger.info(f"Detected {len(idle_instances)} idle instances")
            return idle_instances

        except Exception as e:
            logger.error(f"Failed to detect idle instances: {str(e)}")
            return []

    def stop_idle_instances(self, account_id: str, cpu_threshold: float = 5) -> Dict:
        """
        유휴 인스턴스 자동 중지

        Args:
            account_id: AWS Account ID
            cpu_threshold: CPU 사용률 임계값 (%)

        Returns:
            중지 결과
        """
        try:
            idle_instances = self.detect_idle_instances(account_id, cpu_threshold)
            stopped_count = 0

            for instance in idle_instances:
                try:
                    self.ec2.stop_instances(InstanceIds=[instance['instance_id']])
                    stopped_count += 1

                    # Log to DynamoDB
                    self.table.put_item(Item={
                        'action': 'stop_idle_instance',
                        'account_id': account_id,
                        'instance_id': instance['instance_id'],
                        'cpu_utilization': instance['avg_cpu'],
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'status': 'success'
                    })

                except Exception as e:
                    logger.error(f"Failed to stop instance {instance['instance_id']}: {str(e)}")

            logger.info(f"Stopped {stopped_count} idle instances")

            return {
                'stopped_count': stopped_count,
                'total_candidates': len(idle_instances)
            }

        except Exception as e:
            logger.error(f"Failed to stop idle instances: {str(e)}")
            return {'stopped_count': 0, 'error': str(e)}

    def terminate_stopped_instances(self, account_id: str, days_stopped: int = 30) -> Dict:
        """
        장시간 중지된 인스턴스 종료

        Args:
            account_id: AWS Account ID
            days_stopped: 중지된 지 몇 일 이상인지 (일)

        Returns:
            종료 결과
        """
        try:
            response = self.ec2.describe_instances()
            instances_to_terminate = []
            now = datetime.now(timezone.utc)

            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    if instance['State']['Name'] == 'stopped':
                        launch_time = instance.get('LaunchTime')
                        if isinstance(launch_time, str):
                            launch_time = datetime.fromisoformat(launch_time.replace('Z', '+00:00'))

                        age_days = (now - launch_time).days

                        if age_days > days_stopped:
                            instances_to_terminate.append({
                                'instance_id': instance['InstanceId'],
                                'age_days': age_days
                            })

            terminated_count = 0

            for instance in instances_to_terminate:
                try:
                    self.ec2.terminate_instances(InstanceIds=[instance['instance_id']])
                    terminated_count += 1

                    self.table.put_item(Item={
                        'action': 'terminate_stopped_instance',
                        'account_id': account_id,
                        'instance_id': instance['instance_id'],
                        'stopped_days': instance['age_days'],
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'status': 'success'
                    })

                except Exception as e:
                    logger.error(f"Failed to terminate instance {instance['instance_id']}: {str(e)}")

            logger.info(f"Terminated {terminated_count} long-stopped instances")

            return {
                'terminated_count': terminated_count,
                'total_candidates': len(instances_to_terminate),
                'threshold_days': days_stopped
            }

        except Exception as e:
            logger.error(f"Failed to terminate stopped instances: {str(e)}")
            return {'terminated_count': 0, 'error': str(e)}

    def tag_idle_instances(self, account_id: str) -> Dict:
        """
        유휴 인스턴스 태깅

        Args:
            account_id: AWS Account ID

        Returns:
            태깅 결과
        """
        try:
            idle_instances = self.detect_idle_instances(account_id)
            tagged_count = 0

            now = datetime.now(timezone.utc)

            for instance in idle_instances:
                try:
                    self.ec2.create_tags(
                        Resources=[instance['instance_id']],
                        Tags=[
                            {
                                'Key': 'LastIdleDetection',
                                'Value': now.isoformat()
                            },
                            {
                                'Key': 'IdleReason',
                                'Value': f"CPU usage {instance['avg_cpu']:.1f}% < {instance['threshold']}%"
                            }
                        ]
                    )
                    tagged_count += 1
                except Exception as e:
                    logger.error(f"Failed to tag instance {instance['instance_id']}: {str(e)}")

            logger.info(f"Tagged {tagged_count} idle instances")

            return {
                'tagged_count': tagged_count,
                'total_candidates': len(idle_instances)
            }

        except Exception as e:
            logger.error(f"Failed to tag idle instances: {str(e)}")
            return {'tagged_count': 0, 'error': str(e)}

    def schedule_instance_shutdown(self, instance_id: str, schedule_time: str) -> str:
        """
        특정 시간에 인스턴스 중지 스케줄

        Args:
            instance_id: EC2 Instance ID
            schedule_time: ISO 8601 형식 시간

        Returns:
            스케줄 ID
        """
        try:
            schedule_id = str(uuid.uuid4())

            # Parse schedule time
            try:
                scheduled = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"Invalid schedule time format: {schedule_time}")

            self.table.put_item(Item={
                'schedule_id': schedule_id,
                'instance_id': instance_id,
                'action': 'stop',
                'scheduled_time': schedule_time,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'pending'
            })

            logger.info(f"Scheduled shutdown for {instance_id} at {schedule_time}")

            return schedule_id

        except Exception as e:
            logger.error(f"Failed to schedule shutdown: {str(e)}")
            return ""

    def get_lifecycle_history(self, account_id: str, days: int = 30) -> List[Dict]:
        """
        생명주기 작업 이력 조회

        Args:
            account_id: AWS Account ID
            days: 조회 기간 (일)

        Returns:
            작업 이력 목록
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            response = self.table.query(
                KeyConditionExpression='account_id = :acc',
                ExpressionAttributeValues={':acc': account_id}
            )

            history = response.get('Items', [])

            # Filter by date
            filtered = []
            for item in history:
                timestamp = datetime.fromisoformat(item.get('timestamp', ''))
                if timestamp >= cutoff:
                    filtered.append(item)

            logger.info(f"Retrieved {len(filtered)} lifecycle records")
            return filtered

        except Exception as e:
            logger.error(f"Failed to retrieve lifecycle history: {str(e)}")
            return []
