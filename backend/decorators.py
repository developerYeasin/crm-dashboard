from flask import request, jsonify
from models import db, User


def token_required(f):
    """Decorator to protect routes that require authentication"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401

        token = auth_header.split(' ')[1]

        user = User.query.filter_by(current_token=token).first()

        if not user:
            return jsonify({'error': 'Invalid token'}), 401

        # Pass user to the route function
        return f(user, *args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator for admin-only routes"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401

        token = auth_header.split(' ')[1]

        user = User.query.filter_by(current_token=token, is_admin=True).first()

        if not user:
            return jsonify({'error': 'Admin access required'}), 403

        return f(user, *args, **kwargs)

    return decorated_function
