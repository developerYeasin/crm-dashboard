from flask import Blueprint, request, jsonify
from models import db
from auth import generate_token, log_activity, login_required, get_current_user, authenticate_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login with email and password."""
    data = request.get_json()

    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password required'}), 400

    email = data['email'].lower().strip()
    password = data['password']

    user = authenticate_user(email, password)
    # Debug logging
    print(f"[LOGIN DEBUG] email={email}, user_found={user is not None}")
    if user:
        print(f"[LOGIN DEBUG] user.id={user.id}, is_active={user.is_active}")
    else:
        # Check if user exists at all
        from models import User
        test_user = User.query.filter_by(email=email).first()
        print(f"[LOGIN DEBUG] User exists in DB: {test_user is not None}")
        if test_user:
            print(f"[LOGIN DEBUG] DB user is_active={test_user.is_active}")

    if user:
        token = generate_token(user)
        log_activity('login', {'user_id': user.id, 'email': user.email, 'ip': request.remote_addr}, commit=True)
        return jsonify({
            'token': token,
            'user': user.to_dict(),
            'message': 'Login successful'
        }), 200
    else:
        log_activity('login_failed', {'email': email, 'ip': request.remote_addr}, commit=True)
        return jsonify({'error': 'Invalid email or password'}), 401

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout - client should remove token."""
    user = get_current_user()
    log_activity('logout', {'user_id': user.id if user else None, 'ip': request.remote_addr}, commit=True)
    return jsonify({'message': 'Logged out'}), 200

@auth_bp.route('/verify', methods=['GET'])
@login_required
def verify_token():
    """Verify current token is valid and return user info."""
    user = get_current_user()
    return jsonify({
        'valid': True,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change the current user's password."""
    user = get_current_user()
    data = request.get_json()

    if not data or 'current_password' not in data or 'new_password' not in data:
        return jsonify({'error': 'Current password and new password are required'}), 400

    # Verify current password
    from bcrypt import checkpw
    if not user.password_hash:
        return jsonify({'error': 'No password set for this account'}), 400

    if not checkpw(data['current_password'].encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Current password is incorrect'}), 401

    # Set new password
    new_hash = hashpw(data['new_password'].encode('utf-8'), gensalt()).decode('utf-8')
    user.password_hash = new_hash
    db.session.commit()

    log_activity('change_password', {'user_id': user.id})

    return jsonify({'message': 'Password changed successfully'}), 200
