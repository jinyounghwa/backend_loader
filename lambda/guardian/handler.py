"""Main Lambda handler for AWS Guardian - lazy initialization for optimal cold start."""
import os
import sys
import json
import logging
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from guardian.config import Config
from guardian.logging_config import setup_logger

logger = setup_logger('aws-guardian')


class _LazyOrchestrator:
    """Lazy-initialize heavy dependencies only when first invoked.

    Avoids importing and constructing all checkers/responders during module load,
    which would penalize every cold start regardless of which check is requested.
    """

    def __init__(self):
        self._orchestrator = None
        self._logger = setup_logger('aws-guardian')

    def _build(self):
        """Build the full orchestrator with all checkers and responders."""
        from guardian.checkers.cost import CostChecker
        from guardian.checkers.ec2 import EC2Checker
        from guardian.checkers.s3 import S3Checker
        from guardian.responders.telegram import TelegramResponder
        from guardian.responders.discord import DiscordResponder
        from guardian.responders.remediation_service import AutoRemediationResponder
        from guardian.storage.dynamodb import DynamoDBStorage
        from guardian.orchestrator import GuardianOrchestrator

        config = Config()
        cost_threshold = config.get_cost_threshold()
        telegram_config = config.get_telegram_config()
        discord_config = config.get_discord_config()

        storage = DynamoDBStorage()

        telegram_responder = TelegramResponder() if telegram_config['bot_token'] else None
        discord_responder = DiscordResponder() if discord_config['webhook_url'] else None
        auto_remediation_responder = AutoRemediationResponder(
            self._logger, storage, telegram=telegram_responder,
        )

        self._orchestrator = GuardianOrchestrator(
            logger=self._logger,
            cost_checker=CostChecker(config={'cost_threshold': cost_threshold}),
            ec2_checker=EC2Checker(),
            s3_checker=S3Checker(),
            storage=storage,
            telegram_responder=telegram_responder,
            discord_responder=discord_responder,
            remediation_responder=auto_remediation_responder,
        )

    @property
    def orchestrator(self):
        if self._orchestrator is None:
            self._build()
        return self._orchestrator


_lazy = _LazyOrchestrator()


def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """AWS Lambda entry point."""
    try:
        return _lazy.orchestrator.run_all_checks(event)
    except Exception as e:
        logger.exception("Fatal error in lambda_handler: %s", e)
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


if __name__ == '__main__':
    test_event = {
        'time': '2024-01-01T00:00:00Z',
        'source': 'aws.events'
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
