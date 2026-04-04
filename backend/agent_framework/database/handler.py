"""
Database handler for agent framework CRUD operations.

Provides helper functions for managing agent sessions, steps, tool calls,
approval queue, and long-term memory.
"""

from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from .models import (
    db, AgentSession, AgentStep, ToolCall, ApprovalQueue,
    AgentLongTermMemory, AgentTemplate
)


# ========================================
# AGENT SESSION OPERATIONS
# ========================================

def create_agent_session(
    db_session,
    user_id: int,
    title: str,
    conversation_id: int = None,
    template_id: int = None
) -> AgentSession:
    """
    Create a new agent session.

    Args:
        db_session: SQLAlchemy database session
        user_id: User who owns the session
        title: Session title/goal
        conversation_id: Optional link to existing AI conversation
        template_id: Optional agent template to use

    Returns:
        AgentSession object (not yet committed)
    """
    session = AgentSession(
        user_id=user_id,
        conversation_id=conversation_id,
        title=title[:255],  # Safety truncate
        status='running'
    )
    db_session.add(session)
    db_session.flush()  # Get ID without commit
    return session


def get_agent_session(db_session, session_id: int, user_id: int = None) -> AgentSession:
    """Fetch an agent session by ID, optionally filtering by user"""
    query = AgentSession.query.filter_by(id=session_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    return query.first()


def list_agent_sessions(
    db_session,
    user_id: int = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
) -> list:
    """List agent sessions with optional filters"""
    query = AgentSession.query

    if user_id:
        query = query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(status=status)

    query = query.order_by(AgentSession.created_at.desc())
    query = query.limit(limit).offset(offset)

    return query.all()


def complete_agent_session(db_session, session_id: int, final_result: dict):
    """Mark session as completed with final result"""
    import json
    session = get_agent_session(db_session, session_id)
    if session:
        session.status = 'completed'
        session.completed_at = datetime.utcnow()
        session.final_result = json.dumps(final_result, ensure_ascii=False)
    return session


def fail_agent_session(db_session, session_id: int, error: str):
    """Mark session as failed with error message"""
    import json
    session = get_agent_session(db_session, session_id)
    if session:
        session.status = 'failed'
        session.completed_at = datetime.utcnow()
        session.final_result = json.dumps({'error': error}, ensure_ascii=False)
    return session


# ========================================
# AGENT STEP OPERATIONS
# ========================================

def create_agent_step(
    db_session,
    session_id: int,
    step_number: int,
    thought: str = None,
    action_name: str = None,
    action_args: dict = None
) -> AgentStep:
    """Create a new step in an agent session"""
    step = AgentStep(
        session_id=session_id,
        step_number=step_number,
        thought=thought,
        action_name=action_name,
        action_args=action_args
    )
    db_session.add(step)
    db_session.flush()
    return step


def update_agent_observation(
    db_session,
    step_id: int,
    observation: str = None,
    error: str = None,
    execution_time_ms: int = None
) -> AgentStep:
    """Update step with observation/result (alias for compatibility)"""
    """Update step with observation/result"""
    step = AgentStep.query.get(step_id)
    if step:
        if observation is not None:
            step.observation = observation
        if error is not None:
            step.observation_error = error
        if execution_time_ms is not None:
            step.execution_time_ms = execution_time_ms
    return step


def get_agent_steps(db_session, session_id: int) -> list:
    """Get all steps for a session, ordered"""
    return AgentStep.query.filter_by(session_id=session_id)\
        .order_by(AgentStep.step_number)\
        .all()


# ========================================
# TOOL CALL OPERATIONS
# ========================================

def create_tool_call(
    db_session,
    session_id: int,
    step_id: int = None,
    tool_name: str = None,
    arguments: dict = None,
    requires_approval: bool = False
) -> ToolCall:
    """Log a tool call invocation"""
    call = ToolCall(
        session_id=session_id,
        step_id=step_id,
        tool_name=tool_name,
        arguments=arguments,
        requires_approval=requires_approval,
        approval_status='pending' if requires_approval else None
    )
    db_session.add(call)
    db_session.flush()
    return call


def record_tool_result(
    db_session,
    tool_call_id: int,
    result: dict = None,
    result_text: str = None,
    executed: bool = True
) -> ToolCall:
    """Record successful tool execution result"""
    call = ToolCall.query.get(tool_call_id)
    if call:
        if result is not None:
            call.result = result
        if result_text is not None:
            call.result_text = result_text
        if executed:
            call.executed_at = datetime.utcnow()
            call.approval_status = 'approved' if call.requires_approval else None
    return call


def record_tool_error(
    db_session,
    tool_call_id: int,
    error: str
) -> ToolCall:
    """Record tool execution error"""
    call = ToolCall.query.get(tool_call_id)
    if call:
        call.error = error
        call.executed_at = datetime.utcnow()
        call.approval_status = 'skipped'
    return call


def record_approval(
    db_session,
    tool_call_id: int,
    approved: bool,
    approved_by: int
) -> ToolCall:
    """Record user approval decision"""
    call = ToolCall.query.get(tool_call_id)
    if call:
        call.approval_status = 'approved' if approved else 'denied'
        call.approved_by = approved_by
        call.approved_at = datetime.utcnow()
    return call


def get_tool_calls(
    db_session,
    session_id: int = None,
    tool_name: str = None,
    approval_status: str = None,
    limit: int = 100
) -> list:
    """Query tool calls with filters"""
    query = ToolCall.query

    if session_id:
        query = query.filter_by(session_id=session_id)
    if tool_name:
        query = query.filter_by(tool_name=tool_name)
    if approval_status:
        query = query.filter_by(approval_status=approval_status)

    query = query.order_by(ToolCall.created_at.desc()).limit(limit)
    return query.all()


# ========================================
# APPROVAL QUEUE OPERATIONS
# ========================================

def create_approval_request(
    db_session,
    session_id: int,
    step_id: int,
    tool_name: str,
    arguments: dict,
    risk_level: str = 'medium',
    message: str = None,
    timeout_minutes: int = 10
) -> ApprovalQueue:
    """Create an approval request in the queue"""
    expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)

    approval = ApprovalQueue(
        session_id=session_id,
        step_id=step_id,
        tool_name=tool_name,
        arguments=arguments,
        risk_level=risk_level,
        message=message,
        status='pending',
        expires_at=expires_at
    )
    db_session.add(approval)
    db_session.flush()
    return approval


