from flask import Blueprint, request, jsonify
from models import db, ActivityLog, Task
from auth import login_required, log_activity
from datetime import datetime, timedelta
import json

activity_bp = Blueprint('activity', __name__)

@activity_bp.route('/activity', methods=['GET'])
@login_required
def get_activity_log():
    """Get recent activity log entries."""
    limit = request.args.get('limit', 50, type=int)
    activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
    return jsonify([a.to_dict() for a in activities]), 200

@activity_bp.route('/stats/dashboard', methods=['GET'])
@login_required
def get_dashboard_stats():
    """
    Get dashboard statistics:
    - Total tasks
    - Tasks in progress
    - Overdue tasks
    - Completed this week
    """
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())  # Monday of current week
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    total_tasks = Task.query.count()
    in_progress = Task.query.filter_by(status='In Progress').count()
    overdue = Task.query.filter(
        Task.due_date < now,
        Task.status != 'Done'
    ).count()
    completed_this_week = Task.query.filter(
        Task.status == 'Done',
        Task.updated_at >= week_start
    ).count()

    return jsonify({
        'total': total_tasks,
        'in_progress': in_progress,
        'overdue': overdue,
        'completed_this_week': completed_this_week
    }), 200

@activity_bp.route('/stats/recent-activity', methods=['GET'])
@login_required
def get_recent_activity():
    """Get recent activity for the dashboard feed."""
    limit = request.args.get('limit', 5, type=int)
    activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()

    # Enhance activity details with related data
    result = []
    for activity in activities:
        item = activity.to_dict()
        details = {}

        try:
            if activity.details:
                if isinstance(activity.details, str):
                    details = json.loads(activity.details)
                else:
                    details = activity.details
        except:
            details = {}

        # Add related data
        if activity.action in ['create_task', 'update_task', 'delete_task'] and details.get('task_id'):
            task = Task.query.get(details['task_id'])
            if task:
                details['task_title'] = task.title

        item['details'] = details
        result.append(item)

    return jsonify(result), 200
