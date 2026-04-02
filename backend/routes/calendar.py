from flask import Blueprint, request, jsonify
from models import Task
from auth import login_required
from datetime import datetime, timedelta

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/calendar/tasks', methods=['GET'])
@login_required
def get_calendar_tasks():
    """
    Get tasks for calendar view.
    Supports date range filtering (start, end parameters in ISO format).
    Returns tasks with minimal info for calendar display.
    """
    start_date = request.args.get('start')
    end_date = request.args.get('end')

    query = Task.query.filter(Task.due_date.isnot(None))

    if start_date:
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Task.due_date >= start)
        except:
            pass

    if end_date:
        try:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Task.due_date <= end)
        except:
            pass

    tasks = query.all()

    # Format for calendar - return minimal data
    calendar_events = []
    for task in tasks:
        event = {
            'id': task.id,
            'title': task.title,
            'start': task.due_date.isoformat(),
            'end': task.due_date.isoformat(),  # All-day event, start and end same
            'priority': task.priority,
            'status': task.status,
            'assigned_to': task.assigned_to,
            'assigned_to_name': task.assignee.name if task.assignee else None
        }
        calendar_events.append(event)

    return jsonify(calendar_events), 200

@calendar_bp.route('/calendar/day/<date>', methods=['GET'])
@login_required
def get_tasks_by_date(date):
    """
    Get all tasks for a specific date.
    Date format: YYYY-MM-DD
    """
    try:
        target_date = datetime.fromisoformat(date)
        # Set start and end of day
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        tasks = Task.query.filter(
            Task.due_date >= day_start,
            Task.due_date < day_end
        ).order_by(
            Task.priority.desc()  # High priority first
        ).all()

        return jsonify([t.to_dict() for t in tasks]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
