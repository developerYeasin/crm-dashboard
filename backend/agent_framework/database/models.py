"""
Database models for the autonomous agent framework.

These models extend the existing Max AI Agent database and track agent sessions,
steps, tool executions, and long-term memory.
"""

from datetime import datetime
from sqlalchemy.orm import validates
import json

# Import the existing db instance from extensions to avoid duplicate registration
# This must be imported at runtime after extensions is initialized
try:
    from extensions import db as existing_db
    db = existing_db
except ImportError:
    # Fallback for standalone usage (e.g., migration script)
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy()


# ========================================
# ENUMS (using plain strings for MySQL compatibility)
# ========================================

SESSION_STATUS = ('running', 'completed', 'failed', 'awaiting_approval')
APPROVAL_STATUS = ('pending', 'approved', 'denied', 'timeout', 'skipped')
RISK_LEVEL = ('low', 'medium', 'high')
MEMORY_TYPE = ('fact', 'preference', 'skill', 'error', 'success')


# ========================================
# MODELS
# ========================================

class AgentSession(db.Model):
    """Tracks a multi-step agent execution session"""
    __tablename__ = 'agent_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversations.id', ondelete='SET NULL'))
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='running', index=True)
    final_result = db.Column(db.Text, nullable=True)  # JSON: final answer, summary
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship('User', backref='agent_sessions')
    conversation = db.relationship('AIConversation', backref='agent_sessions')
    steps = db.relationship('AgentStep', back_populates='session', cascade='all, delete-orphan', order_by='AgentStep.step_number')
    tool_calls = db.relationship('ToolCall', back_populates='session', cascade='all, delete-orphan')
    approvals = db.relationship('ApprovalQueue', back_populates='session', cascade='all, delete-orphan')

    @validates('status')
    def validate_status(self, key, status):
        if status not in SESSION_STATUS:
            raise ValueError(f"Invalid status: {status}. Must be one of {SESSION_STATUS}")
        return status

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'conversation_id': self.conversation_id,
            'title': self.title,
            'status': self.status,
            'final_result': json.loads(self.final_result) if self.final_result else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'step_count': len(self.steps) if self.steps else 0
        }


