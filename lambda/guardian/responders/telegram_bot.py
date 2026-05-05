"""Telegram bot listener - polls for user commands and executes auto-remediation"""
import os
import re
import sys
import time
import logging
import signal
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from guardian.responders.telegram import TelegramResponder
from guardian.responders.auto_remediation import remediate_cost_overrun, remediate_hacking_suspicion
from guardian.responders.aws_action_executor import AWSActionExecutor
from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider
from guardian.storage.dynamodb import DynamoDBStorage

logger = logging.getLogger('telegram_bot')

COMMANDS = {
    '요금과다 원인수정': remediate_cost_overrun,
    '해킹우려 수정': remediate_hacking_suspicion,
}

INSTANCE_ID_RE = re.compile(r'^i-[0-9a-f]{8,17}$')


def get_status() -> dict:
    try:
        ec2 = AWSClientProvider.get_client('ec2')
        s3 = AWSClientProvider.get_client('s3')

        ec2_response = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        running_instances = sum(
            len(r.get('Instances', []))
            for r in ec2_response.get('Reservations', [])
        )

        s3_response = s3.list_buckets()
        total_buckets = len(s3_response.get('Buckets', []))

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'ec2_running': running_instances,
            's3_buckets': total_buckets,
            'threshold': Config.get_cost_threshold()
        }
    except Exception as e:
        logger.error("Error getting status: %s", e)
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def get_instances() -> dict:
    try:
        ec2 = AWSClientProvider.get_client('ec2')

        response = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )

        instances = []
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instances.append({
                    'instance_id': instance['InstanceId'],
                    'instance_type': instance['InstanceType'],
                    'state': instance['State']['Name'],
                    'launch_time': instance['LaunchTime'].isoformat() if 'LaunchTime' in instance else 'N/A'
                })

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'instances': instances,
            'count': len(instances)
        }
    except Exception as e:
        logger.error("Error getting instances: %s", e)
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def stop_instance(instance_id: str) -> dict:
    if not INSTANCE_ID_RE.match(instance_id):
        return {'error': f'Invalid instance ID format: {instance_id}', 'timestamp': datetime.now(timezone.utc).isoformat()}
    try:
        ec2 = AWSClientProvider.get_client('ec2')
        ec2.stop_instances(InstanceIds=[instance_id])

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': 'stop_instance',
            'instance_id': instance_id,
            'status': 'stopped'
        }
    except Exception as e:
        logger.error("Error stopping instance %s: %s", instance_id, e)
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def set_threshold(amount: str) -> dict:
    try:
        threshold = float(amount)
        if threshold <= 0 or threshold > 1000000:
            return {'error': 'Amount must be between $0.01 and $1,000,000', 'timestamp': datetime.now(timezone.utc).isoformat()}
        ssm = AWSClientProvider.get_client('ssm')

        ssm.put_parameter(
            Name='/guardian/cost-threshold',
            Value=str(threshold),
            Type='String',
            Overwrite=True
        )

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': 'set_threshold',
            'new_threshold': threshold,
            'status': 'success'
        }
    except ValueError:
        return {'error': 'Invalid amount', 'timestamp': datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.error("Error setting threshold: %s", e)
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def get_history(hours: int = 24) -> dict:
    try:
        storage = DynamoDBStorage()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        items = storage.get_latest_check_result(time_filter=since)

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'hours': hours,
            'events': items if items else [],
            'count': len(items) if items else 0
        }
    except Exception as e:
        logger.error("Error getting history: %s", e)
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def remediate_finding(finding_id: str) -> dict:
    if not re.match(r'^finding-[a-f0-9\-]+$', finding_id):
        return {'error': f'Invalid finding ID format: {finding_id}'}

    storage = DynamoDBStorage()
    try:

        existing = storage.get_item_by_id(finding_id)
        if existing and existing.get('remediation_status') == 'InProgress':
            return {
                'action': 'remediate',
                'finding_id': finding_id,
                'status': 'in_progress',
                'message': '이미 진행 중인 대응입니다. 잠시 후 다시 확인하세요.'
            }
        if existing and existing.get('remediation_status') == 'Completed':
            return {
                'action': 'remediate',
                'finding_id': finding_id,
                'status': 'completed',
                'message': f'이미 완료됨. 결과: {existing.get("remediation_result", "성공")}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        storage.update_remediation_status(finding_id, 'InProgress')

        result = _execute_remediation(finding_id, existing or {})

        storage.update_remediation_status(finding_id, 'Completed', result['action'])

        return {
            'action': 'remediate',
            'finding_id': finding_id,
            'status': 'success',
            'message': result['message'],
            'result': result['action'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error("Error remediating finding %s: %s", finding_id, e)
        try:
            storage.update_remediation_status(finding_id, 'Failed', str(e))
        except Exception as update_err:
            logger.warning("Failed to update remediation status for %s: %s", finding_id, update_err)
        return {'error': f'대응 실행 실패: {str(e)}'}


def _execute_remediation(finding_id: str, finding_data: dict) -> dict:
    resource_type = finding_data.get('resource_type', 'unknown')
    resource_id = finding_data.get('resource_id', '')
    executor = AWSActionExecutor()

    if resource_type == 'EC2':
        region = finding_data.get('region', 'us-east-1')
        success = executor.stop_ec2_instance(resource_id, region)
        return {
            'action': 'stopped' if success else 'failed',
            'message': f'{"✅" if success else "❌"} EC2 인스턴스 {resource_id} {"중지됨" if success else "중지 실패"}',
        }
    elif resource_type == 'S3':
        success = executor.block_s3_public_access(resource_id)
        return {
            'action': 'blocked' if success else 'failed',
            'message': f'{"✅" if success else "❌"} S3 버킷 {resource_id} 퍼블릭 액세스 {"차단됨" if success else "차단 실패"}',
        }
    else:
        return {'action': 'logged', 'message': f'✅ 발견사항 {finding_id} 기록됨'}


def export_events(format_str: str, days: int = 7, severity: Optional[str] = None) -> dict:
    """Handle /export {csv|pdf|json} command (Gemini recommended memory optimization)"""
    from guardian.reporters.event_exporter import EventExporter, query_events_with_pagination

    # Strict format validation
    if not EventExporter.validate_format(format_str):
        return {'error': 'Invalid format. Must be: csv, pdf, or json'}

    try:
        storage = DynamoDBStorage()
        events = query_events_with_pagination(
            storage.table,
            severity_filter=severity,
            days=days,
            limit=500
        )

        if not events:
            return {'error': f'No events found for past {days} days'}

        summary = {
            'total_events': len(events),
            'by_severity': {},
            'by_type': {}
        }
        for event in events:
            summary['by_severity'][event.get('severity', 'UNKNOWN')] = \
                summary['by_severity'].get(event.get('severity'), 0) + 1
            summary['by_type'][event.get('event_type', 'unknown')] = \
                summary['by_type'].get(event.get('event_type'), 0) + 1

        file_path, content = EventExporter.export_events(events, format_str, summary)

        return {
            'action': 'export',
            'format': format_str,
            'file_path': file_path,
            'event_count': len(events),
            'size_bytes': len(content) if isinstance(content, (str, bytes)) else 0,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error("Error exporting events: %s", e)
        return {'error': f'보고서 생성 실패: {str(e)}'}


def analyze_threats() -> dict:
    """Handle /insights command (Gemini AI threat analysis with caching)"""
    from guardian.analyzers.gemini_threat_analyzer import GeminiThreatAnalyzer
    from guardian.reporters.event_exporter import query_events_with_pagination

    try:
        storage = DynamoDBStorage()

        # Collect events from past 24 hours
        events = query_events_with_pagination(storage.table, days=1, limit=1000)

        if not events:
            return {'analysis': '지난 24시간 위협 이벤트가 없습니다.'}

        # Prepare summary
        summary = {
            'total_events': len(events),
            'by_severity': {},
            'by_type': {},
            'affected_resources': set()
        }

        for event in events:
            severity = event.get('severity', 'UNKNOWN')
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1

            event_type = event.get('event_type', 'unknown')
            summary['by_type'][event_type] = summary['by_type'].get(event_type, 0) + 1

            if 'resource_id' in event:
                summary['affected_resources'].add(event['resource_id'])

        summary['affected_resources'] = list(summary['affected_resources'])[:5]

        # Get Gemini analysis (with caching and fallback)
        api_key = os.getenv('GEMINI_API_KEY')
        analyzer = GeminiThreatAnalyzer(api_key)
        analysis = analyzer.analyze_threats(summary)

        return {
            'action': 'insights',
            'analysis': analysis,
            'event_count': len(events),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error("Error analyzing threats: %s", e)
        return {'error': f'분석 실패: {str(e)}'}


class TelegramBotListener:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.last_update_id = 0
        self.running = True
        self.telegram = TelegramResponder()

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info("Shutdown signal received. Stopping...")
        self.running = False

    def get_updates(self):
        try:
            response = requests.get(
                f"{self.api_url}/getUpdates",
                params={'offset': self.last_update_id + 1, 'timeout': 30},
                timeout=35
            )
            if response.status_code == 200:
                return response.json().get('result', [])
        except requests.exceptions.ReadTimeout:
            return []
        except Exception as e:
            logger.error("Error polling updates: %s", e)
            time.sleep(5)
        return []

    def parse_command(self, text: str):
        if not text:
            return None
        text = text.strip()

        if text in COMMANDS:
            return COMMANDS[text], text

        if text.startswith('/'):
            parts = text.split()
            command = parts[0].lstrip('/')
            args = ' '.join(parts[1:]) if len(parts) > 1 else None

            if command == 'status':
                return get_status, '/status'
            elif command == 'instances':
                return get_instances, '/instances'
            elif command == 'stop' and args:
                return lambda: stop_instance(args), f'/stop {args}'
            elif command == 'threshold' and args:
                return lambda: set_threshold(args), f'/threshold {args}'
            elif command == 'history':
                try:
                    hours = int(args) if args else 24
                    return lambda: get_history(hours), f'/history {hours}'
                except ValueError:
                    return lambda: get_history(), '/history'
            # Sprint 9: New advanced commands
            elif command == 'remediate' and args:
                return lambda: remediate_finding(args), f'/remediate {args}'
            elif command == 'export':
                format_match = re.search(r'\b(csv|pdf|json)\b', text)
                days_match = re.search(r'--days\s+(\d+)', text)
                severity_match = re.search(r'--severity\s+(\w+)', text)

                fmt = format_match.group(1) if format_match else 'csv'
                days = int(days_match.group(1)) if days_match else 7
                severity = severity_match.group(1) if severity_match else None

                return lambda: export_events(fmt, days, severity), f'/export {fmt} --days {days}'
            elif command == 'insights':
                return analyze_threats, '/insights'
            elif command == 'help':
                return self._show_help, '/help'

        for keyword, handler in COMMANDS.items():
            if keyword in text:
                return handler, keyword

        return None

    def _show_help(self) -> dict:
        help_text = """
<b>📖 AWS Guardian 명령어</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>상태 조회:</b>
/status - 현재 EC2, S3, 비용 상태
/instances - 실행 중인 인스턴스 목록
/history [시간] - 최근 이벤트 로그 (기본 24시간)

<b>제어 명령:</b>
/stop <instance-id> - 특정 인스턴스 중지
/threshold <금액> - 비용 임계값 변경 (달러)

<b>자동 수정:</b>
요금과다 원인수정 - 비용 과다 자동 분석 및 수정
해킹우려 수정 - 보안 위협 자동 대응

<b>🔄 Sprint 9: 고급 명령어</b>
/remediate <finding-id> - GuardDuty 발견사항 자동 대응
/export [csv|pdf|json] --days 7 - 이벤트 보고서 생성
/insights - AI 위협 분석 (Gemini)

/help - 이 도움말 표시
"""
        self.telegram.send_message(help_text)
        return {'action': 'help', 'status': 'sent'}

    def handle_message(self, message: dict):
        chat_id = str(message.get('chat', {}).get('id', ''))
        text = message.get('text', '')
        from_user = message.get('from', {}).get('first_name', 'User')

        if self.chat_id and chat_id != self.chat_id:
            return

        parsed = self.parse_command(text)
        if not parsed:
            return

        handler, command_text = parsed
        logger.info("Command received from %s: %s", from_user, command_text)

        try:
            result = handler()
            self._format_response(result, command_text)
        except Exception as e:
            logger.error("Command error: %s", e)
            self.telegram.send_message(f"❌ <b>명령 실패</b>\n명령: {command_text}\n오류: {str(e)}")

    def _format_response(self, result: dict, command_text: str):
        if 'error' in result:
            self.telegram.send_message(f"❌ <b>오류</b>\n{result['error']}")
            return

        if 'steps' in result:
            lines = [
                "✅ <b>자동 수정 완료</b>",
                f"📋 명령: {command_text}",
                f"🕐 시간: {result['timestamp'][:10]}",
                "",
                "<b>실행 내역:</b>",
            ]

            for step in result.get('steps', []):
                status_icon = "✅" if step['status'] == 'done' else "🔍" if step['status'] == 'analyzed' else "❌"
                lines.append(f"{status_icon} {step['name']}")
                lines.append(f"   └ {step['detail']}")

            lines.append("")
            lines.append("<b>요약:</b>")
            lines.append(result.get('summary', '완료'))

            self.telegram.send_message('\n'.join(lines))

        elif 'ec2_running' in result:
            threshold_icon = "🟢" if result.get('today_cost', 0) < result['threshold'] else "🔴"
            lines = [
                "<b>📊 현재 상태</b>",
                "━━━━━━━━━━━━━━━━━━━",
                f"🖥️  EC2: {result['ec2_running']}개 실행 중",
                f"🪣 S3: {result['s3_buckets']}개 버킷",
                f"{threshold_icon} 임계값: ${result['threshold']:.2f}",
                "━━━━━━━━━━━━━━━━━━━",
            ]
            self.telegram.send_message('\n'.join(lines))

        elif 'instances' in result and result.get('count', 0) > 0:
            lines = [
                f"<b>🖥️  실행 중인 인스턴스 ({result['count']})</b>",
                "━━━━━━━━━━━━━━━━━━━",
            ]
            for inst in result['instances'][:10]:
                lines.append(f"• <code>{inst['instance_id']}</code>")
                lines.append(f"  타입: {inst['instance_type']} | 상태: {inst['state']}")
            if result['count'] > 10:
                lines.append(f"\n... 외 {result['count'] - 10}개")
            lines.append("━━━━━━━━━━━━━━━━━━━")
            self.telegram.send_message('\n'.join(lines))
        elif 'instances' in result:
            self.telegram.send_message("✅ 실행 중인 인스턴스가 없습니다.")

        elif result.get('action') == 'stop_instance':
            self.telegram.send_message(f"✅ <b>인스턴스 중지</b>\nID: <code>{result['instance_id']}</code>\n상태: {result['status']}")

        elif result.get('action') == 'set_threshold':
            self.telegram.send_message(f"✅ <b>임계값 변경</b>\n새 임계값: ${result['new_threshold']:.2f}")

        elif 'events' in result and result.get('count', 0) > 0:
            lines = [
                f"<b>📜 최근 이벤트 ({result['count']})</b> (최근 {result['hours']}시간)",
                "━━━━━━━━━━━━━━━━━━━",
            ]
            for event in result['events'][:10]:
                lines.append(f"• {event.get('check_type', 'unknown')}: {event.get('status', 'N/A')}")
            if result['count'] > 10:
                lines.append(f"\n... 외 {result['count'] - 10}개")
            lines.append("━━━━━━━━━━━━━━━━━━━")
            self.telegram.send_message('\n'.join(lines))
        elif 'events' in result:
            self.telegram.send_message(f"✅ 최근 {result.get('hours', 24)}시간 이벤트가 없습니다.")

        # Sprint 9: Advanced commands
        elif result.get('action') == 'remediate':
            status = result.get('status', 'error')
            if status == 'in_progress':
                self.telegram.send_message(f"⏳ <b>대응 진행 중</b>\nFinding: {result['finding_id']}\n{result['message']}")
            elif status == 'completed':
                self.telegram.send_message(f"✅ <b>대응 완료</b>\nFinding: {result['finding_id']}\n{result['message']}")
            else:
                msg = result.get('message', '성공')
                self.telegram.send_message(f"✅ <b>대응 실행</b>\nFinding: {result['finding_id']}\n{msg}")

        elif result.get('action') == 'export':
            self.telegram.send_message(
                f"✅ <b>보고서 생성</b>\n"
                f"형식: {result['format'].upper()}\n"
                f"이벤트: {result['event_count']}개\n"
                f"파일: {result['file_path']}\n"
                f"크기: {result['size_bytes'] / 1024:.1f} KB"
            )

        elif result.get('action') == 'insights':
            analysis = result.get('analysis', '분석 불가')
            # Send analysis as markdown (Gemini output)
            self.telegram.send_message(f"🔍 <b>위협 분석</b> ({result.get('event_count', 0)}개 이벤트)\n\n{analysis}")

    def run(self):
        logger.info("AWS Guardian Telegram Bot 시작")
        logger.info("사용 가능한 명령어: /status, /instances, /history, /stop, /threshold, /help")
        logger.info("종료하려면 Ctrl+C")

        while self.running:
            updates = self.get_updates()

            for update in updates:
                self.last_update_id = update['update_id']

                if 'message' in update:
                    self.handle_message(update['message'])

        logger.info("Bot stopped.")


if __name__ == '__main__':
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        print("TELEGRAM_BOT_TOKEN 환경변수가 필요합니다.")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s'
    )

    bot = TelegramBotListener()
    bot.run()
