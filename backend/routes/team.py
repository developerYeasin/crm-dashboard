from flask import Blueprint, request, jsonify, g
from models import db, User, Task
from auth import login_required, admin_required, log_activity, get_current_user
from bcrypt import hashpw, gensalt

team_bp = Blueprint('team', __name__)

@team_bp.route('/team', methods=['GET'])
@login_required
def get_team_members():
    """Get all team members."""
    members = User.query.all()
    return jsonify([m.to_dict() for m in members]), 200

@team_bp.route('/team/<int:member_id>', methods=['GET'])
@login_required
def get_team_member(member_id):
    """Get a single team member with their tasks."""
    member = User.query.get_or_404(member_id)
    data = member.to_dict()
    # Include tasks assigned to this member
    tasks = Task.query.filter_by(assigned_to=member_id).all()
    data['tasks'] = [t.to_dict() for t in tasks]
    return jsonify(data), 200

@team_bp.route('/team', methods=['POST'])
@admin_required
def create_team_member():
    """Create a new team member (admin only)."""
    data = request.get_json()

    if not data or 'name' not in data or 'email' not in data:
        return jsonify({'error': 'Name and email are required'}), 400

    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400

    # Hash password if provided
    password_hash = None
    if data.get('password'):
        password_hash = hashpw(data['password'].encode('utf-8'), gensalt()).decode('utf-8')

    member = User(
        name=data['name'],
        role=data.get('role', 'Team Member'),
        avatar_url=data.get('avatar_url'),
        email=data['email'],
        password_hash=password_hash,
        is_active=data.get('is_active', True)
    )

    db.session.add(member)
    db.session.commit()

    log_activity('create_team_member', {'member_id': member.id, 'name': member.name, 'email': member.email})

    return jsonify(member.to_dict()), 201

@team_bp.route('/team/<int:member_id>', methods=['PUT'])
@admin_required
def update_team_member(member_id):
    """Update a team member (admin only)."""
    member = User.query.get_or_404(member_id)
    data = request.get_json()

    if 'name' in data:
        member.name = data['name']
    if 'role' in data:
        member.role = data['role']
    if 'avatar_url' in data:
        member.avatar_url = data['avatar_url']
    if 'email' in data:
        # Check if email is taken by another member
        existing = User.query.filter_by(email=data['email']).first()
        if existing and existing.id != member_id:
            return jsonify({'error': 'Email already in use'}), 400
        member.email = data['email']
    if 'is_active' in data:
        member.is_active = bool(data['is_active'])
    if 'password' in data and data['password']:
        member.password_hash = hashpw(data['password'].encode('utf-8'), gensalt()).decode('utf-8')

    db.session.commit()
    log_activity('update_team_member', {'member_id': member.id, 'name': member.name})

    return jsonify(member.to_dict()), 200

@team_bp.route('/team/<int:member_id>', methods=['DELETE'])
@admin_required
def delete_team_member(member_id):
    """Delete a team member (admin only)."""
    member = User.query.get_or_404(member_id)
    member_name = member.name
    db.session.delete(member)
    db.session.commit()

    log_activity('delete_team_member', {'member_id': member_id, 'name': member_name})

    return jsonify({'message': 'Team member deleted'}), 200
