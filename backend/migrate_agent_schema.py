#!/usr/bin/env python3
"""
Database migration: Create autonomous agent framework tables.

This script creates all necessary tables for the agent framework:
- agent_sessions
- agent_steps
- tool_calls
- approval_queue
- agent_long_term_memory
- agent_templates

Run with: python migrate_agent_schema.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

# Import existing db from extensions to avoid duplicate instances
from extensions import db
from agent_framework.database.models import (
    AgentSession, AgentStep, ToolCall, ApprovalQueue,
    AgentLongTermMemory, AgentTemplate
)

# No need to create Flask app; just use db.engine directly


def create_tables():
    """Create all agent framework tables"""
    # Check if tables already exist
    inspector = db.inspect(db.engine)
    existing_tables = inspector.get_table_names()

    agent_tables = [
        'agent_sessions',
        'agent_steps',
        'tool_calls',
        'approval_queue',
        'agent_long_term_memory',
        'agent_templates'
    ]

    to_create = [t for t in agent_tables if t not in existing_tables]

    if not to_create:
        print("All agent framework tables already exist.")
        return

    print(f"Creating tables: {', '.join(to_create)}")
    db.create_all()
    print("✓ Tables created successfully")

    # Create indexes (MySQL specific)
    print("\nCreating additional indexes...")
    with db.engine.connect() as conn:
        # Add FULLTEXT index for memory content search if using MySQL
        try:
            conn.execute("""
                CREATE FULLTEXT INDEX IF NOT EXISTS idx_agent_memory_content
                ON agent_long_term_memory(content)
            """)
            print("✓ FULLTEXT index created on agent_long_term_memory(content)")
        except Exception as e:
            print(f"  Note: FULLTEXT index may not be supported: {e}")

    print("\nMigration complete!")


def drop_tables():
    """Drop all agent framework tables (USE WITH CAUTION)"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        print("Dropping agent framework tables...")
        db.drop_all()
        print("✓ Tables dropped")


def seed_templates():
    """Insert default agent templates"""
    # Need Flask app context for db session
    from flask import Flask
    from config import Config
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        # Check if templates already exist
        existing = Template.query.count()
        if existing > 0:
            print(f"{existing} templates already exist. Skipping seed.")
            return

        print("Seeding agent templates...")

        templates = [
            {
                'name': 'system_admin',
                'description': 'General system administration assistant',
                'system_prompt': """You are a system administrator assistant.
You can execute shell commands, query databases, read files, and check system metrics.
Always be cautious and explain what you're doing before doing it.
For read-only operations, proceed without approval.
For writes or system changes, users will need to approve.""",
                'allowed_tools': [
                    'get_system_metrics',
                    'list_directory',
                    'read_file',
                    'execute_shell_command',
                    'query_database'
                ],
                'config': {'max_steps': 20, 'temperature': 0.7}
            },
            {
                'name': 'coder',
                'description': 'Software development helper',
                'system_prompt': """You are a software development assistant.
You can read and write code files, search the codebase, and run tests.
Always make backups before modifying files.
Explain your changes clearly.""",
                'allowed_tools': [
                    'list_directory',
                    'read_file',
                    'write_file',
                    'execute_shell_command',
                    'search_knowledge_base'
                ],
                'config': {'max_steps': 30, 'temperature': 0.8}
            },
            {
                'name': 'analyst',
                'description': 'Data analyst for system queries',
                'system_prompt': """You are a data analyst focused on system insights.
You can query the database to generate reports, analyze trends, and answer questions.
Read-only access only - no data modifications.""",
                'allowed_tools': [
                    'query_database',
                    'get_system_metrics',
                    'search_knowledge_base'
                ],
                'config': {'max_steps': 15, 'temperature': 0.5}
            }
        ]

        from agent_framework.database.models import AgentTemplate as Template
        for t in templates:
            template = AgentTemplate(
                name=t['name'],
                description=t['description'],
                system_prompt=t['system_prompt'],
                allowed_tools=t['allowed_tools'],
                config=t['config'],
                is_active=True
            )
            db.session.add(template)

        db.session.commit()
        print(f"✓ Created {len(templates)} agent templates")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Agent framework database migrations")
    parser.add_argument('--drop', action='store_true', help='Drop tables (use with caution)')
    parser.add_argument('--seed', action='store_true', help='Seed default templates')

    args = parser.parse_args()

    if args.drop:
        confirmed = input("Are you sure you want to DROP all agent framework tables? This cannot be undone. (yes/no): ")
        if confirmed.lower() == 'yes':
            drop_tables()
        else:
            print("Cancelled.")
    elif args.seed:
        seed_templates()
    else:
        create_tables()
