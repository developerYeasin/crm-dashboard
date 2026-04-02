import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'crm_user')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'crm_password')
    MYSQL_DB = os.getenv('MYSQL_DB', 'crm_dashboard')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))

    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Admin password hash (we'll generate this in init_db)
    ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')

    # Email configuration (optional)
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_FROM = os.getenv('SMTP_FROM', 'noreply@yourdomain.com')

    # Slack webhook
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

    # App settings
    PORT = int(os.getenv('PORT', 8087))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
