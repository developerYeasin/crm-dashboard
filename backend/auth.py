from datetime import datetime, timedelta
import jwt
from flask import request, jsonify, g
from config import Config
from models import db, User, ActivityLog
from bcrypt import checkpw, hashpw, gensalt

def authenticate_user(email, password):
    """Authenticate a user by email and password."""
    user = User.query.filter_by(email=email).first()
    if user and user.is_active:
        # If user has a password_hash, verify it
        if user.password_hash:
            if checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return user
        else:
            # Backward compatibility: check against ADMIN_PASSWORD_HASH in config
            if Config.ADMIN_PASSWORD_HASH:
                stored_hash = Config.ADMIN_PASSWORD_HASH.encode('utf-8')
                if checkpw(password.encode('utf-8'), stored_hash):
                    # Migrate: set the user's password hash for future logins
                    from bcrypt import hashpw, gensalt
                    new_hash = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
                    user.password_hash = new_hash
                    db.session.commit()
                    return user
    return None

def generate_token(user):
    """Generate JWT token for a user."""
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=7)  # 7 day expiry
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify the JWT token and return user if valid."""
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user and user.is_active:
                return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    return None

def login_required(f):
    """Decorator to protect routes requiring authentication."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        print(f"[DEBUG login_required] auth_header: {auth_header}")
        token = auth_header.replace('Bearer ', '')
        print(f"[DEBUG login_required] token (len={len(token)}): {token[:30]}...")
        if not token:
            return jsonify({'error': 'Authentication required'}), 401

        user = verify_token(token)
        print(f"[DEBUG login_required] user: {user}")
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Store user in flask.g for access in route handlers
        g.current_user = user
        print(f"[DEBUG login_required] stored in g.current_user: {g.current_user}")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to protect routes requiring admin role."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authentication required'}), 401

        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        if user.role != 'Administrator':
            return jsonify({'error': 'Administrator access required'}), 403

        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the currently authenticated user from flask.g."""
    return g.get('current_user')

def log_activity(action, details=None, commit=True):
    """Log an activity to the database."""
    try:
        log = ActivityLog(
            action=action,
            details=details
        )
        db.session.add(log)
        if commit:
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Failed to log activity: {e}")
