#!/usr/bin/env python3
"""
Agent Scheduler: runs agents on predefined schedule using APScheduler.
This is a long-running daemon that triggers agents at specified intervals.
"""
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from agents.run_agent import main as run_agent_main
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AgentScheduler')

class AgentScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs = {}

    def schedule_agent(self, agent_type: str, cron_expr: str):
        """Schedule an agent to run on a cron schedule."""
        job_id = f'agent_{agent_type}'

        def job_wrapper():
            logger.info(f"Starting scheduled run of {agent_type} agent")
            try:
                # Run agent in a separate thread to not block scheduler
                thread = threading.Thread(
                    target=run_agent_main,
                    kwargs={'agent_type': agent_type}
                )
                thread.start()
                # Don't wait for completion; let it run async
                logger.info(f"Scheduled {agent_type} agent started in background")
            except Exception as e:
                logger.error(f"Failed to start {agent_type} agent: {e}")

        self.scheduler.add_job(
            job_wrapper,
            CronTrigger.from_crontab(cron_expr),
            id=job_id,
            replace_existing=True
        )
        self.jobs[job_id] = {
            'agent_type': agent_type,
            'cron': cron_expr,
            'next_run': None
        }
        logger.info(f"Scheduled {agent_type} agent with cron: {cron_expr}")

    def start(self):
        """Start the scheduler."""
        logger.info("Starting Agent Scheduler...")
        self.scheduler.start()
        logger.info("Agent Scheduler started")

        # Update next run times
        for job in self.scheduler.get_jobs():
            self.jobs[job.id]['next_run'] = job.next_run_time.isoformat() if job.next_run_time else None

        try:
            # Keep main thread alive
            while True:
                time.sleep(60)
                # Refresh next run times
                for job in self.scheduler.get_jobs():
                    self.jobs[job.id]['next_run'] = job.next_run_time.isoformat() if job.next_run_time else None
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down scheduler...")
            self.scheduler.shutdown()

    def list_jobs(self):
        """List all scheduled jobs."""
        return self.jobs

def main():
    """Main entry point for the scheduler daemon."""
    # Read schedule configuration from environment
    schedules = {
        'qa': os.getenv('QA_SCHEDULE', '0 2 * * *'),  # Daily at 2 AM
        'backend': os.getenv('BACKEND_SCHEDULE', '0 */6 * * *'),  # Every 6 hours
        'frontend': os.getenv('FRONTEND_SCHEDULE', '0 */4 * * *'),  # Every 4 hours
    }

    scheduler = AgentScheduler()

    for agent_type, cron_expr in schedules.items():
        scheduler.schedule_agent(agent_type, cron_expr)

    logger.info(f"Scheduled {len(schedules)} agents")
    scheduler.start()

if __name__ == "__main__":
    main()
