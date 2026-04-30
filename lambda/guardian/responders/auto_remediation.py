"""Auto-remediation actions for AWS Guardian Telegram commands"""
import logging
from datetime import datetime, timezone as tz

from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger('auto_remediation')


def remediate_cost_overrun() -> dict:
    results = {
        'action': '요금과다 원인수정',
        'timestamp': datetime.now(tz.utc).isoformat(),
        'steps': [],
        'summary': ''
    }

    try:
        if Config.is_localstack():
            results['steps'].append({
                'name': '비용 상세 분석',
                'detail': 'LocalStack: 일일 $5.50 / 월간 $150.50 (mock)',
                'status': 'analyzed'
            })
            results['steps'].append({
                'name': '상위 비용 서비스 식별',
                'detail': 'LocalStack: EC2(t2.micro x3)가 주요 비용 원인으로 추정',
                'status': 'identified'
            })
            results['steps'].append({
                'name': '비용 임계값 상향 (10→20)',
                'detail': 'SSM /guardian/cost-threshold 를 20.0으로 상향',
                'status': 'done'
            })

            ssm = AWSClientProvider.get_client('ssm')
            ssm.put_parameter(
                Name='/guardian/cost-threshold',
                Value='20.0',
                Type='String',
                Overwrite=True
            )

            results['summary'] = (
                '비용 원인 분석 완료.\n'
                '- 주요 원인: EC2 인스턴스 다수 실행\n'
                '- 임계값을 $10 → $20 상향\n'
                '- 불필요한 인스턴스 중지 권장'
            )
        else:
            ce = AWSClientProvider.get_client('ce')
            today = datetime.now(tz.utc).strftime('%Y-%m-%d')
            yesterday = (datetime.now(tz.utc).replace(hour=0, minute=0, second=0)).strftime('%Y-%m-%d')

            try:
                response = ce.get_cost_and_usage(
                    TimePeriod={'Start': yesterday, 'End': today},
                    Granularity='DAILY',
                    Metrics=['UnblendedCost'],
                    GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
                )

                top_services = []
                if response.get('ResultsByTime'):
                    groups = response['ResultsByTime'][0].get('Groups', [])
                    for g in sorted(groups, key=lambda x: float(x['Metrics']['UnblendedCost']['Amount']), reverse=True)[:3]:
                        top_services.append(f"{g['Keys'][0]}: ${float(g['Metrics']['UnblendedCost']['Amount']):.2f}")

                results['steps'].append({
                    'name': '비용 상세 분석',
                    'detail': '\n'.join(top_services) if top_services else 'No data',
                    'status': 'analyzed'
                })
            except Exception as ce_error:
                logger.warning("Cost Explorer API failed: %s", ce_error)
                results['steps'].append({
                    'name': '비용 상세 분석',
                    'detail': 'Cost Explorer API 조회 실패 (권한 확인)',
                    'status': 'failed'
                })

            try:
                ssm = AWSClientProvider.get_client('ssm')
                current = float(ssm.get_parameter(Name='/guardian/cost-threshold')['Parameter']['Value'])
                new_threshold = current * 2
                ssm.put_parameter(Name='/guardian/cost-threshold', Value=str(new_threshold), Type='String', Overwrite=True)

                results['steps'].append({
                    'name': f'임계값 상향 (${current} → ${new_threshold})',
                    'detail': '반복 알림 방지를 위해 임계값 상향',
                    'status': 'done'
                })

                results['summary'] = (
                    f'비용 원인 분석 완료.\n'
                    f'- 상위 서비스:\n' + '\n'.join(f'  {s}' for s in top_services if top_services) + '\n'
                    f'- 임계값 ${current} → ${new_threshold} 상향\n'
                    f'- 불필요한 리소스 정리 권장'
                )
            except Exception as ssm_error:
                logger.error("SSM parameter update failed: %s", ssm_error)
                results['steps'].append({
                    'name': '임계값 상향',
                    'detail': f'SSM 업데이트 실패: {str(ssm_error)}',
                    'status': 'failed'
                })
                results['summary'] = '일부 단계가 실패했습니다. 콘솔에서 수동 확인 필요.'

    except Exception as e:
        logger.error("Cost remediation error: %s", e)
        results['steps'].append({
            'name': '자동 수정',
            'detail': f'오류: {str(e)}',
            'status': 'failed'
        })
        results['summary'] = f'자동 수정 실패: {str(e)}'

    return results


