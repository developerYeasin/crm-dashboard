"""
Chat routes for AI conversation interface.
"""

from flask import Blueprint, request, jsonify, g
from models import db, Conversation, Message, AIOperation
from auth import login_required, get_current_user, admin_required
from ai_service_v2 import PowerfulAIService, create_conversation, get_conversation, list_conversations, add_message

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations for the current user."""
    user = get_current_user()
    conversations = list_conversations(user.id)
    return jsonify([conv.to_dict() for conv in conversations]), 200


@chat_bp.route('/chat/conversations', methods=['POST'])
@login_required
def create_conversation_endpoint():
    """Create a new conversation."""
    user = get_current_user()
    data = request.get_json() or {}
    title = data.get('title')

    conv = create_conversation(user.id, title)
    if not conv:
        return jsonify({'error': 'Failed to create conversation'}), 500

    return jsonify(conv.to_dict()), 201


@chat_bp.route('/chat/conversations/<int:conv_id>', methods=['GET'])
@login_required
def get_conversation_endpoint(conv_id):
    """Get a specific conversation with its messages."""
    user = get_current_user()
    conv = get_conversation(user.id, conv_id)
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404

    messages = Message.query.filter_by(conversation_id=conv_id)\
        .order_by(Message.created_at.asc())\
        .all()
    result = conv.to_dict()
    result['messages'] = [msg.to_dict() for msg in messages]
    return jsonify(result), 200


@chat_bp.route('/chat/conversations/<int:conv_id>/messages', methods=['POST'])
@login_required
def send_message(conv_id):
    """Send a message to the AI and get a response."""
    user = get_current_user()
    conv = get_conversation(user.id, conv_id)
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message content required'}), 400

    user_message = data['message']

    # Add user message to conversation
    add_message(conv_id, 'user', user_message)

    # Initialize powerful AI service (no approval for immediate execution)
    ai = PowerfulAIService(user, require_approval=True)
    try:
        ai_response = ai.generate_response(conv_id, user_message)
    except Exception as e:
        ai_response = f"Error generating response: {str(e)}"

    # Add assistant message to conversation
    assistant_msg = add_message(conv_id, 'assistant', ai_response)

    return jsonify({
        'user_message': user_message,
        'assistant_response': ai_response,
        'message_id': assistant_msg.id
    }), 200


@chat_bp.route('/chat/conversations/<int:conv_id>', methods=['DELETE'])
@login_required
def delete_conversation(conv_id):
    """Delete a conversation."""
    user = get_current_user()
    conv = get_conversation(user.id, conv_id)
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404

    db.session.delete(conv)
    db.session.commit()
    return jsonify({'message': 'Conversation deleted'}), 200


# Admin AI Operations endpoints
@chat_bp.route('/admin/ai/operations', methods=['GET'])
@admin_required
def list_ai_operations():
    """List all AI operations (admin only)."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    status_filter = request.args.get('status')

    query = AIOperation.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    operations = query.order_by(AIOperation.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'operations': [op.to_dict() for op in operations.items],
        'total': operations.total,
        'pages': operations.pages,
        'page': page
    }), 200


@chat_bp.route('/admin/ai/operations/<int:op_id>/approve', methods=['POST'])
@admin_required
def approve_operation(op_id):
    """Approve a pending AI operation."""
    op = AIOperation.query.get_or_404(op_id)
    if op.status != 'pending':
        return jsonify({'error': 'Operation not pending'}), 400

    admin_user = get_current_user()
    op.status = 'approved'
    op.approved_by = admin_user.id
    op.executed_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Operation approved', 'operation': op.to_dict()}), 200


@chat_bp.route('/admin/ai/operations/<int:op_id>/reject', methods=['POST'])
@admin_required
def reject_operation(op_id):
    """Reject a pending AI operation."""
    op = AIOperation.query.get_or_404(op_id)
    if op.status != 'pending':
        return jsonify({'error': 'Operation not pending'}), 400

    op.status = 'rejected'
    op.approved_by = get_current_user().id
    op.executed_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Operation rejected', 'operation': op.to_dict()}), 200


@chat_bp.route('/admin/ai/operations/stats', methods=['GET'])
@admin_required
def get_ai_operation_stats():
    """Get statistics about AI operations."""
    total = AIOperation.query.count()
    by_status = db.session.query(
        AIOperation.status, db.func.count(AIOperation.id)
    ).group_by(AIOperation.status).all()

    recent = AIOperation.query.order_by(AIOperation.created_at.desc()).limit(10).all()

    return jsonify({
        'total': total,
        'by_status': dict(by_status),
        'recent': [op.to_dict() for op in recent]
    }), 200


@chat_bp.route('/admin/ai/operations/<int:op_id>/execute', methods=['POST'])
@admin_required
def execute_operation(op_id):
    """Manually execute a pending operation (admin only)."""
    op = AIOperation.query.get_or_404(op_id)
    if op.status != 'pending':
        return jsonify({'error': 'Operation not pending'}), 400

    admin_user = get_current_user()

    # Recreate the operation
    try:
        params = json.loads(op.parameters) if op.parameters else {}
        action_type = op.action_type

        # Create temporary AI service to execute
        ai = PowerfulAIService(op.user, require_approval=False)

        if action_type == 'create_task':
            result = ai._create_task(params)
            status = 'completed'
        elif action_type in ['execute_command', 'create_cron_job', 'list_cron_jobs',
                            'delete_cron_job', 'restart_service', 'system_status',
                            'backup_database', 'read_file', 'write_file']:
            result = ai._execute_function(action_type, params)
            status = 'completed' if result.get('success') else 'failed'
        else:
            return jsonify({'error': f'Unknown action type: {action_type}'}), 400

        # Update operation
        op.status = status
        op.approved_by = admin_user.id
        op.result = json.dumps(result)
        op.executed_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': f'Operation {status}', 'result': result, 'operation': op.to_dict()}), 200

    except Exception as e:
        op.status = 'failed'
        op.result = json.dumps({'error': str(e)})
        op.executed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'error': str(e), 'operation': op.to_dict()}), 500
