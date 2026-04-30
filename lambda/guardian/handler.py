"""Main Lambda handler for AWS Guardian - optimized for cold start"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from guardian.checkers.cost import CostChecker
from guardian.checkers.ec2 import EC2Checker
from guardian.checkers.s3 import S3Checker
from guardian.responders.telegram import TelegramResponder
from guardian.responders.discord import DiscordResponder
from guardian.responders.remediation_service import AutoRemediationResponder
from guardian.storage.dynamodb import DynamoDBStorage
from guardian.config import Config
from guardian.logging_config import setup_logger
from guardian.orchestrator import GuardianOrchestrator

logger = setup_logger('aws-guardian', log_file='guardian.log')

config = Config()
cost_threshold = config.get_cost_threshold()
telegram_config = config.get_telegram_config()
discord_config = config.get_discord_config()

cost_checker = CostChecker(cost_threshold=cost_threshold)
ec2_checker = EC2Checker()
s3_checker = S3Checker()

storage = DynamoDBStorage()

telegram_responder = TelegramResponder() if telegram_config['bot_token'] else None
discord_responder = DiscordResponder() if discord_config['webhook_url'] else None
auto_remediation_responder = AutoRemediationResponder(logger, storage, ec2_checker, s3_checker)

orchestrator = GuardianOrchestrator(
    logger=logger,
    cost_checker=cost_checker,
    ec2_checker=ec2_checker,
    s3_checker=s3_checker,
    storage=storage,
    telegram_responder=telegram_responder,
    discord_responder=discord_responder,
    remediation_responder=auto_remediation_responder,
)


def lambda_handler(event, context=None):
    return orchestrator.run_all_checks(event)


if __name__ == '__main__':
    test_event = {
        'time': '2024-01-01T00:00:00Z',
        'source': 'aws.events'
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
