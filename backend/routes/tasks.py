from flask import Blueprint, request, jsonify, g
from models import db, Task, User, Comment, ActivityLog
from auth import login_required, log_activity, get_current_user
from datetime import datetime
import json

tasks_bp = Blueprint('tasks', __name__)

def parse_tags(tags_str):
    """Parse tags from JSON string or comma-separated string."""
    if not tags_str:
        return []
    try:
        if isinstance(tags_str, str):
            tags = json.loads(tags_str)
            if isinstance(tags, list):
                return tags
    except:
        pass
    # Fallback: comma-separated
    if isinstance(tags_str, str):
        return [t.strip() for t in tags_str.split(',') if t.strip()]
    return []

@tasks_bp.route('/tasks', methods=['GET'])
@login_required
def get_tasks():
    """Get all tasks with optional filters."""
    query = Task.query

    # Filters
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    priority = request.args.get('priority')
    if priority:
        query = query.filter_by(priority=priority)

    assigned_to = request.args.get('assigned_to')
    if assigned_to and assigned_to.isdigit():
        query = query.filter_by(assigned_to=int(assigned_to))

    due_before = request.args.get('due_before')
    if due_before:
        try:
            date = datetime.fromisoformat(due_before.replace('Z', '+00:00'))
            query = query.filter(Task.due_date <= date)
        except:
            pass

    due_after = request.args.get('due_after')
    if due_after:
        try:
            date = datetime.fromisoformat(due_after.replace('Z', '+00:00'))
            query = query.filter(Task.due_date >= date)
        except:
            pass

    # Sort by priority and due date
    query = query.order_by(
        db.case(
            (Task.priority == 'Urgent', 0),
            (Task.priority == 'High', 1),
            (Task.priority == 'Medium', 2),
            (Task.priority == 'Low', 3),
            else_=4
        ),
        Task.due_date.asc()
    )

    include_details = request.args.get('include_details', 'false').lower() == 'true'
    tasks = query.all()

    return jsonify([task.to_dict(include_details=include_details) for task in tasks]), 200

@tasks_bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    """Create a new task."""
    data = request.get_json()

    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400

    current_user = get_current_user()

    task = Task(
        title=data['title'],
        description=data.get('description'),
        status=data.get('status', 'To Do'),
        priority=data.get('priority', 'Medium'),
        assigned_to=data.get('assigned_to'),
        assigned_by=current_user.id,
        due_date=datetime.fromisoformat(data['due_date'].replace('Z', '+00:00')) if data.get('due_date') else None,
        tags=json.dumps(data.get('tags', [])) if data.get('tags') else None
    )

    db.session.add(task)
    db.session.commit()

    log_activity('create_task', {'task_id': task.id, 'title': task.title, 'created_by': current_user.id})

    return jsonify(task.to_dict(include_details=True)), 201

@tasks_bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    """Get a single task with all details."""
    task = Task.query.get_or_404(task_id)
    return jsonify(task.to_dict(include_details=True)), 200

@tasks_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """Update a task."""
    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        task.status = data['status']
    if 'priority' in data:
        task.priority = data['priority']
    if 'assigned_to' in data:
        task.assigned_to = data['assigned_to']
    if 'due_date' in data and data['due_date']:
        task.due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
    if 'tags' in data:
        task.tags = json.dumps(data['tags']) if isinstance(data['tags'], list) else data['tags']

    db.session.commit()

    log_activity('update_task', {'task_id': task.id, 'title': task.title})

    return jsonify(task.to_dict(include_details=True)), 200

@tasks_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Delete a task."""
    task = Task.query.get_or_404(task_id)
    task_title = task.title
    db.session.delete(task)
    db.session.commit()

    log_activity('delete_task', {'task_id': task_id, 'title': task_title})

    return jsonify({'message': 'Task deleted'}), 200

@tasks_bp.route('/tasks/<int:task_id>/comments', methods=['GET'])
@login_required
def get_comments(task_id):
    """Get all comments for a task."""
    task = Task.query.get_or_404(task_id)
    comments = Comment.query.filter_by(task_id=task_id).order_by(Comment.created_at.asc()).all()
    return jsonify([c.to_dict() for c in comments]), 200

@tasks_bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
def add_comment(task_id):
    """Add a comment to a task."""
    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    if not data or 'content' not in data:
        return jsonify({'error': 'Content is required'}), 400

    current_user = get_current_user()
    # Use current user as author; allow override only if explicitly provided (for system use)
    author_id = data.get('author_id', current_user.id)

    comment = Comment(
        task_id=task_id,
        author_id=author_id,
        content=data['content']
    )

    db.session.add(comment)
    db.session.commit()

    log_activity('add_comment', {'task_id': task_id, 'comment_id': comment.id, 'author_id': author_id})

    return jsonify(comment.to_dict()), 201

@tasks_bp.route('/tasks/<int:task_id>/status', methods=['PATCH'])
@login_required
def update_task_status(task_id):
    """Quick update of task status."""
    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    if 'status' in data:
        task.status = data['status']
        db.session.commit()
        log_activity('update_task_status', {'task_id': task.id, 'status': task.status})
        return jsonify(task.to_dict()), 200

    return jsonify({'error': 'Status required'}), 400