class AgentStep(db.Model):
    """One Thought → Action → Observation cycle"""
    __tablename__ = 'agent_steps'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    step_number = db.Column(db.Integer, nullable=False, index=True)
    thought = db.Column(db.Text, nullable=True)  # Agent's reasoning
    action_name = db.Column(db.String(100), nullable=True)  # Tool name
    action_args = db.Column(db.JSON, nullable=True)  # Parameters passed to tool
    observation = db.Column(db.Text, nullable=True)  # Result of tool execution
    observation_error = db.Column(db.Text, nullable=True)  # If action failed
    execution_time_ms = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    session = db.relationship('AgentSession', back_populates='steps')
    tool_calls = db.relationship('ToolCall', back_populates='step', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('session_id', 'step_number', name='uniq_session_step'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'step_number': self.step_number,
            'thought': self.thought,
            'action': {
                'name': self.action_name,
                'args': self.action_args
            } if self.action_name else None,
            'observation': self.observation,
            'observation_error': self.observation_error,
            'execution_time_ms': self.execution_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ToolCall(db.Model):
    """Audit log of every tool invocation"""
    __tablename__ = 'tool_calls'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    step_id = db.Column(db.Integer, db.ForeignKey('agent_steps.id', ondelete='SET NULL'), nullable=True)
    tool_name = db.Column(db.String(100), nullable=False, index=True)
    arguments = db.Column(db.JSON, nullable=False)
    result = db.Column(db.JSON, nullable=True)  # Successful result (structured)
    result_text = db.Column(db.Text, nullable=True)  # Text representation for easy viewing
    error = db.Column(db.Text, nullable=True)
    requires_approval = db.Column(db.Boolean, default=False)
    approval_status = db.Column(db.String(20), nullable=True, default='pending', index=True)  # pending, approved, denied, skipped
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    executed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    session = db.relationship('AgentSession', back_populates='tool_calls')
    step = db.relationship('AgentStep', back_populates='tool_calls')
    approver = db.relationship('User', backref='approved_tool_calls')

    @validates('approval_status')
    def validate_approval_status(self, key, status):
        if status and status not in APPROVAL_STATUS:
            raise ValueError(f"Invalid approval_status: {status}. Must be one of {APPROVAL_STATUS}")
        return status

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'step_id': self.step_id,
            'tool_name': self.tool_name,
            'arguments': self.arguments,
            'result': self.result,
            'result_text': self.result_text,
            'error': self.error,
            'requires_approval': self.requires_approval,
            'approval_status': self.approval_status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ApprovalQueue(db.Model):
    """Queue of actions awaiting human approval"""
    __tablename__ = 'approval_queue'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    step_id = db.Column(db.Integer, db.ForeignKey('agent_steps.id', ondelete='CASCADE'), nullable=False, index=True)
    tool_name = db.Column(db.String(100), nullable=False)
    arguments = db.Column(db.JSON, nullable=False)
    risk_level = db.Column(db.String(10), nullable=False, default='medium')  # low, medium, high
    message = db.Column(db.Text, nullable=True)  # Explanation for user
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    requested_at = db.Column(db.DateTime, server_default=db.func.now())
    expires_at = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    responded_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    session = db.relationship('AgentSession', back_populates='approvals')
    step = db.relationship('AgentStep')
    responder = db.relationship('User', backref='approval_responses')

    __table_args__ = (
        db.Index('idx_pending', 'status', 'requested_at'),
    )

    @validates('status')
    def validate_status(self, key, status):
        if status not in APPROVAL_STATUS:
            raise ValueError(f"Invalid status: {status}. Must be one of {APPROVAL_STATUS}")
        return status

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'step_id': self.step_id,
            'tool_name': self.tool_name,
            'arguments': self.arguments,
            'risk_level': self.risk_level,
            'message': self.message,
            'status': self.status,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'responded_by': self.responded_by
        }


class AgentLongTermMemory(db.Model):
    """Long-term memories with embeddings for semantic search"""
    __tablename__ = 'agent_long_term_memory'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('agent_sessions.id', ondelete='SET NULL'), nullable=True)
    memory_type = db.Column(db.String(20), nullable=False, default='fact', index=True)  # fact, preference, skill, error, success
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.LargeBinary(length=2**24-1), nullable=True)  # FAISS binary embedding
    importance = db.Column(db.Float, default=1.0, index=True)  # 0.0 to 1.0
    access_count = db.Column(db.Integer, default=0, index=True)
    last_accessed = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)

    # Relationships
    user = db.relationship('User', backref='agent_memories')
    session = db.relationship('AgentSession', backref='memories')

    @validates('memory_type')
    def validate_memory_type(self, key, mtype):
        if mtype not in MEMORY_TYPE:
            raise ValueError(f"Invalid memory_type: {mtype}. Must be one of {MEMORY_TYPE}")
        return mtype

    @validates('importance')
    def validate_importance(self, key, value):
        if not 0.0 <= value <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        return value

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'memory_type': self.memory_type,
            'content': self.content[:200] + ('...' if len(self.content) > 200 else ''),
            'importance': self.importance,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AgentTemplate(db.Model):
    """Pre-defined agent personalities/skills"""
    __tablename__ = 'agent_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    system_prompt = db.Column(db.Text, nullable=False)
    allowed_tools = db.Column(db.JSON, nullable=False)  # List of tool names
    config = db.Column(db.JSON, default={})  # max_steps, temperature, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt[:200] + '...' if len(self.system_prompt) > 200 else self.system_prompt,
            'allowed_tools': self.allowed_tools,
            'config': self.config,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ========================================
# DATABASE INITIALIZATION
# ========================================

def init_agent_models(app):
    """Initialize agent models with Flask app"""
    # Note: db is already initialized in app.py, no need to call init_app again
    # db.init_app(app)  # Removed - duplicate initialization causes error

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    print("Agent framework database models initialized")


def drop_agent_models(app):
    """Drop all agent framework tables (use with caution)"""
    with app.app_context():
        AgentSession.__table__.drop(db.engine, checkfirst=True)
        AgentStep.__table__.drop(db.engine, checkfirst=True)
        ToolCall.__table__.drop(db.engine, checkfirst=True)
        ApprovalQueue.__table__.drop(db.engine, checkfirst=True)
        AgentLongTermMemory.__table__.drop(db.engine, checkfirst=True)
        AgentTemplate.__table__.drop(db.engine, checkfirst=True)
    print("Agent framework database models dropped")
