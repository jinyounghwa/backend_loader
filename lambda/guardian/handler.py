"""Main Lambda handler for AWS Guardian - OPTIMIZED for cold start"""
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
from responders.remediation_service import AutoRemediationResponder
from storage.dynamodb import DynamoDBStorage
from config import Config
from logging_config import setup_logger
from orchestrator import GuardianOrchestrator

# ============================================================================
# GLOBAL SCOPE INITIALIZATION (Executed once per Lambda container)
# This is the key optimization: expensive resources are initialized outside
# the handler, allowing Lambda to reuse them across warm invocations
# ============================================================================

# Setup logging (once)
logger = setup_logger('aws-guardian', log_file='guardian.log')

# Initialize configuration (once)
config = Config()
cost_threshold = config.get_cost_threshold()
telegram_config = config.get_telegram_config()
discord_config = config.get_discord_config()

# Initialize checkers (once, reused across invocations)
cost_checker = CostChecker(cost_threshold=cost_threshold)
ec2_checker = EC2Checker()
s3_checker = S3Checker()

# Initialize storage (once, reused across invocations)
storage = DynamoDBStorage()

# Initialize responders only if credentials are available (once)
telegram_responder = TelegramResponder() if telegram_config['bot_token'] else None
discord_responder = DiscordResponder() if discord_config['webhook_url'] else None
auto_remediation_responder = AutoRemediationResponder(logger, storage, ec2_checker, s3_checker)

# Initialize orchestrator (once, reused across invocations)
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

# ============================================================================
# LAMBDA HANDLER (Executed on every invocation)
# Now simplified to delegate all work to the pre-initialized orchestrator
# ============================================================================


def lambda_handler(event, context=None):
    """Main Lambda handler for AWS Guardian monitoring"""
    return orchestrator.run_all_checks(event)


if __name__ == '__main__':
    # For local testing
    test_event = {
        'time': '2024-01-01T00:00:00Z',
        'source': 'aws.events'
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
