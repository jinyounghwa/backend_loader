"""APScheduler-based scheduler for AWS Guardian monitoring"""
import os
import sys
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, os.path.dirname(__file__))

from handler import lambda_handler
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('Guardian Scheduler')


class GuardianScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.job = None

    def job_callback(self):
        """Callback function that runs the Lambda handler"""
        try:
            logger.info("Starting scheduled check...")
            event = {
                'time': datetime.now(timezone.utc).isoformat(),
                'source': 'scheduler'
            }
            result = lambda_handler(event)
            logger.info(f"Check completed: {result.get('status', 'unknown')}")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

    def start(self, interval_minutes: int = 60):
        """Start the scheduler"""
        logger.info(f"Starting AWS Guardian Scheduler (interval: {interval_minutes} minutes)")

        # Add job to run every N minutes
        self.job = self.scheduler.add_job(
            self.job_callback,
            trigger=CronTrigger(minute=f"*/{interval_minutes}"),
            id='guardian_check',
            name='AWS Guardian Monitoring Check',
            misfire_grace_time=30
        )

        self.scheduler.start()
        logger.info("Scheduler started. Press Ctrl+C to stop.")

        try:
            self.scheduler._thread.join()
        except KeyboardInterrupt:
            logger.info("Shutdown requested. Stopping scheduler...")
            self.scheduler.shutdown()
            logger.info("Scheduler stopped.")

    def run_once(self):
        """Run the check immediately (for testing)"""
        logger.info("Running check immediately...")
        self.job_callback()


if __name__ == '__main__':
    scheduler = GuardianScheduler()

    # Run once immediately, then schedule for 1-hour intervals
    scheduler.run_once()
    scheduler.start(interval_minutes=60)
