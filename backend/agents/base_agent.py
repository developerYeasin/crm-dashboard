#!/usr/bin/env python3
"""
Base class for all AI agents in the order-tracker system.
Provides common functionality for logging, command execution, and file operations.
"""
import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from models import db, ActivityLog

class BaseAgent:
    """Base class for all specialized agents."""

    def __init__(self, agent_type: str, agent_name: str):
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.project_root = ROOT_DIR
        self.backend_dir = self.project_root / 'backend'
        self.frontend_dir = self.project_root / 'frontend'
        self.logs = []
        self.start_time = None
        self.end_time = None

    def log(self, message: str, level: str = "INFO"):
        """Log a message to console and internal logs."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        print(log_entry)

    def log_activity(self, action: str, details: Optional[str] = None, order_id: Optional[int] = None):
        """Log activity to the database."""
        try:
            # We need an app context to use db
            from app import create_app
            app = create_app()
            with app.app_context():
                # Check if ActivityLog model has 'order_id' column (order-tracker has it, CRM doesn't)
                log_kwargs = {
                    'action': f"{self.agent_name}: {action}",
                    'details': details[:500] if details else None
                }
                if hasattr(ActivityLog, 'order_id'):
                    log_kwargs['order_id'] = order_id  # Can be None for system activities

                log = ActivityLog(**log_kwargs)
                db.session.add(log)
                db.session.commit()
                self.log(f"Logged to database: {action}")
        except Exception as e:
            self.log(f"Failed to log to database: {e}", "ERROR")

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        working_dir = cwd or self.project_root
        self.log(f"Running: {' '.join(cmd)} in {working_dir}")

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=capture_output,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if result.stdout:
                self.log(f"STDOUT: {result.stdout[:500]}")
            if result.stderr:
                self.log(f"STDERR: {result.stderr[:500]}", "WARNING")
            return result
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out: {' '.join(cmd)}", "ERROR")
            raise
        except Exception as e:
            self.log(f"Command failed: {e}", "ERROR")
            raise

    def read_file(self, relative_path: str) -> str:
        """Read a file from the project."""
        file_path = self.project_root / relative_path
        self.log(f"Reading file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_file(self, relative_path: str, content: str):
        """Write to a file in the project."""
        file_path = self.project_root / relative_path
        self.log(f"Writing file: {file_path}")
        # Create backup first
        backup_path = str(file_path) + '.bak'
        if file_path.exists():
            import shutil
            shutil.copy2(file_path, backup_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists."""
        file_path = self.project_root / relative_path
        return file_path.exists()

    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[Path]:
        """List files in a directory, optionally filtering by pattern."""
        dir_path = self.project_root / directory
        if pattern:
            import glob
            return [Path(p) for p in glob.glob(str(dir_path / pattern), recursive=True)]
        else:
            return list(dir_path.rglob('*'))

    def start(self):
        """Start the agent execution."""
        self.start_time = datetime.now()
        self.log(f"🚀 {self.agent_name} started")
        self.log_activity("Agent Started", f"Start time: {self.start_time}")

    def complete(self, success: bool = True, summary: Optional[str] = None):
        """Complete the agent execution."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        status = "completed successfully" if success else "failed"
        self.log(f"✅ {self.agent_name} {status} (duration: {duration:.2f}s)")

        details = f"Duration: {duration:.2f}s\nSummary: {summary or 'No summary'}\nTotal logs: {len(self.logs)}"
        self.log_activity("Agent Completed" if success else "Agent Failed", details)

    def get_logs(self) -> List[str]:
        """Get all logs from this run."""
        return self.logs

    def run(self) -> bool:
        """
        Main execution method - to be implemented by subclasses.
        Returns True if successful, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement run()")
