"""
Cron Daemon for AI-managed cron jobs
This script reads cron jobs from the database and executes them on schedule.

Run this as a background process or systemd service.
"""

import os
import time
import subprocess
from datetime import datetime
from croniter import croniter
from flask import Flask
from extensions import db
from models import SystemCronJob
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USER', 'order_user')}:{os.getenv('DB_PASSWORD', 'order_pass')}@{os.getenv('DB_HOST', 'localhost')}:{int(os.getenv('DB_PORT', 3306))}/{os.getenv('DB_NAME', 'order_tracker')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def execute_job(job):
    """Execute a cron job command"""
    try:
        result = subprocess.run(
            job.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute max
        )

        with app.app_context():
            job.last_run = datetime.utcnow()
            job.last_output = f"Exit code: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

            # Log the execution
            from models import SystemCommandLog
            log = SystemCommandLog(
                command=job.command,
                executed_by='cron_daemon',
                output=job.last_output,
                exit_code=result.returncode,
                execution_time=0,  # Will be calculated
                status='success' if result.returncode == 0 else 'failed'
            )
            db.session.add(log)
            db.session.commit()

            print(f"[{datetime.utcnow()}] Executed job '{job.name}': exit code {result.returncode}")

    except subprocess.TimeoutExpired:
        with app.app_context():
            job.last_run = datetime.utcnow()
            job.last_output = "Error: Job timed out after 300 seconds"
            db.session.commit()
        print(f"[{datetime.utcnow()}] Job '{job.name}' timed out")
    except Exception as e:
        with app.app_context():
            job.last_run = datetime.utcnow()
            job.last_output = f"Error: {str(e)}"
            db.session.commit()
        print(f"[{datetime.utcnow()}] Job '{job.name}' failed: {str(e)}")


def main():
    """Main cron daemon loop"""
    print("Starting cron daemon...")
    print("Polling database every minute for scheduled jobs...")

    with app.app_context():
        while True:
            now = datetime.utcnow()

            # Get all enabled cron jobs
            jobs = SystemCronJob.query.filter_by(enabled=True).all()

            for job in jobs:
                try:
                    # Check if job should run now
                    cron = croniter(job.schedule, now)
                    prev_run = cron.get_prev(datetime)

                    # If the previous scheduled time is within the last minute (and we haven't run yet)
                    time_diff = (now - prev_run).total_seconds()
                    if 0 <= time_diff <= 60:
                        # Check if we already ran this minute (avoid duplicate runs)
                        if job.last_run:
                            last_run_diff = (now - job.last_run).total_seconds()
                            if last_run_diff < 60:
                                continue

                        print(f"Running scheduled job: {job.name}")
                        execute_job(job)
                except Exception as e:
                    print(f"Error checking job '{job.name}': {str(e)}")

            # Sleep for 30 seconds before checking again
            time.sleep(30)


if __name__ == '__main__':
    main()
