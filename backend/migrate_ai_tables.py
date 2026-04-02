"""Migration script to create AI assistant tables"""
import os
from flask import Flask
from extensions import db
from models import (
    AIConversation, AIMessage, AIAction, SystemCronJob,
    SystemCommandLog, SystemMetric
)
from dotenv import load_dotenv

load_dotenv()

def create_ai_tables():
    """Create all AI-related tables"""
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'order-tracker-secret-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USER', 'order_user')}:{os.getenv('DB_PASSWORD', 'order_pass')}@{os.getenv('DB_HOST', 'localhost')}:{int(os.getenv('DB_PORT', 3306))}/{os.getenv('DB_NAME', 'order_tracker')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        print("Creating AI assistant tables...")

        # Create all tables (including existing ones)
        db.create_all()

        print("✓ All tables are up to date!")
        print("  New tables created (if they didn't exist):")
        print("  - ai_conversations")
        print("  - ai_messages")
        print("  - ai_actions")
        print("  - system_cron_jobs")
        print("  - system_command_logs")
        print("  - system_metrics")

if __name__ == '__main__':
    create_ai_tables()