def remediate_hacking_suspicion() -> dict:
    results = {
        'action': '해킹우려 수정',
        'timestamp': datetime.now(tz.utc).isoformat(),
        'steps': [],
        'summary': ''
    }

    try:
        stopped_instances = []
        blocked_buckets = []

        regions = ['us-east-1'] if Config.is_localstack() else _get_all_regions()

        for region in regions:
            ec2 = AWSClientProvider.get_client('ec2', region=region)

            try:
                response = ec2.describe_instances(
                    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
                )

                instance_ids = []
                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        instance_ids.append(instance['InstanceId'])

                if instance_ids:
                    ec2.stop_instances(InstanceIds=instance_ids)
                    for iid in instance_ids:
                        stopped_instances.append(f"{iid} ({region})")
                        logger.info("Stopped instance: %s in %s", iid, region)
            except Exception as e:
                logger.error("Failed to stop instances in %s: %s", region, e)
                results['steps'].append({
                    'name': f'EC2 중지 ({region})',
                    'detail': str(e),
                    'status': 'failed'
                })

        if stopped_instances:
            results['steps'].append({
                'name': 'EC2 인스턴스 중지',
                'detail': f'{len(stopped_instances)}개 인스턴스 중지: ' + ', '.join(stopped_instances[:5]),
                'status': 'done'
            })

        s3 = AWSClientProvider.get_client('s3')

        try:
            buckets_response = s3.list_buckets()
            for bucket in buckets_response.get('Buckets', []):
                bucket_name = bucket['Name']
                try:
                    s3.put_public_access_block(
                        Bucket=bucket_name,
                        PublicAccessBlockConfiguration={
                            'BlockPublicAcls': True,
                            'IgnorePublicAcls': True,
                            'BlockPublicPolicy': True,
                            'RestrictPublicBuckets': True
                        }
                    )
                    blocked_buckets.append(bucket_name)
                    logger.info("Blocked public access for bucket: %s", bucket_name)
                except Exception as bucket_error:
                    logger.warning("Failed to block public access for %s: %s", bucket_name, bucket_error)

            if blocked_buckets:
                results['steps'].append({
                    'name': 'S3 퍼블릭 액세스 차단',
                    'detail': f'{len(blocked_buckets)}개 버킷 차단: ' + ', '.join(blocked_buckets[:5]),
                    'status': 'done'
                })
        except Exception as s3_error:
            logger.error("S3 list buckets failed: %s", s3_error)
            results['steps'].append({
                'name': 'S3 퍼블릭 액세스 차단',
                'detail': str(s3_error),
                'status': 'failed'
            })

        results['summary'] = (
            f'보안 위협 자동 수정 완료.\n'
            f'- EC2: {len(stopped_instances)}개 인스턴스 중지\n'
            f'- S3: {len(blocked_buckets)}개 버킷 퍼블릭 차단\n'
            f'- Security Group 0.0.0.0/0 규칙은 실 AWS에서 수동 확인 필요'
        )

    except Exception as e:
        logger.error("Hacking suspicion remediation error: %s", e)
        results['steps'].append({
            'name': '자동 수정',
            'detail': f'오류: {str(e)}',
            'status': 'failed'
        })
        results['summary'] = f'자동 수정 실패: {str(e)}'

    return results


def _get_all_regions() -> list:
    ec2 = AWSClientProvider.get_client('ec2')
    response = ec2.describe_regions()
    return [r['RegionName'] for r in response['Regions']]
