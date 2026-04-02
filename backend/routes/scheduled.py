from flask import Blueprint, request, jsonify
from models import db, ScheduledReminder, Task
from auth import login_required, log_activity
from datetime import datetime

scheduled_bp = Blueprint('scheduled', __name__)

@scheduled_bp.route('/scheduled', methods=['GET'])
@login_required
def get_scheduled_reminders():
    """Get upcoming scheduled reminders."""
    upcoming_only = request.args.get('upcoming', 'true').lower() == 'true'

    query = ScheduledReminder.query

    if upcoming_only:
        query = query.filter(ScheduledReminder.scheduled_for >= datetime.utcnow())

    reminders = query.order_by(ScheduledReminder.scheduled_for.asc()).all()
    return jsonify([r.to_dict() for r in reminders]), 200

@scheduled_bp.route('/scheduled', methods=['POST'])
@login_required
def create_scheduled_reminder():
    """Create a new scheduled reminder."""
    data = request.get_json()

    if not data or 'reminder_type' not in data or 'scheduled_for' not in data:
        return jsonify({'error': 'Reminder type and scheduled_for are required'}), 400

    try:
        scheduled_for = datetime.fromisoformat(data['scheduled_for'].replace('Z', '+00:00'))
    except:
        return jsonify({'error': 'Invalid scheduled_for format'}), 400

    reminder = ScheduledReminder(
        task_id=data.get('task_id'),
        reminder_type=data['reminder_type'],  # 'email', 'slack', 'in-app'
        scheduled_for=scheduled_for,
        message=data.get('message')
    )

    db.session.add(reminder)
    db.session.commit()

    log_activity('create_scheduled_reminder', {'reminder_id': reminder.id})

    return jsonify(reminder.to_dict()), 201

@scheduled_bp.route('/scheduled/<int:reminder_id>', methods=['PUT'])
@login_required
def update_scheduled_reminder(reminder_id):
    """Update a scheduled reminder."""
    reminder = ScheduledReminder.query.get_or_404(reminder_id)
    data = request.get_json()

    if 'reminder_type' in data:
        reminder.reminder_type = data['reminder_type']
    if 'scheduled_for' in data:
        try:
            reminder.scheduled_for = datetime.fromisoformat(data['scheduled_for'].replace('Z', '+00:00'))
        except:
            return jsonify({'error': 'Invalid scheduled_for format'}), 400
    if 'message' in data:
        reminder.message = data['message']

    db.session.commit()
    log_activity('update_scheduled_reminder', {'reminder_id': reminder.id})

    return jsonify(reminder.to_dict()), 200

@scheduled_bp.route('/scheduled/<int:reminder_id>', methods=['DELETE'])
@login_required
def delete_scheduled_reminder(reminder_id):
    """Delete a scheduled reminder."""
    reminder = ScheduledReminder.query.get_or_404(reminder_id)
    db.session.delete(reminder)
    db.session.commit()

    log_activity('delete_scheduled_reminder', {'reminder_id': reminder_id})

    return jsonify({'message': 'Reminder deleted'}), 200

@scheduled_bp.route('/scheduled/<int:reminder_id>/send', methods=['POST'])
@login_required
def send_reminder_now(reminder_id):
    """Manually trigger a reminder to be sent immediately."""
    reminder = ScheduledReminder.query.get_or_404(reminder_id)

    # In a real implementation, this would queue an email/slack notification
    # For now, just mark as sent
    reminder.sent = True
    reminder.sent_at = datetime.utcnow()
    db.session.commit()

    log_activity('send_reminder_now', {'reminder_id': reminder_id})

    return jsonify({'message': 'Reminder sent', 'reminder': reminder.to_dict()}), 200
