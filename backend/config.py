import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'order_user')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'order_pass_123!')
    MYSQL_DB = os.getenv('MYSQL_DB', 'order_tracker')
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

    # Upload settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads'))

    # WebSocket settings
    SOCKET_CORS_ALLOWED_ORIGINS = os.getenv('SOCKET_CORS_ALLOWED_ORIGINS', '*').split(',')

    # Max Model 1 settings
    MAX_MODEL1_INTERNAL_TYPE = os.getenv('MAX_MODEL1_INTERNAL_TYPE', 'embeddings')
    MAX_MODEL1_EXTERNAL_API_URL = os.getenv('MAX_MODEL1_EXTERNAL_API_URL', '')
    MAX_MODEL1_EXTERNAL_API_KEY = os.getenv('MAX_MODEL1_EXTERNAL_API_KEY', '')
    MAX_MODEL1_EXTERNAL_MODEL = os.getenv('MAX_MODEL1_EXTERNAL_MODEL', 'claude-3-5-sonnet-20241022')
    MAX_MODEL1_CONFIDENCE_THRESHOLD = float(os.getenv('MAX_MODEL1_CONFIDENCE_THRESHOLD', '0.7'))

    # Model storage paths
    MODELS_DIR = os.getenv('MODELS_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models'))
    MAX_MODEL1_PATH = os.path.join(MODELS_DIR, 'max_model1')
