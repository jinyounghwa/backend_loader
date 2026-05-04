"""Discord command handler Lambda for AWS Guardian"""
import json
import os
import re
import sys
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from guardian.checkers.cost import CostChecker
from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.s3 import S3Checker
from guardian.responders.discord import DiscordResponder
from guardian.responders.aws_action_executor import AWSActionExecutor
from guardian.storage.dynamodb import DynamoDBStorage
from guardian.aws_client_provider import AWSClientProvider

logger = logging.getLogger(__name__)

INSTANCE_ID_PATTERN = re.compile(r'^i-[0-9a-f]{8,17}$')
REGION_PATTERN = re.compile(r'^(us|eu|ap|sa|ca|me|af)-(east|west|south|north|central|southeast|northeast)-[0-9]$')
MIN_THRESHOLD = 0.01
MAX_THRESHOLD = 1000000.0

cost_checker = CostChecker()
ec2_checker = EC2Checker()
s3_checker = S3Checker()
discord = DiscordResponder()
storage = DynamoDBStorage()
action_executor = AWSActionExecutor()


def verify_discord_request(request_body: str, signature: str, timestamp: str) -> bool:
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError

        public_key = os.getenv('DISCORD_PUBLIC_KEY', '')
        if not public_key or not signature or not timestamp:
            return False

        verify_key = VerifyKey(bytes.fromhex(public_key))
        message = (timestamp + request_body).encode('utf-8')
        verify_key.verify(message, bytes.fromhex(signature))
        return True
    except (BadSignatureError, ValueError, Exception) as e:
        logger.warning("Discord signature verification failed: %s", e)
        return False


def create_response(content: str, ephemeral: bool = False):
    return {
        'type': 4,
        'data': {
            'content': content,
            'flags': 64 if ephemeral else 0
        }
    }


def lambda_handler(event, context):
    try:
        body = event.get('body', '{}')
        if isinstance(body, str):
            interaction = json.loads(body)
        else:
            interaction = body

        signature = event.get('headers', {}).get('x-signature-ed25519', '')
        timestamp = event.get('headers', {}).get('x-signature-timestamp', '')

        if not verify_discord_request(body, signature, timestamp):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid request signature'})
            }

        if interaction.get('type') == 1:
            return {
                'statusCode': 200,
                'body': json.dumps({'type': 1})
            }

        if interaction.get('type') == 2:
            command_name = interaction['data']['name']

            handlers = {
                'status': handle_status_command,
                'stop': handle_stop_command,
                'budget': handle_budget_command,
                'history': handle_history_command,
            }

            handler = handlers.get(command_name)
            if handler:
                return handler(interaction)
            else:
                return create_response(f"Unknown command: {command_name}", ephemeral=True)

    except Exception as e:
        logger.error("Discord handler error: %s", e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'internal_error'})
        }


def handle_status_command(interaction):
    try:
        cost_result = cost_checker.check()
        cost_details = cost_result.details

        ec2_result = ec2_checker.check()
        ec2_details = ec2_result.details

        s3_result = s3_checker.check()
        s3_details = s3_result.details

        total_instances = sum(
            len(insts) for insts in ec2_details.get('unauthorized_region_instances', {}).values()
        ) + len(ec2_details.get('new_instances', []))

        public_count = len(s3_details.get('public_buckets', []))

        embed = {
            'title': '📊 AWS Guardian Status',
            'color': 65280,
            'fields': [
                {'name': '💰 Monthly Cost', 'value': f"${cost_details.get('monthly_cost', 0):.2f}", 'inline': True},
                {'name': "📈 Today's Cost", 'value': f"${cost_details.get('today_cost', 0):.2f}", 'inline': True},
                {'name': '🏃 EC2 Issues', 'value': str(total_instances), 'inline': True},
                {'name': '🪣 S3 Issues', 'value': str(public_count), 'inline': True},
                {'name': '📍 System Health', 'value': cost_result.severity, 'inline': True}
            ],
            'footer': {'text': 'AWS Guardian'},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        return {
            'statusCode': 200,
            'body': json.dumps({
                'type': 4,
                'data': {'embeds': [embed]}
            })
        }

    except Exception as e:
        logger.error("Status command error: %s", e)
        return create_response("Failed to retrieve status", ephemeral=True)


def handle_stop_command(interaction):
    try:
        options = interaction['data'].get('options', [])
        instance_id = None
        region = None

        for opt in options:
            if opt['name'] == 'instance_id':
                instance_id = opt['value']
            elif opt['name'] == 'region':
                region = opt['value']

        if not instance_id:
            return create_response("Instance ID is required", ephemeral=True)

        if not INSTANCE_ID_PATTERN.match(instance_id):
            return create_response("Invalid instance ID format", ephemeral=True)

        if not region:
            return create_response("Region is required", ephemeral=True)

        if not REGION_PATTERN.match(region):
            return create_response("Invalid region format", ephemeral=True)

        success = action_executor.stop_ec2_instance(instance_id, region)

        if success:
            message = f"✅ Successfully stopped instance: `{instance_id}` in `{region}`"
        else:
            message = f"❌ Failed to stop instance: `{instance_id}`"

        return create_response(message, ephemeral=True)

    except Exception as e:
        logger.error("Stop command error: %s", e)
        return create_response("Failed to stop instance", ephemeral=True)


def handle_budget_command(interaction):
    try:
        options = interaction['data'].get('options', [])
        subcommand = options[0]['name'] if options else None

        if subcommand == 'set':
            amount_str = options[0]['options'][0]['value'] if options[0].get('options') else None

            if not amount_str:
                return create_response("Amount is required", ephemeral=True)

            try:
                amount = float(amount_str)
                if amount < MIN_THRESHOLD or amount > MAX_THRESHOLD:
                    return create_response(
                        f"Amount must be between ${MIN_THRESHOLD} and ${MAX_THRESHOLD:,.0f}",
                        ephemeral=True
                    )
                cost_checker.set_threshold(amount)
                message = f"✅ Cost threshold set to ${amount:.2f}/day"
            except ValueError:
                message = "❌ Invalid amount format"

        else:
            threshold = cost_checker.get_threshold()
            message = f"📊 Current cost threshold: ${threshold:.2f}/day"

        return create_response(message, ephemeral=True)

    except Exception as e:
        logger.error("Budget command error: %s", e)
        return create_response("Failed to set budget", ephemeral=True)


def handle_history_command(interaction):
    try:
        events = storage.get_recent_events(hours=24)

        if not events:
            return create_response("No events in the last 24 hours", ephemeral=True)

        event_list = []
        for event in events[:10]:
            event_type = event.get('event_type', 'unknown')
            severity = event.get('severity', 'info')
            ts = event.get('timestamp', '')
            event_list.append(f"• [{ts}] {severity.upper()} - {event_type}")

        message = "📋 **Recent Events (Last 24 hours)**\n" + "\n".join(event_list)
        return create_response(message, ephemeral=True)

    except Exception as e:
        logger.error("History command error: %s", e)
        return create_response("Failed to retrieve history", ephemeral=True)
