"""
Agent Memories API endpoints.

Provides access to the agent's long-term memory store.
"""

from flask import Blueprint, request, jsonify
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from agent_framework.database.handler import (
    search_memories,
    forget_old_memories,
    AgentLongTermMemory
)
from agent_framework.database.models import db

agent_memories_bp = Blueprint('agent_memories', __name__, url_prefix='/api/agent/memories')


@agent_memories_bp.route('', methods=['GET'])
def get_memories():
    """
    Search agent long-term memories.

    Query params:
        q: search query (searches content)
        type: filter by memory_type (fact, preference, skill, error, success)
        limit: max results (default 20)
        user_id: (optional, defaults to current user)

    Returns:
        { "memories": [memory_dict, ...], "total": int }
    """
    try:
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        query_text = request.args.get('q', '')
        memory_type = request.args.get('type')
        limit = min(int(request.args.get('limit', 20)), 100)
        user_id = request.args.get('user_id', type=int) or user.id

        db_session = db.session
        memories = search_memories(
            db_session=db_session,
            user_id=user_id,
            query_text=query_text if query_text else None,
            memory_type=memory_type,
            limit=limit
        )

        # Also get total count for this user
        total = AgentLongTermMemory.query.filter_by(user_id=user_id)
        if memory_type:
            total = total.filter_by(memory_type=memory_type)
        total = total.count()

        return jsonify({
            'memories': [m.to_dict() for m in memories],
            'total': total,
            'limit': limit,
            'query': query_text,
            'type': memory_type
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to search memories: {e}")
        return jsonify({'error': 'Failed to search memories', 'details': str(e)}), 500


@agent_memories_bp.route('/prune', methods=['POST'])
def prune_memories():
    """
    Remove old, low-importance memories to manage storage.

    Query params:
        older_than_days: delete memories older than this many days (default 90)
        importance_threshold: delete memories with importance below this (0.0-1.0, default 0.1)

    Returns:
        { "deleted_count": int }
    """
    try:
        from auth import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        older_than_days = request.args.get('older_than_days', 90, type=int)
        importance_threshold = request.args.get('importance_threshold', 0.1, type=float)

        db_session = db.session
        deleted_count = forget_old_memories(
            db_session=db_session,
            user_id=user.id,
            older_than_days=older_than_days,
            importance_threshold=importance_threshold
        )
        db.session.commit()

        current_app.logger.info(f"Pruned {deleted_count} memories for user {user.id}")

        return jsonify({
            'deleted_count': deleted_count,
            'older_than_days': older_than_days,
            'importance_threshold': importance_threshold
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to prune memories: {e}")
        return jsonify({'error': 'Failed to prune memories', 'details': str(e)}), 500
