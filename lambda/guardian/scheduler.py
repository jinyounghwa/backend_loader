"""APScheduler-based scheduler for AWS Guardian monitoring"""

import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from guardian.handler import lambda_handler

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s"
)
logger = logging.getLogger("Guardian Scheduler")


class GuardianScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.job = None

    def job_callback(self):
        try:
            logger.info("Starting scheduled check...")
            event = {"time": datetime.now(timezone.utc).isoformat(), "source": "scheduler"}
            result = lambda_handler(event)
            logger.info("Check completed: %s", result.get("status", "unknown"))
        except Exception as e:
            logger.error("Scheduler error: %s", e)

    def start(self, interval_minutes: int = 60):
        logger.info("Starting AWS Guardian Scheduler (interval: %d minutes)", interval_minutes)

        self.job = self.scheduler.add_job(
            self.job_callback,
            trigger=CronTrigger(minute=f"*/{interval_minutes}"),
            id="guardian_check",
            name="AWS Guardian Monitoring Check",
            misfire_grace_time=30,
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
        logger.info("Running check immediately...")
        self.job_callback()


if __name__ == "__main__":
    scheduler = GuardianScheduler()
    scheduler.run_once()
    scheduler.start(interval_minutes=60)