def check_approval_status(db_session, session_id: int, tool_name: str) -> ApprovalQueue:
    """
    Check if a tool execution has been approved.

    Returns:
        ApprovalQueue object if approved/denied, None if still pending or no request exists
    """
    # Look for most recent approval for this session+tool
    approval = ApprovalQueue.query.filter_by(
        session_id=session_id,
        tool_name=tool_name,
        status='approved'
    ).order_by(ApprovalQueue.responded_at.desc()).first()

    # Check for denials (should override approvals if more recent)
    denial = ApprovalQueue.query.filter_by(
        session_id=session_id,
        tool_name=tool_name,
        status='denied'
    ).order_by(ApprovalQueue.responded_at.desc()).first()

    if denial and (not approval or denial.responded_at > approval.responded_at):
        return denial

    return approval


def respond_to_approval(
    db_session,
    approval_id: int,
    approved: bool,
    responded_by: int,
    comment: str = None
) -> ApprovalQueue:
    """Record user's approval/deny decision"""
    approval = ApprovalQueue.query.get(approval_id)
    if approval and approval.status == 'pending':
        approval.status = 'approved' if approved else 'denied'
        approval.responded_at = datetime.utcnow()
        approval.responded_by = responded_by
        if comment:
            approval.message = (approval.message or '') + f"\n\nUser comment: {comment}"

        # Also update associated ToolCall
        if approved:
            tool_call = ToolCall.query.filter_by(
                session_id=approval.session_id,
                tool_name=approval.tool_name
            ).order_by(ToolCall.created_at.desc()).first()
            if tool_call:
                tool_call.approval_status = 'approved'
                tool_call.approved_by = responded_by
                tool_call.approved_at = datetime.utcnow()

    return approval


def get_pending_approvals(db_session, session_id: int = None, limit: int = 50) -> list:
    """Get pending approval requests"""
    query = ApprovalQueue.query.filter_by(status='pending')

    if session_id:
        query = query.filter_by(session_id=session_id)

    query = query.order_by(ApprovalQueue.requested_at.desc()).limit(limit)
    return query.all()


