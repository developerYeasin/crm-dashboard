from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from models import db
from datetime import datetime

# Import route blueprints
from routes.auth import auth_bp
from routes.tasks import tasks_bp
from routes.team import team_bp
from routes.notes import notes_bp
from routes.kb import kb_bp
from routes.calendar import calendar_bp
from routes.activity import activity_bp
from routes.scheduled import scheduled_bp
from routes.agents import agents_bp
from routes.ai_chat import ai_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS
    CORS(app, supports_credentials=True)

    # Initialize database
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)  # /login, /logout, /verify, /change-password
    app.register_blueprint(tasks_bp)  # /tasks
    app.register_blueprint(team_bp)   # /team
    app.register_blueprint(notes_bp)  # /notes
    app.register_blueprint(kb_bp)     # /kb
    app.register_blueprint(calendar_bp)  # /calendar
    app.register_blueprint(activity_bp)  # /activity
    app.register_blueprint(scheduled_bp) # /scheduled
    app.register_blueprint(agents_bp)    # /agents
    app.register_blueprint(ai_bp, url_prefix='/api/ai')  # /api/ai/chat, /api/ai/execute, etc.

    # Health check
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
