"""Discord command handler Lambda for AWS Guardian"""
import json
import os
import sys
import hmac
import hashlib
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from guardian.checkers.cost import CostChecker
from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.s3 import S3Checker
from guardian.responders.discord import DiscordResponder
from guardian.storage.dynamodb import DynamoDBStorage


def verify_discord_request(request_body, signature, timestamp):
    """Verify Discord interaction signature"""
    public_key = os.getenv('DISCORD_PUBLIC_KEY', '')
    message = timestamp + request_body
    expected_signature = hmac.new(
        public_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature == expected_signature


def create_response(content: str, ephemeral: bool = False):
    """Create Discord interaction response"""
    return {
        'type': 4,  # CHANNEL_MESSAGE_WITH_SOURCE
        'data': {
            'content': content,
            'flags': 64 if ephemeral else 0  # Ephemeral flag
        }
    }


def lambda_handler(event, context):
    """Handle Discord interactions"""

    try:
        body = event.get('body', '{}')
        if isinstance(body, str):
            interaction = json.loads(body)
        else:
            interaction = body

        # Verify request
        signature = event.get('headers', {}).get('x-signature-ed25519', '')
        timestamp = event.get('headers', {}).get('x-signature-timestamp', '')

        if not verify_discord_request(body, signature, timestamp):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid request signature'})
            }

        # Handle PING
        if interaction.get('type') == 1:
            return {
                'statusCode': 200,
                'body': json.dumps({'type': 1})
            }

        # Handle commands
        if interaction.get('type') == 2:
            command_name = interaction['data']['name']

            if command_name == 'status':
                return handle_status_command(interaction)
            elif command_name == 'stop':
                return handle_stop_command(interaction)
            elif command_name == 'budget':
                return handle_budget_command(interaction)
            elif command_name == 'history':
                return handle_history_command(interaction)
            else:
                return create_response(f"Unknown command: {command_name}", ephemeral=True)

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_status_command(interaction):
    """Handle /status command"""
    try:
        cost_checker = CostChecker()
        ec2_checker = EC2Checker()
        s3_checker = S3Checker()

        # Get current status
        daily_cost = cost_checker.get_daily_cost()
        monthly_cost = cost_checker.get_monthly_cost()

        all_instances = ec2_checker.get_all_instances()
        total_instances = sum(len(insts) for insts in all_instances.values())

        all_buckets = s3_checker.get_public_buckets()

        status_data = {
            'monthly_cost': monthly_cost,
            'daily_cost': daily_cost,
            'running_instances': total_instances,
            'total_buckets': len(all_buckets),
            'public_buckets': len(all_buckets)
        }

        discord = DiscordResponder()
        embed = {
            'title': '📊 AWS Guardian Status',
            'color': 65280,  # Green
            'fields': [
                {
                    'name': '💰 Monthly Cost',
                    'value': f"${monthly_cost:.2f}",
                    'inline': True
                },
                {
                    'name': '📈 Today\'s Cost',
                    'value': f"${daily_cost:.2f}",
                    'inline': True
                },
                {
                    'name': '🏃 Running EC2',
                    'value': str(total_instances),
                    'inline': True
                },
                {
                    'name': '🪣 Total S3 Buckets',
                    'value': str(len(all_buckets)),
                    'inline': True
                },
                {
                    'name': '🌐 Public Buckets',
                    'value': str(len(all_buckets)),
                    'inline': True
                }
            ],
            'footer': {'text': 'AWS Guardian'},
            'timestamp': datetime.utcnow().isoformat()
        }

        return {
            'statusCode': 200,
            'body': json.dumps({
                'type': 4,
                'data': {
                    'embeds': [embed]
                }
            })
        }

    except Exception as e:
        return create_response(f"Error getting status: {str(e)}", ephemeral=True)


def handle_stop_command(interaction):
    """Handle /stop instance-id command"""
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

        if not region:
            return create_response("Region is required", ephemeral=True)

        ec2_checker = EC2Checker()
        success = ec2_checker.stop_instance(instance_id, region)

        if success:
            message = f"✅ Successfully stopped instance: `{instance_id}` in `{region}`"
        else:
            message = f"❌ Failed to stop instance: `{instance_id}`"

        return create_response(message, ephemeral=True)

    except Exception as e:
        return create_response(f"Error: {str(e)}", ephemeral=True)


def handle_budget_command(interaction):
    """Handle /budget set amount command"""
    try:
        options = interaction['data'].get('options', [])
        subcommand = options[0]['name'] if options else None

        if subcommand == 'set':
            amount_str = options[0]['options'][0]['value'] if options[0].get('options') else None

            if not amount_str:
                return create_response("Amount is required", ephemeral=True)

            try:
                amount = float(amount_str)
                cost_checker = CostChecker()
                cost_checker.set_threshold(amount)
                message = f"✅ Cost threshold set to ${amount:.2f}/day"
            except ValueError:
                message = "❌ Invalid amount format"

        else:
            cost_checker = CostChecker()
            threshold = cost_checker.get_threshold()
            message = f"📊 Current cost threshold: ${threshold:.2f}/day"

        return create_response(message, ephemeral=True)

    except Exception as e:
        return create_response(f"Error: {str(e)}", ephemeral=True)


def handle_history_command(interaction):
    """Handle /history command"""
    try:
        storage = DynamoDBStorage()
        events = storage.get_recent_events(hours=24)

        if not events:
            return create_response("No events in the last 24 hours", ephemeral=True)

        # Format events
        event_list = []
        for event in events[:10]:  # Show last 10
            event_type = event.get('event_type', 'unknown')
            severity = event.get('severity', 'info')
            timestamp = event.get('timestamp', '')

            event_list.append(f"• [{timestamp}] {severity.upper()} - {event_type}")

        message = "📋 **Recent Events (Last 24 hours)**\n" + "\n".join(event_list)

        return create_response(message, ephemeral=True)

    except Exception as e:
        return create_response(f"Error: {str(e)}", ephemeral=True)