# ========================================
# LONG-TERM MEMORY OPERATIONS
# ========================================

def store_memory(
    db_session,
    user_id: int,
    content: str,
    memory_type: str = 'fact',
    session_id: int = None,
    importance: float = 1.0,
    embedding: bytes = None
) -> AgentLongTermMemory:
    """Store a memory in long-term memory"""
    memory = AgentLongTermMemory(
        user_id=user_id,
        session_id=session_id,
        memory_type=memory_type,
        content=content,
        embedding=embedding,
        importance=min(max(importance, 0.0), 1.0)  # Clamp to [0, 1]
    )
    db_session.add(memory)
    db_session.flush()
    return memory


def search_memories(
    db_session,
    user_id: int,
    query_embedding: bytes = None,
    query_text: str = None,
    memory_type: str = None,
    limit: int = 10
) -> list:
    """
    Search long-term memories by embedding similarity or text matching.
    Note: Full embedding search requires FAISS integration.
    For now, simple text search.
    """
    query = AgentLongTermMemory.query.filter_by(user_id=user_id)

    if memory_type:
        query = query.filter_by(memory_type=memory_type)

    # Basic text search as fallback
    if query_text:
        # Simple LIKE match (should be replaced with full-text or embedding search)
        like_pattern = f"%{query_text.lower()}%"
        from sqlalchemy import or_
        query = query.filter(
            or_(
                AgentLongTermMemory.content.like(like_pattern),
                AgentLongTermMemory.memory_type.like(like_pattern)
            )
        )

    # Order by importance and recency (MySQL doesn't support nullsfirst/nullslast)
    # NULL last_accessed will appear last in DESC order (which is desired - never accessed = old)
    query = query.order_by(
        AgentLongTermMemory.importance.desc(),
        AgentLongTermMemory.last_accessed.desc()
    ).limit(limit)

    memories = query.all()

    # Update access stats
    for mem in memories:
        mem.access_count += 1
        mem.last_accessed = datetime.utcnow()

    db_session.commit()
    return memories


def forget_old_memories(
    db_session,
    user_id: int,
    keep_count: int = 1000,
    importance_threshold: float = 0.2
) -> int:
    """
    Forget old, low-importance memories to prevent unbounded growth.
    Keeps the top `keep_count` most important memories + all memories with importance >= threshold.
    """
    # Count memories
    total = AgentLongTermMemory.query.filter_by(user_id=user_id).count()

    if total <= keep_count:
        return 0  # Nothing to delete

    # Find memories to delete
    to_keep_subq = db.session.query(AgentLongTermMemory.id)\
        .filter_by(user_id=user_id)\
        .filter(
            (AgentLongTermMemory.importance >= importance_threshold) |
            (AgentLongTermMemory.id.in_(
                db.session.query(AgentLongTermMemory.id)
                .filter_by(user_id=user_id)
                .order_by(
                    AgentLongTermMemory.importance.desc(),
                    AgentLongTermMemory.created_at.desc()
                )
                .limit(keep_count)
            ))
        ).subquery()

    deleted = db.session.query(AgentLongTermMemory)\
        .filter_by(user_id=user_id)\
        .filter(~AgentLongTermMemory.id.in_(to_keep_subq))\
        .delete(synchronize_session=False)

    db.session.commit()
    return deleted


# ========================================
# AGENT TEMPLATE OPERATIONS
# ========================================

def get_template(db_session, template_id: int) -> AgentTemplate:
    """Get agent template by ID"""
    return AgentTemplate.query.get(template_id)


def list_templates(db_session, active_only: bool = True) -> list:
    """List all agent templates"""
    query = AgentTemplate.query
    if active_only:
        query = query.filter_by(is_active=True)
    return query.order_by(AgentTemplate.name).all()


# ========================================
# INITIALIZATION
# ========================================

def init_db_handlers(app):
    """Initialize database handlers with Flask app context"""
    from .models import init_agent_models
    init_agent_models(app)
    print("Agent database handlers initialized")

# Alias for backward compatibility - some code might expect this name
update_agent_step_observation = update_agent_observation
