"""정리 작업 감사 로거"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class CleanupAuditLogger:
    """정리 작업의 모든 활동을 감사하고 추적"""

    def __init__(self, dynamodb_table):
        """
        Args:
            dynamodb_table: DynamoDB table for audit logs
        """
        self.table = dynamodb_table

    def log_cleanup_action(self, account_id: str, action: Dict) -> None:
        """
        정리 작업 기록

        Args:
            account_id: AWS Account ID
            action: 정리 작업 정보
                - resource_id: 리소스 ID
                - resource_type: 리소스 타입 (EBS_VOLUME, SNAPSHOT, ELASTIC_IP, SECURITY_GROUP, INSTANCE)
                - action: 작업 종류 (delete, stop, terminate, etc.)
                - status: 상태 (success, failed)
                - savings: 절감액
        """
        try:
            audit_entry = {
                'account_id': account_id,
                'cleanup_id': action.get('cleanup_id'),
                'resource_id': action.get('resource_id'),
                'resource_type': action.get('resource_type'),
                'action': action.get('action'),
                'status': action.get('status'),
                'savings': action.get('savings', 0.0),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'details': action.get('details', {})
            }

            self.table.put_item(Item=audit_entry)

            logger.info(f"Logged cleanup action: {action.get('action')} on {action.get('resource_id')}")

        except Exception as e:
            logger.error(f"Failed to log cleanup action: {str(e)}")

    def get_cleanup_summary(self, account_id: str, days: int = 30) -> Dict:
        """
        기간별 정리 작업 요약

        Args:
            account_id: AWS Account ID
            days: 조회 기간 (일)

        Returns:
            정리 작업 요약 정보
                - total_resources_cleaned: 정리된 리소스 수
                - total_savings: 절감액 합계
                - success_count: 성공한 작업 수
                - failed_count: 실패한 작업 수
                - by_resource_type: 리소스 타입별 정리 건수
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            response = self.table.query(
                KeyConditionExpression='account_id = :acc',
                ExpressionAttributeValues={':acc': account_id}
            )

            items = response.get('Items', [])

            # Filter by date
            filtered = []
            for item in items:
                timestamp = datetime.fromisoformat(item.get('timestamp', ''))
                if timestamp >= cutoff:
                    filtered.append(item)

            # Calculate summary
            summary = {
                'account_id': account_id,
                'period_days': days,
                'total_resources_cleaned': 0,
                'total_savings': 0.0,
                'success_count': 0,
                'failed_count': 0,
                'by_resource_type': {},
                'by_status': {}
            }

            for item in filtered:
                summary['total_savings'] += item.get('savings', 0.0)

                status = item.get('status', 'unknown')
                summary['by_status'][status] = summary['by_status'].get(status, 0) + 1

                if status == 'success':
                    summary['success_count'] += 1
                    summary['total_resources_cleaned'] += 1
                else:
                    summary['failed_count'] += 1

                resource_type = item.get('resource_type', 'unknown')
                summary['by_resource_type'][resource_type] = summary['by_resource_type'].get(resource_type, 0) + 1

            # Calculate success rate
            total = summary['success_count'] + summary['failed_count']
            if total > 0:
                summary['success_rate'] = (summary['success_count'] / total) * 100
            else:
                summary['success_rate'] = 0.0

            logger.info(f"Cleanup summary for {account_id}: {summary['total_resources_cleaned']} resources, ${summary['total_savings']:.2f} saved")

            return summary

        except Exception as e:
            logger.error(f"Failed to get cleanup summary: {str(e)}")
            return {
                'account_id': account_id,
                'total_resources_cleaned': 0,
                'total_savings': 0.0,
                'error': str(e)
            }

    def generate_cleanup_report(self, account_id: str, days: int = 30) -> Dict:
        """
        정기 정리 보고서 생성

        Args:
            account_id: AWS Account ID
            days: 보고 기간 (일)

        Returns:
            정리 보고서
        """
        try:
            summary = self.get_cleanup_summary(account_id, days)

            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            report_date = datetime.now(timezone.utc)

            report = {
                'account_id': account_id,
                'report_date': report_date.isoformat(),
                'period': f"{cutoff.date()} to {report_date.date()}",
                'period_days': days,
                'total_resources_cleaned': summary['total_resources_cleaned'],
                'total_savings': summary['total_savings'],
                'success_rate': summary['success_rate'],
                'success_count': summary['success_count'],
                'failed_count': summary['failed_count'],
                'by_resource_type': summary['by_resource_type'],
                'by_status': summary['by_status']
            }

            # Calculate monthly projection
            if days > 0:
                daily_savings = summary['total_savings'] / days
                report['monthly_projection'] = daily_savings * 30
                report['yearly_projection'] = daily_savings * 365
            else:
                report['monthly_projection'] = 0.0
                report['yearly_projection'] = 0.0

            logger.info(f"Generated cleanup report for {account_id}")

            return report

        except Exception as e:
            logger.error(f"Failed to generate cleanup report: {str(e)}")
            return {'account_id': account_id, 'error': str(e)}

    def log_rollback_action(self, account_id: str, cleanup_id: str, resource_id: str, reason: str = None) -> None:
        """
        정리 작업 롤백 기록

        Args:
            account_id: AWS Account ID
            cleanup_id: 원래 정리 작업 ID
            resource_id: 리소스 ID
            reason: 롤백 사유
        """
        try:
            rollback_entry = {
                'account_id': account_id,
                'cleanup_id': cleanup_id,
                'resource_id': resource_id,
                'action': 'rollback',
                'status': 'success',
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            self.table.put_item(Item=rollback_entry)

            logger.info(f"Logged rollback for {resource_id}: {reason}")

        except Exception as e:
            logger.error(f"Failed to log rollback action: {str(e)}")

    def get_audit_logs(self, account_id: str, resource_type: str = None, days: int = 30) -> List[Dict]:
        """
        감사 로그 조회

        Args:
            account_id: AWS Account ID
            resource_type: 리소스 타입 필터 (선택사항)
            days: 조회 기간 (일)

        Returns:
            감사 로그 목록
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            response = self.table.query(
                KeyConditionExpression='account_id = :acc',
                ExpressionAttributeValues={':acc': account_id}
            )

            items = response.get('Items', [])

            # Filter by date and resource type
            filtered = []
            for item in items:
                timestamp = datetime.fromisoformat(item.get('timestamp', ''))
                if timestamp >= cutoff:
                    if resource_type is None or item.get('resource_type') == resource_type:
                        filtered.append(item)

            logger.info(f"Retrieved {len(filtered)} audit logs for {account_id}")

            return filtered

        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {str(e)}")
            return []
