"""
Agent Sessions API endpoints for autonomous agent framework.

Provides REST endpoints for creating, managing, and querying agent sessions.
"""

from flask import Blueprint, request, jsonify
from flask import current_app
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from models import db
from agent_framework.database.handler import (
    create_agent_session as create_session,
    get_agent_session,
    list_agent_sessions,
    complete_agent_session,
    fail_agent_session,
    get_agent_steps,
    get_pending_approvals,
    respond_to_approval
)
from agent_framework.database.models import AgentSession, AgentTemplate
from agent_framework import create_agent
from agent_framework.tools.registry import default_registry
import asyncio
import threading

agent_sessions_bp = Blueprint('agent_sessions', __name__, url_prefix='/api/agent')


@agent_sessions_bp.route('/sessions', methods=['POST'])
def create_agent_session():
    """
    Create a new agent session.

    Expected JSON body:
    {
        "goal": "string - the task for the agent",
        "template_id": int (optional),
        "title": "string (optional, derived from goal if missing)"
    }

    Returns:
        { "session_id": int, "status": "running", "websocket_url": "/ws/agent/{session_id}?token=..." }
    """
    try:
        data = request.get_json()
        if not data or 'goal' not in data:
            return jsonify({'error': 'Goal is required'}), 400

        goal = data['goal']
        template_id = data.get('template_id')

        # Get user from auth context (assuming you have auth middleware)
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        # Generate title from goal if not provided
        title = data.get('title') or goal[:100] + ('...' if len(goal) > 100 else '')

        # Create session in database
        db_session = db.session
        session = create_session(
            db_session=db_session,
            user_id=user.id,
            title=title,
            conversation_id=None,
            template_id=template_id
        )
        db.session.commit()

        current_app.logger.info(f"Created agent session {session.id} for user {user.id}")

        # Generate WebSocket URL (will be used with actual token)
        ws_url = f"/ws/agent/{session.id}?token={token}"

        return jsonify({
            'session_id': session.id,
            'status': 'running',
            'title': session.title,
            'websocket_url': ws_url,
            'created_at': session.created_at.isoformat() if session.created_at else None
        }), 201

    except Exception as e:
        current_app.logger.error(f"Failed to create agent session: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to create session', 'details': str(e)}), 500


@agent_sessions_bp.route('/sessions', methods=['GET'])
def get_agent_sessions():
    """
    List agent sessions for current user.

    Query params:
        status: filter by status (running, completed, failed, awaiting_approval)
        limit: max results (default 50)
        offset: pagination offset (default 0)

    Returns:
        { "sessions": [session_dict, ...], "total": int }
    """
    try:
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        status = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))

        db_session = db.session
        sessions = list_agent_sessions(
            db_session=db_session,
            user_id=user.id,
            status=status,
            limit=limit,
            offset=offset
        )

        # Count total (simplified - could optimize with separate count query)
        total = AgentSession.query.filter_by(user_id=user.id)
        if status:
            total = total.filter_by(status=status)
        total = total.count()

        return jsonify({
            'sessions': [s.to_dict() for s in sessions],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to list agent sessions: {e}")
        return jsonify({'error': 'Failed to fetch sessions', 'details': str(e)}), 500


@agent_sessions_bp.route('/sessions/<int:session_id>', methods=['GET'])
def get_agent_session(session_id):
    """
    Get a specific agent session with its steps.

    Returns:
        { "session": session_dict, "steps": [step_dict, ...], "pending_approvals": [...] }
    """
    try:
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        db_session = db.session
        session = get_agent_session(db_session, session_id=session_id, user_id=user.id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Get steps
        steps = get_agent_steps(db_session, session_id=session_id)

        # Get pending approvals
        pending = get_pending_approvals(db_session, session_id=session_id)

        return jsonify({
            'session': session.to_dict(),
            'steps': [s.to_dict() for s in steps],
            'pending_approvals': [p.to_dict() for p in pending]
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to get agent session {session_id}: {e}")
        return jsonify({'error': 'Failed to fetch session', 'details': str(e)}), 500


@agent_sessions_bp.route('/sessions/<int:session_id>/approve', methods=['POST'])
def approve_action(session_id):
    """
    Approve or deny a pending action for an agent session.

    Expected JSON body:
    {
        "approved": boolean,
        "comment": "string (optional)"
    }

    Returns:
        { "status": "ok" }
    """
    try:
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json()
        if data is None:
            return jsonify({'error': 'Request body required'}), 400

        approved = data.get('approved')
        comment = data.get('comment', '')

        if approved is None:
            return jsonify({'error': 'approved field is required'}), 400

        db_session = db.session

        # Find the pending approval for this session
        pending = get_pending_approvals(db_session, session_id=session_id, limit=1)
        if not pending:
            return jsonify({'error': 'No pending approval found for this session'}), 404

        approval = pending[0]

        # Record the response
        approval = respond_to_approval(
            db_session=db_session,
            approval_id=approval.id,
            approved=approved,
            responded_by=user.id,
            comment=comment
        )
        db.session.commit()

        current_app.logger.info(f"Approval {approval.id} for session {session_id}: {'approved' if approved else 'denied'} by user {user.id}")

        return jsonify({'status': 'ok', 'approval_id': approval.id}), 200

    except Exception as e:
        current_app.logger.error(f"Failed to approve action for session {session_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process approval', 'details': str(e)}), 500


@agent_sessions_bp.route('/sessions/<int:session_id>/cancel', methods=['POST'])
def cancel_agent_session(session_id):
    """
    Cancel a running agent session.

    Returns:
        { "status": "cancelled" }
    """
    try:
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        db_session = db.session
        session = get_agent_session(db_session, session_id=session_id, user_id=user.id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status not in ['running', 'awaiting_approval']:
            return jsonify({'error': f'Cannot cancel session in {session.status} status'}), 400

        # Mark session as failed with cancellation message
        fail_agent_session(
            db_session=db_session,
            session_id=session_id,
            error='Session cancelled by user'
        )
        db.session.commit()

        current_app.logger.info(f"Cancelled agent session {session_id} by user {user.id}")

        return jsonify({'status': 'cancelled'}), 200

    except Exception as e:
        current_app.logger.error(f"Failed to cancel session {session_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel session', 'details': str(e)}), 500


@agent_sessions_bp.route('/templates', methods=['GET'])
def list_agent_templates():
    """
    List available agent templates.

    Returns:
        { "templates": [template_dict, ...] }
    """
    try:
        db_session = db.session
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        templates = AgentTemplate.query.filter_by(is_active=True).order_by(AgentTemplate.name).all()

        return jsonify({
            'templates': [t.to_dict() for t in templates]
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to list templates: {e}")
        return jsonify({'error': 'Failed to fetch templates', 'details': str(e)}), 500


@agent_sessions_bp.route('/tools', methods=['GET'])
def list_available_tools():
    """
    List all available tools (for debugging/admin).

    Returns:
        { "tools": [tool_dict, ...] }
    """
    try:
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        # Only admin users can see all tools (optional restriction)
        # For now, all authenticated users can see

        tools = default_registry.list_tools()

        return jsonify({
            'tools': tools,
            'count': len(tools)
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to list tools: {e}")
        return jsonify({'error': 'Failed to fetch tools', 'details': str(e)}), 500
