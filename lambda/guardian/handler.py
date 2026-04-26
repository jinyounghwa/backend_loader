"""Main Lambda handler for AWS Guardian"""
import os
import sys
import json

# Add parent directory to path for local testing
sys.path.insert(0, os.path.dirname(__file__))

from checkers.cost import CostChecker
from checkers.ec2 import EC2Checker
from checkers.s3 import S3Checker
from responders.telegram import TelegramResponder
from responders.discord import DiscordResponder
from responders.glm import GLMAnalyzer
from storage.dynamodb import DynamoDBStorage
from config import Config


def lambda_handler(event, context=None):
    """Main Lambda handler for AWS Guardian monitoring"""

    # Get configuration
    is_localstack = Config.is_localstack()

    if is_localstack:
        print("[LocalStack Mode] Running in LocalStack environment")

    # Initialize components
    cost_threshold = Config.get_cost_threshold()
    cost_checker = CostChecker(cost_threshold=cost_threshold)
    ec2_checker = EC2Checker()
    s3_checker = S3Checker()

    # Get credentials from config
    telegram_config = Config.get_telegram_config()
    discord_config = Config.get_discord_config()

    # Initialize responders only if credentials are available
    has_telegram = telegram_config['bot_token'] and not is_localstack
    has_discord = discord_config['webhook_url'] and not is_localstack

    telegram = TelegramResponder() if has_telegram else None
    discord = DiscordResponder() if has_discord else None
    glm_analyzer = GLMAnalyzer()  # Always initialize GLM
    storage = DynamoDBStorage()

    results = {
        'timestamp': event.get('time', 'unknown'),
        'status': 'success',
        'checks': {}
    }

    # 1. Check costs
    print("Checking AWS costs...")
    try:
        cost_anomaly, cost_data = cost_checker.check_cost_anomaly()
        results['checks']['cost'] = cost_data

        if cost_anomaly:
            print(f"⚠️ Cost anomaly detected: ${cost_data['today_cost']}")

            # Analyze with GLM
            print("🤖 Analyzing with GLM...")
            glm_analysis = glm_analyzer.analyze_cost_anomaly(cost_data)
            cost_data['glm_analysis'] = glm_analysis

            storage.save_event('cost', 'warning', cost_data)
            if telegram:
                telegram.send_cost_alert(cost_data)
            if discord:
                discord.send_cost_alert(cost_data)
            if is_localstack:
                print(f"[LocalStack] Would send cost alert: {json.dumps(cost_data, indent=2, default=str)}")
        else:
            print(f"✓ Cost normal: ${cost_data['today_cost']}")

    except Exception as e:
        print(f"❌ Error checking costs: {e}")
        results['checks']['cost'] = {'error': str(e)}

    # 2. Check EC2
    print("Checking EC2 instances...")
    try:
        ec2_anomaly, ec2_data = ec2_checker.check_ec2_anomalies()
        results['checks']['ec2'] = ec2_data

        if ec2_anomaly:
            print(f"⚠️ EC2 anomalies detected: {len(ec2_data.get('anomalies', []))} issues")

            # Analyze with GLM
            print("🤖 Analyzing EC2 issues with GLM...")
            glm_analysis = glm_analyzer.analyze_ec2_anomalies(ec2_data)
            ec2_data['glm_analysis'] = glm_analysis

            storage.save_event('ec2', 'critical', ec2_data)
            if telegram:
                telegram.send_ec2_alert(ec2_data)
            if discord:
                discord.send_ec2_alert(ec2_data)
            if is_localstack:
                print(f"[LocalStack] Would send EC2 alert: {json.dumps(ec2_data, indent=2, default=str)}")

            # Auto-respond: Stop exposed instances
            for exposed in ec2_data.get('exposed_instances', []):
                instance_id = exposed['instance_id']
                region = exposed['region']
                print(f"Stopping exposed instance: {instance_id}")
                if not is_localstack:
                    success = ec2_checker.stop_instance(instance_id, region)
                else:
                    print(f"[LocalStack] Would stop instance: {instance_id}")
                    success = True
                storage.save_auto_response(
                    'stop_ec2',
                    instance_id,
                    'success' if success else 'failed',
                    {'region': region, 'reason': 'exposed_to_0_0_0_0'}
                )
                if telegram:
                    telegram.send_auto_response_notification('stop_ec2', instance_id, 'success' if success else 'failed')

        else:
            print("✓ EC2 instances secure")

    except Exception as e:
        print(f"❌ Error checking EC2: {e}")
        results['checks']['ec2'] = {'error': str(e)}

    # 3. Check S3
    print("Checking S3 buckets...")
    try:
        s3_anomaly, s3_data = s3_checker.check_s3_anomalies()
        results['checks']['s3'] = s3_data

        if s3_anomaly:
            print(f"⚠️ S3 anomalies detected: {len(s3_data.get('anomalies', []))} issues")

            # Analyze with GLM
            print("🤖 Analyzing S3 issues with GLM...")
            glm_analysis = glm_analyzer.analyze_s3_anomalies(s3_data)
            s3_data['glm_analysis'] = glm_analysis

            storage.save_event('s3', 'critical', s3_data)
            if telegram:
                telegram.send_s3_alert(s3_data)
            if discord:
                discord.send_s3_alert(s3_data)
            if is_localstack:
                print(f"[LocalStack] Would send S3 alert: {json.dumps(s3_data, indent=2, default=str)}")

            # Auto-respond: Block public access
            for public_bucket in s3_data.get('public_buckets', []):
                bucket_name = public_bucket['bucket_name']
                print(f"Blocking public access for: {bucket_name}")
                if not is_localstack:
                    success = s3_checker.block_public_access(bucket_name)
                else:
                    print(f"[LocalStack] Would block public access for: {bucket_name}")
                    success = True
                storage.save_auto_response(
                    'block_s3_public',
                    bucket_name,
                    'success' if success else 'failed',
                    {'reasons': public_bucket['public_reasons']}
                )
                if telegram:
                    telegram.send_auto_response_notification('block_s3_public', bucket_name, 'success' if success else 'failed')

        else:
            print("✓ S3 buckets secure")

    except Exception as e:
        print(f"❌ Error checking S3: {e}")
        results['checks']['s3'] = {'error': str(e)}

    # 4. Get and send summary
    try:
        summary = storage.get_event_summary(hours=24)

        # Generate AI-powered report with GLM
        print("🤖 Generating GLM-powered summary report...")
        glm_report = glm_analyzer.generate_summary_report(results['checks'])
        summary['glm_report'] = glm_report

        if summary.get('total_events', 0) > 0:
            if telegram:
                telegram.send_summary(summary)
            if discord:
                discord.send_summary_embed(summary)

        # Save summary with GLM insights
        storage.save_event('summary', 'info', summary)

    except Exception as e:
        print(f"Warning: Could not send summary: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }


if __name__ == '__main__':
    # For local testing
    test_event = {
        'time': '2024-01-01T00:00:00Z',
        'source': 'aws.events'
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
