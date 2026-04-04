"""
Autonomous Agent Framework for Max AI Agent

Provides a reasoning agent that can execute multi-step tasks with:
- Thought generation via LLM
- Tool execution with approval workflow
- Long-term memory
- Real-time streaming updates
"""

from .agent_core import Agent, create_agent, AgentResult, Thought, Action, Observation
from .tools.registry import ToolRegistry, ToolDefinition, default_registry, ToolNotFoundError, ApprovalRequiredError, ApprovalDeniedError
# Import tools to register them with default_registry
from .tools import implementations  # noqa: F401 - triggers auto-registration
from .database.models import (
    db, AgentSession, AgentStep, ToolCall, ApprovalQueue,
    AgentLongTermMemory, AgentTemplate
)
from .database.handler import (
    create_agent_session, get_agent_session, list_agent_sessions,
    complete_agent_session, fail_agent_session,
    create_agent_step, get_agent_steps,
    create_tool_call, record_tool_result, record_tool_error, record_approval,
    get_tool_calls, get_pending_approvals,
    store_memory, search_memories, forget_old_memories,
    get_template, list_templates,
    init_db_handlers,
    update_agent_observation  # Added for agent_core
)

__all__ = [
    'Agent', 'create_agent', 'AgentResult', 'Thought', 'Action', 'Observation',
    'ToolRegistry', 'ToolDefinition', 'default_registry',
    'ToolNotFoundError', 'ApprovalRequiredError', 'ApprovalDeniedError',
    'db', 'AgentSession', 'AgentStep', 'ToolCall', 'ApprovalQueue',
    'AgentLongTermMemory', 'AgentTemplate',
    'create_agent_session', 'get_agent_session', 'list_agent_sessions',
    'complete_agent_session', 'fail_agent_session',
    'create_agent_step', 'update_agent_observation', 'get_agent_steps',
    'create_tool_call', 'record_tool_result', 'record_tool_error', 'record_approval',
    'get_tool_calls', 'get_pending_approvals',
    'store_memory', 'search_memories', 'forget_old_memories',
    'get_template', 'list_templates',
    'init_db_handlers'
]
