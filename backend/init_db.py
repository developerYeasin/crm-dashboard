#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables and seeds initial data.
"""

import os
import json
from datetime import datetime, timedelta
from bcrypt import hashpw, gensalt
from flask import Flask
from config import Config
from models import db, User, Task, Note, KnowledgeBaseEntry, ActivityLog

def init_database():
    """Initialize database and seed data."""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ All tables created")

        # Check if team members already exist
        if User.query.count() == 0:
            # Create admin team member (the one who assigns tasks)
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            admin = User(
                name="Admin",
                email="admin@example.com",
                password_hash=hashpw(admin_password.encode('utf-8'), gensalt()).decode('utf-8'),
                is_admin=True,
                role="Administrator",
                avatar_url="https://api.dicebear.com/7.x/adventurer/svg?seed=Admin"
            )
            db.session.add(admin)
            db.session.flush()  # Get the ID

            # Create additional sample team members with default passwords
            default_password = 'password'
            members = [
                User(
                    name="Sarah Johnson",
                    email="sarah@example.com",
                    password_hash=hashpw(default_password.encode('utf-8'), gensalt()).decode('utf-8'),
                    is_admin=False,
                    role="Project Manager",
                    avatar_url="https://api.dicebear.com/7.x/adventurer/svg?seed=Sarah"
                ),
                User(
                    name="Mike Chen",
                    email="mike@example.com",
                    password_hash=hashpw(default_password.encode('utf-8'), gensalt()).decode('utf-8'),
                    is_admin=False,
                    role="Developer",
                    avatar_url="https://api.dicebear.com/7.x/adventurer/svg?seed=Mike"
                ),
                User(
                    name="Emily Davis",
                    email="emily@example.com",
                    password_hash=hashpw(default_password.encode('utf-8'), gensalt()).decode('utf-8'),
                    is_admin=False,
                    role="Designer",
                    avatar_url="https://api.dicebear.com/7.x/adventurer/svg?seed=Emily"
                ),
                User(
                    name="James Wilson",
                    email="james@example.com",
                    password_hash=hashpw(default_password.encode('utf-8'), gensalt()).decode('utf-8'),
                    is_admin=False,
                    role="Editor",
                    avatar_url="https://api.dicebear.com/7.x/adventurer/svg?seed=James"
                )
            ]

            for member in members:
                db.session.add(member)

            db.session.flush()

            # Assign admin ID for assigned_by
            admin_id = admin.id

            # Create sample tasks
            sample_tasks = [
                Task(
                    title="Design new landing page",
                    description="Create a modern, responsive landing page for the product launch.",
                    status="In Progress",
                    priority="High",
                    assigned_to=members[2].id,  # Emily (Designer)
                    assigned_by=admin_id,
                    due_date=datetime.utcnow(),
                    tags=json.dumps(["design", "landing", "urgent"])
                ),
                Task(
                    title="Fix authentication bug",
                    description="Users are experiencing issues with login after password reset.",
                    status="To Do",
                    priority="Urgent",
                    assigned_to=members[1].id,  # Mike (Developer)
                    assigned_by=admin_id,
                    due_date=datetime.utcnow(),
                    tags=json.dumps(["bug", "auth", "critical"])
                ),
                Task(
                    title="Write API documentation",
                    description="Document all endpoints for the new v2 API.",
                    status="To Do",
                    priority="Medium",
                    assigned_to=members[3].id,  # James (Editor)
                    assigned_by=admin_id,
                    due_date=None,
                    tags=json.dumps(["documentation", "api"])
                ),
                Task(
                    title="Client meeting preparation",
                    description="Prepare slides for Q2 review with Acme Corp.",
                    status="Done",
                    priority="Medium",
                    assigned_to=members[0].id,  # Sarah (PM)
                    assigned_by=admin_id,
                    due_date=datetime.utcnow() - timedelta(days=1),
                    tags=json.dumps(["meeting", "client"])
                ),
                Task(
                    title="Update dependencies",
                    description="Upgrade Flask to latest version and test compatibility.",
                    status="In Progress",
                    priority="Low",
                    assigned_to=members[1].id,  # Mike (Developer)
                    assigned_by=admin_id,
                    due_date=datetime.utcnow() + timedelta(days=7),
                    tags=json.dumps(["maintenance", "dependencies"])
                )
            ]

            for task in sample_tasks:
                db.session.add(task)

            # Create sample notes
            notes = [
                Note(
                    title="Meeting Notes - 2024-03-15",
                    content="# Client Feedback\n\n- Love the new color scheme\n- Want more animations\n- Need better mobile support\n\n**Action items:**\n- Add swipe gestures\n- Optimize images\n\n![Screenshot](https://via.placeholder.com/300x200)\n\n```javascript\nconsole.log('Hello world');\n```"
                ),
                Note(
                    title="Project Ideas",
                    content="## Q2 Goals\n\n- [ ] Launch new website\n- [ ] Mobile app beta\n- [ ] Partner integration\n\n## Long-term\n- AI features\n- Analytics dashboard\n- Multi-language support"
                )
            ]

            for note in notes:
                db.session.add(note)

            # Create sample knowledge base entries
            kb_entries = [
                KnowledgeBaseEntry(
                    title="Getting Started Guide",
                    content="# Welcome to the CRM Dashboard\n\nThis guide will help you get started with managing your tasks and team.\n\n## Features\n\n- Task management with priorities\n- Team collaboration\n- Calendar view\n- Notes and knowledge base\n\n## Login\n\nUse the admin password configured in your `.env` file to log in.",
                    category="Guides"
                ),
                KnowledgeBaseEntry(
                    title="Keyboard Shortcuts",
                    content="## Available Shortcuts\n\n| Key | Action |\n|-----|--------|\n| N | Create new task |\n| / | Search |\n| T | Go to Tasks |\n| C | Go to Calendar |\n| M | Toggle theme |\n\n**Note:** Shortcuts work from anywhere in the app.",
                    category="Reference"
                ),
                KnowledgeBaseEntry(
                    title="Task Priority Definitions",
                    content="## Priority Levels\n\n- **Urgent**: Needs immediate attention, blocks critical work\n- **High**: Important, should be done soon\n- **Medium**: Normal priority, within sprint/iteration\n- **Low**: Nice to have, can be deprioritized\n\n## When to use each\n\nUse **Urgent** sparingly - only for true emergencies that require immediate action.",
                    category="Process"
                ),
                KnowledgeBaseEntry(
                    title="Team Roles and Responsibilities",
                    content="## Role Descriptions\n\n- **Administrator**: Full access, manages team and settings\n- **Project Manager**: Creates and assigns tasks, tracks progress\n- **Developer**: Works on technical tasks, updates status\n- **Designer**: Creates visual assets, reviews designs\n- **Editor**: Reviews content, proofreads\n\n## Escalation Path\n\n1. Team member → PM\n2. PM → Admin\n3. Admin → Stakeholder",
                    category="Team"
                )
            ]

            for entry in kb_entries:
                db.session.add(entry)

            db.session.commit()
            print("✓ Sample data seeded")
        else:
            print("ℹ Team members already exist, skipping seed data")

        # Print credentials info
        if User.query.count() > 0:
            print("\n🔐 Default account credentials:")
            print("   Admin: admin@example.com / admin123")
            print("   Sarah (PM): sarah@example.com / password")
            print("   Mike (Dev): mike@example.com / password")
            print("   Emily (Designer): emily@example.com / password")
            print("   James (Editor): james@example.com / password")
            print("\n⚠️  Change these passwords after first login!")

        print("\n✓ Database initialization complete!")

if __name__ == '__main__':
    init_database()
