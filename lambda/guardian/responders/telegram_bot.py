"""Telegram bot listener - polls for user commands and executes auto-remediation"""
import os
import sys
import json
import time
import requests
import signal
import boto3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from responders.telegram import TelegramResponder
from responders.auto_remediation import remediate_cost_overrun, remediate_hacking_suspicion
from config import Config
from storage.dynamodb import DynamoDBStorage

COMMANDS = {
    '요금과다 원인수정': remediate_cost_overrun,
    '해킹우려 수정': remediate_hacking_suspicion,
}


def get_status() -> dict:
    """Get current system status"""
    try:
        kwargs = Config.get_boto3_kwargs()
        ec2 = boto3.client('ec2', **kwargs)
        s3 = boto3.client('s3', **kwargs)
        ce = boto3.client('ce', **kwargs)

        # Get EC2 status
        ec2_response = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        running_instances = sum(
            len(r.get('Instances', []))
            for r in ec2_response.get('Reservations', [])
        )

        # Get S3 status
        s3_response = s3.list_buckets()
        total_buckets = len(s3_response.get('Buckets', []))

        # Get cost
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        cost_response = ce.get_cost_and_usage(
            TimePeriod={'Start': today, 'End': (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%d')},
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        today_cost = 0
        if cost_response.get('ResultsByTime'):
            today_cost = float(cost_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'ec2_running': running_instances,
            's3_buckets': total_buckets,
            'today_cost': today_cost,
            'threshold': Config.get_cost_threshold()
        }
    except Exception as e:
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def get_instances() -> dict:
    """Get list of running EC2 instances"""
    try:
        kwargs = Config.get_boto3_kwargs()
        ec2 = boto3.client('ec2', **kwargs)

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
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def stop_instance(instance_id: str) -> dict:
    """Stop a specific EC2 instance"""
    try:
        kwargs = Config.get_boto3_kwargs()
        ec2 = boto3.client('ec2', **kwargs)

        ec2.stop_instances(InstanceIds=[instance_id])

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': 'stop_instance',
            'instance_id': instance_id,
            'status': 'stopped'
        }
    except Exception as e:
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def set_threshold(amount: str) -> dict:
    """Set cost threshold"""
    try:
        threshold = float(amount)
        kwargs = Config.get_boto3_kwargs()
        ssm = boto3.client('ssm', **kwargs)

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
        return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}


def get_history(hours: int = 24) -> dict:
    """Get recent event history"""
    try:
        storage = DynamoDBStorage()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # Get latest check results
        items = storage.get_latest_check_result(
            time_filter=since
        )

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'hours': hours,
            'events': items if items else [],
            'count': len(items) if items else 0
        }
    except Exception as e:
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
        print(f"\n[Bot] Shutdown signal received. Stopping...")
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
            print(f"[Bot] Error polling updates: {e}")
            time.sleep(5)
        return []

    def parse_command(self, text: str):
        if not text:
            return None
        text = text.strip()

        # Handle legacy commands
        if text in COMMANDS:
            return COMMANDS[text], text

        # Handle slash commands
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

        # Handle legacy keywords
        for keyword, handler in COMMANDS.items():
            if keyword in text:
                return handler, keyword

        return None

    def _show_help(self) -> dict:
        """Show available commands"""
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
        print(f"[Bot] Command received from {from_user}: {command_text}")

        try:
            result = handler()
            self._format_response(result, command_text)
        except Exception as e:
            print(f"[Bot] Command error: {e}")
            self.telegram.send_message(f"❌ <b>명령 실패</b>\n명령: {command_text}\n오류: {str(e)}")

    def _format_response(self, result: dict, command_text: str):
        """Format and send response based on command result type"""
        if 'error' in result:
            self.telegram.send_message(f"❌ <b>오류</b>\n{result['error']}")
            return

        # Auto-remediation result (steps)
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

        # Status result
        elif 'ec2_running' in result:
            threshold_icon = "🟢" if result['today_cost'] < result['threshold'] else "🔴"
            lines = [
                "<b>📊 현재 상태</b>",
                "━━━━━━━━━━━━━━━━━━━",
                f"🖥️  EC2: {result['ec2_running']}개 실행 중",
                f"🪣 S3: {result['s3_buckets']}개 버킷",
                f"{threshold_icon} 비용: ${result['today_cost']:.2f} / ${result['threshold']:.2f}",
                "━━━━━━━━━━━━━━━━━━━",
            ]
            self.telegram.send_message('\n'.join(lines))

        # Instances list
        elif 'instances' in result and result.get('count', 0) > 0:
            lines = [
                f"<b>🖥️  실행 중인 인스턴스 ({result['count']})</b>",
                "━━━━━━━━━━━━━━━━━━━",
            ]
            for inst in result['instances'][:10]:  # Show first 10
                lines.append(f"• <code>{inst['instance_id']}</code>")
                lines.append(f"  타입: {inst['instance_type']} | 상태: {inst['state']}")
            if result['count'] > 10:
                lines.append(f"\n... 외 {result['count'] - 10}개")
            lines.append("━━━━━━━━━━━━━━━━━━━")
            self.telegram.send_message('\n'.join(lines))
        elif 'instances' in result:
            self.telegram.send_message("✅ 실행 중인 인스턴스가 없습니다.")

        # Stop instance result
        elif result.get('action') == 'stop_instance':
            self.telegram.send_message(f"✅ <b>인스턴스 중지</b>\nID: <code>{result['instance_id']}</code>\n상태: {result['status']}")

        # Set threshold result
        elif result.get('action') == 'set_threshold':
            self.telegram.send_message(f"✅ <b>임계값 변경</b>\n새 임계값: ${result['new_threshold']:.2f}")

        # History result
        elif 'events' in result and result.get('count', 0) > 0:
            lines = [
                f"<b>📜 최근 이벤트 ({result['count']})</b> (최근 {result['hours']}시간)",
                "━━━━━━━━━━━━━━━━━━━",
            ]
            for event in result['events'][:10]:  # Show first 10
                lines.append(f"• {event.get('check_type', 'unknown')}: {event.get('status', 'N/A')}")
            if result['count'] > 10:
                lines.append(f"\n... 외 {result['count'] - 10}개")
            lines.append("━━━━━━━━━━━━━━━━━━━")
            self.telegram.send_message('\n'.join(lines))
        elif 'events' in result:
            self.telegram.send_message(f"✅ 최근 {result.get('hours', 24)}시간 이벤트가 없습니다.")

    def run(self):
        print(f"[Bot] AWS Guardian Telegram Bot 시작")
        print(f"[Bot] 사용 가능한 명령어:")
        print(f"  상태: /status, /instances, /history [시간]")
        print(f"  제어: /stop <id>, /threshold <금액>")
        print(f"  자동: 요금과다 원인수정, 해킹우려 수정")
        print(f"  도움: /help")
        print(f"[Bot] 종료하려면 Ctrl+C\n")

        while self.running:
            updates = self.get_updates()

            for update in updates:
                self.last_update_id = update['update_id']

                if 'message' in update:
                    self.handle_message(update['message'])

        print("[Bot] Stopped.")


if __name__ == '__main__':
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        print("TELEGRAM_BOT_TOKEN 환경변수가 필요합니다.")
        sys.exit(1)

    bot = TelegramBotListener()
    bot.run()
