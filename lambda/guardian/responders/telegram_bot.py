"""Telegram bot listener - polls for user commands and executes auto-remediation"""
import os
import sys
import json
import time
import logging
import signal
import requests
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from guardian.responders.telegram import TelegramResponder
from guardian.responders.auto_remediation import remediate_cost_overrun, remediate_hacking_suspicion
from guardian.config import Config
from guardian.aws_client_provider import AWSClientProvider
from guardian.storage.dynamodb import DynamoDBStorage

logger = logging.getLogger('telegram_bot')

COMMANDS = {
    '요금과다 원인수정': remediate_cost_overrun,
    '해킹우려 수정': remediate_hacking_suspicion,
}


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
                f"✅ <b>자동 수정 완료</b>",
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
            lines.append(f"<b>요약:</b>")
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
