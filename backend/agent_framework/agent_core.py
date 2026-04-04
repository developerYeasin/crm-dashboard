"""
Agent Core - The reasoning engine for autonomous agent framework.

Implements the Thought → Action → Observation loop using LLM + Tools.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from flask import current_app, g
from sqlalchemy.exc import OperationalError

from .tools.registry import ToolRegistry, ToolNotFoundError, ApprovalRequiredError, ApprovalDeniedError
from .database.handler import (
    create_agent_session, get_agent_session, complete_agent_session, fail_agent_session,
    create_agent_step, update_agent_observation, get_agent_steps,
    create_tool_call, record_tool_result, record_tool_error, record_approval,
    get_pending_approvals, store_memory, search_memories,
    AgentSession, AgentStep
)
from ai_models.max_model1 import get_max_model


@dataclass
class Thought:
    """Represents an agent's reasoning"""
    content: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def to_dict(self):
        return {
            'content': self.content,
            'confidence': self.confidence,
            'metadata': self.metadata or {}
        }


@dataclass
class Action:
    """Represents a tool call decision"""
    tool_name: str
    arguments: Dict[str, Any]
    requires_approval: bool = False
    risk_level: str = "medium"
    metadata: Dict[str, Any] = None

    def to_dict(self):
        return {
            'name': self.tool_name,
            'arguments': self.arguments,
            'requires_approval': self.requires_approval,
            'risk_level': self.risk_level,
            'metadata': self.metadata or {}
        }


@dataclass
class Observation:
    """Result of an action execution"""
    content: str
    success: bool = True
    error: str = None
    metadata: Dict[str, Any] = None

    def to_dict(self):
        return {
            'content': self.content,
            'success': self.success,
            'error': self.error,
            'metadata': self.metadata or {}
        }


@dataclass
class AgentResult:
    """Final result of agent execution"""
    final_thought: Thought
    steps: List[Tuple[Thought, Action, Observation]]
    summary: str
    session_id: int
    status: str = 'completed'  # completed, failed, cancelled

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'status': self.status,
            'final_thought': self.final_thought.to_dict(),
            'summary': self.summary,
            'steps': [
                {
                    'thought': t.to_dict(),
                    'action': a.to_dict(),
                    'observation': o.to_dict()
                }
                for t, a, o in self.steps
            ]
        }


class Agent:
    """
    Autonomous agent with reasoning loop.

    The agent executes a Thought → Action → Observation cycle until:
    - Goal is achieved (determined by LLM)
    - Maximum steps reached
    - Fatal error occurs
    - User cancels
    """

    # System prompt for the reasoning agent
    REASONING_SYSTEM_PROMPT = """You are an autonomous AI assistant with access to tools.

Your job is to accomplish the user's goal by reasoning step-by-step and using available tools.

**Workflow:**
1. Analyze the goal
2. Think about what you need to do
3. Choose a tool and its parameters
4. Execute the tool
5. Observe the result
6. Repeat until goal is complete

**Response Format:**
You must respond with a JSON object containing:

{{
  "thought": "Your reasoning about what to do next",
  "action": {{
    "name": "tool_name",
    "arguments": {{"param1": "value1", ...}}
  }},
  "is_complete": false
}}

- If you need to use a tool, set "action" with tool name and arguments
- If the goal is complete, set "is_complete": true and provide final answer in "thought"
- If you cannot proceed, set "is_complete": true with an explanation

**Available Tools:**
{tool_list}

**Constraints:**
- Think carefully before choosing tools
- Consider the results of previous steps
- Some tools require human approval - if you attempt one without approval, you'll wait
- Maximum steps: {max_steps}
- Be concise in your thoughts
- Use tools strategically to gather information or perform actions

**Risk Levels:**
- Low: Safe, read-only operations
- Medium: Operations with some impact
- High: Potentially dangerous operations (file writes, shell commands)

Only use high-risk tools when absolutely necessary and with clear justification.
"""

    def __init__(
        self,
        session_id: str,
        user_id: int,
        db_session,
        tool_registry: ToolRegistry = None,
        max_steps: int = 30,
        stream_callback = None
    ):
        """
        Initialize the agent.

        Args:
            session_id: Unique session identifier
            user_id: User executing the agent
            db_session: SQLAlchemy database session
            tool_registry: Registry of available tools (uses default if None)
            max_steps: Maximum steps before forced termination
            stream_callback: Async callback for streaming events (session_id, event, data)
        """
        self.session_id = session_id
        self.user_id = user_id
        self.db = db_session
        self.max_steps = max_steps
        self.stream_callback = stream_callback

        self.tools = tool_registry or self._get_default_registry()
        self.step_count = 0
        self.start_time = time.time()
        self.memory_cache = []  # Recent memories for context

    def _get_default_registry(self) -> ToolRegistry:
        """Get the default tool registry (imports and registers tools)"""
        from .tools.implementations import default_registry
        return default_registry

    async def emit(self, event: str, data: Dict[str, Any]):
        """Emit streaming event to frontend if callback configured"""
        if self.stream_callback:
            try:
                await self.stream_callback(
                    session_id=self.session_id,
                    event=event,
                    data=data
                )
            except Exception as e:
                current_app.logger.error(f"Failed to emit event {event}: {e}")

    async def think(
        self,
        goal: str,
        history: List[Tuple[Thought, Action, Observation]]
    ) -> Thought:
        """
        Generate next thought using LLM.

        Args:
            goal: Original user goal
            history: Previous thought-action-observation cycles

        Returns:
            Thought object with reasoning
        """
        # Build context from history
        context = f"Goal: {goal}\n\n"

        if history:
            context += "Previous steps:\n"
            for idx, (thought, action, observation) in enumerate(history, 1):
                context += f"Step {idx}:\n"
                context += f"  Thought: {thought.content}\n"
                context += f"  Action: {action.tool_name}({json.dumps(action.arguments)})\n"
                context += f"  Observation: {observation.content[:500]}{'...' if len(observation.content) > 500 else ''}\n\n"

        # Get relevant long-term memories
        memories = search_memories(self.db, self.user_id, query_text=goal, limit=3)
        if memories:
            context += "Relevant past memories:\n"
            for mem in memories:
                context += f"- {mem.content[:200]}\n"
            context += "\n"

        # Simple system prompt; we'll use Anthropic's tool calling instead of JSON
        system_prompt = """You are an autonomous AI assistant. You have access to tools. Think step-by-step. If you need to use a tool, use it. If the goal is complete, provide a final answer."""

        # Call LLM (using MaxModel1 or direct API)
        try:
            # Use MaxModel1 if available (it will fall back to external)
            from ai_models.max_model1 import get_max_model
            max_model = get_max_model()

            # Use Anthropic API directly for proper response format
            from config import Config
            import os
            from anthropic import Anthropic

            client = Anthropic(
                api_key=Config.MAX_MODEL1_EXTERNAL_API_KEY or os.getenv('ANTHROPIC_AUTH_TOKEN'),
                base_url=Config.MAX_MODEL1_EXTERNAL_API_URL or os.getenv('ANTHROPIC_BASE_URL')
            )

            # Build tool schemas for Anthropic (convert from OpenAI format)
            tools_schema = None
            if self.tools.tools:
                tools_schema = []
                for tool in self.tools.tools.values():
                    tools_schema.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.parameters  # Anthropic uses input_schema, not parameters
                    })

            messages = [{"role": "user", "content": context}]

            response = client.messages.create(
                model=Config.MAX_MODEL1_EXTERNAL_MODEL or os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
                max_tokens=1000,
                system=system_prompt,
                messages=messages,
                tools=tools_schema
            )

            # Parse response: collect text and any tool_use
            thought_content = ""
            action = None

            print(f"DEBUG: LLM stop_reason={response.stop_reason}", file=__import__('sys').stderr)
            for block in response.content:
                print(f"DEBUG: block type={block.type}", file=__import__('sys').stderr)
                if block.type == "text":
                    if thought_content:
                        thought_content += "\n"
                    thought_content += block.text
                elif block.type == "tool_use":
                    current_app.logger.info(f"Tool use: {block.name}, input: {block.input}")
                    tool_name = block.name
                    tool_args = block.input

                    if not self.tools.has_tool(tool_name):
                        raise ToolNotFoundError(f"Unknown tool: {tool_name}")

                    tool_def = self.tools.get_tool(tool_name)
                    action = Action(
                        tool_name=tool_name,
                        arguments=tool_args,
                        requires_approval=tool_def.requires_approval,
                        risk_level=tool_def.risk_level
                    )

            if not thought_content:
                if action:
                    thought_content = f"I will use {action.tool_name}."
                else:
                    thought_content = "I need to think more."

            is_complete = response.stop_reason == "end_turn" and not action

            print(f"DEBUG: Returning Thought: action={action}, is_complete={is_complete}", file=__import__('sys').stderr)

            return Thought(
                content=thought_content,
                confidence=0.9,
                metadata={'is_complete': is_complete, 'action': action.to_dict() if action else None}
            )

        except json.JSONDecodeError as e:
            current_app.logger.error(f"Failed to parse LLM JSON response: {e}")
            return Thought(
                content=f"Error parsing LLM response: {str(e)}. Please try again.",
                confidence=0.0
            )
        except Exception as e:
            current_app.logger.error(f"Think error: {e}")
            return Thought(
                content=f"Error generating thought: {str(e)}",
                confidence=0.0
            )

    async def plan_action(self, thought: Thought, goal: str) -> Optional[Action]:
        """
        Extract action from thought.
        (In this implementation, action is extracted in think() directly)
        """
        # Action extraction happens in think()
        # This method can be expanded if we separate reasoning from action selection
        return None  # Not used in current design

    async def execute_action(self, action: Action, step_id: int) -> Observation:
        """
        Execute a tool action and record result.

        Args:
            action: The action to execute
            step_id: Database step ID for logging

        Returns:
            Observation with execution result
        """
        start_time = time.time()

        try:
            # Execute tool with approval check
            result = await self.tools.execute(
                name=action.tool_name,
                arguments=action.arguments,
                session_id=self.session_id,
                user_id=self.user_id,
                db_session=self.db
            )

            execution_time = int((time.time() - start_time) * 1000)

            # Format result
            if isinstance(result, dict):
                if result.get('success', True):
                    content = json.dumps(result, indent=2, ensure_ascii=False)
                    obs = Observation(content=content, success=True, metadata={'execution_time_ms': execution_time})
                else:
                    error_msg = result.get('error', 'Unknown error')
                    content = json.dumps(result, indent=2, ensure_ascii=False)
                    obs = Observation(content=content or error_msg, success=False, error=error_msg, metadata={'execution_time_ms': execution_time})
            else:
                # Convert non-dict results to string
                obs = Observation(content=str(result), success=True, metadata={'execution_time_ms': execution_time})

            return obs

        except ApprovalRequiredError as e:
            # This should have been caught earlier by registry
            return Observation(
                content="",
                success=False,
                error=f"Approval required but not granted: {str(e)}"
            )
        except ToolNotFoundError as e:
            return Observation(
                content="",
                success=False,
                error=f"Tool error: {str(e)}"
            )
        except Exception as e:
            current_app.logger.error(f"Action execution failed: {e}")
            return Observation(
                content="",
                success=False,
                error=f"Execution error: {str(e)}"
            )

    def should_terminate(self, thought: Thought) -> bool:
        """Determine if agent should stop based on current thought"""
        return thought.metadata and thought.metadata.get('is_complete', False)

    async def run_loop(self, goal: str) -> AgentResult:
        """
        Main reasoning loop: Thought → Action → Observation → repeat.

        Args:
            goal: User's goal to accomplish

        Returns:
            AgentResult with final state and step history
        """
        current_app.logger.info(f"Agent run_loop started: session={self.session_id}, goal={goal[:100]}")

        # Create database session record
        db_session_obj = create_agent_session(
            self.db,
            user_id=self.user_id,
            title=goal[:255],
            conversation_id=None
        )
        self.db.commit()
        session_id = db_session_obj.id
        current_app.logger.info(f"Created agent session {session_id}")

        thoughts = []
        actions = []
        observations = []

        try:
            # Initial thought
            thought = await self.think(goal, [])
            thoughts.append(thought)

            await self.emit('agent_thinking', {
                'step': 0,
                'thought': thought.content,
                'confidence': thought.confidence
            })

            while not self.should_terminate(thought) and self.step_count < self.max_steps:
                self.step_count += 1

                # If no action (complete), break
                if thought.metadata and thought.metadata.get('is_complete'):
                    break

                # Get action from thought (extracted during think)
                action = None
                if thought.metadata and 'action' in thought.metadata:
                    action_data = thought.metadata.get('action', {})
                    if isinstance(action_data, dict) and 'name' in action_data:
                        tool_name = action_data['name']
                        tool_args = action_data.get('arguments', {})

                        tool_def = self.tools.get_tool(tool_name)
                        action = Action(
                            tool_name=tool_name,
                            arguments=tool_args,
                            requires_approval=tool_def.requires_approval if tool_def else False,
                            risk_level=tool_def.risk_level if tool_def else 'medium'
                        )

                print(f"DEBUG: step {self.step_count}, action={action}", file=__import__('sys').stderr)

                if not action:
                    # Agent didn't propose an action but not complete - ask for clarification
                    thought = Thought(
                        content="I need to clarify what to do next. Let me analyze the situation.",
                        confidence=0.8
                    )
                    thoughts.append(thought)
                    continue

                # Emit action start
                await self.emit('agent_action', {
                    'step': self.step_count,
                    'thought': thought.content,
                    'action': action.to_dict()
                })

                # Create database step record
                db_step = create_agent_step(
                    self.db,
                    session_id=session_id,
                    step_number=self.step_count,
                    thought=thought.content,
                    action_name=action.tool_name,
                    action_args=action.arguments
                )
                self.db.flush()

                # Log tool call
                db_tool_call = create_tool_call(
                    self.db,
                    session_id=session_id,
                    step_id=db_step.id,
                    tool_name=action.tool_name,
                    arguments=action.arguments,
                    requires_approval=action.requires_approval
                )
                self.db.flush()

                # Check if approval required
                if action.requires_approval:
                    await self.emit('awaiting_approval', {
                        'step_id': db_step.id,
                        'tool_call_id': db_tool_call.id,
                        'tool_name': action.tool_name,
                        'arguments': action.arguments,
                        'risk_level': action.risk_level,
                        'message': f"Agent wants to use {action.tool_name}. Approve?"
                    })
                    # Wait for approval (blocking until approved/denied/timeout)
                    await self._wait_for_approval(db_tool_call.id)

                # Execute action
                print(f"DEBUG: Executing action {action.tool_name}", file=__import__('sys').stderr)
                observation = await self.execute_action(action, db_step.id)
                actions.append(action)
                observations.append(observation)
                print(f"DEBUG: Observation success={observation.success}, content={observation.content[:100]}", file=__import__('sys').stderr)

                # Record tool result in database
                if observation.success:
                    record_tool_result(
                        self.db,
                        tool_call_id=db_tool_call.id,
                        result=observation.to_dict(),
                        result_text=observation.content[:10000],
                        executed=True
                    )
                else:
                    record_tool_error(
                        self.db,
                        tool_call_id=db_tool_call.id,
                        error=observation.error or observation.content
                    )

                # Update step with observation
                update_agent_observation(
                    self.db,
                    step_id=db_step.id,
                    observation=observation.content[:10000],
                    error=observation.error,
                    execution_time_ms=observation.metadata.get('execution_time_ms')
                )
                self.db.commit()

                # Emit observation
                await self.emit('agent_observation', {
                    'step': self.step_count,
                    'observation': observation.content[:5000],
                    'success': observation.success,
                    'error': observation.error
                })

                # Store successful experiences in long-term memory (optional)
                if observation.success and observation.content:
                    store_memory(
                        self.db,
                        user_id=self.user_id,
                        session_id=session_id,
                        content=f"Goal: {goal[:100]}\nAction: {action.tool_name}\nResult: {observation.content[:500]}",
                        memory_type='success' if observation.success else 'error',
                        importance=0.5
                    )

                # Generate next thought
                thought = await self.think(goal, list(zip(thoughts, actions, observations)))
                thoughts.append(thought)

                await self.emit('agent_thinking', {
                    'step': self.step_count,
                    'thought': thought.content,
                    'confidence': thought.confidence
                })

            # Loop complete - generate summary
            summary = await self._generate_summary(goal, thoughts, actions, observations)
            final_status = 'completed' if self.step_count < self.max_steps else 'failed'

            if final_status == 'completed':
                complete_agent_session(self.db, session_id=session_id, final_result={
                    'summary': summary,
                    'steps': self.step_count,
                    'total_time_seconds': time.time() - self.start_time
                })
            else:
                fail_agent_session(self.db, session_id=session_id, error='Max steps exceeded')

            self.db.commit()

            result = AgentResult(
                final_thought=thought,
                steps=list(zip(thoughts, actions, observations)),
                summary=summary,
                session_id=session_id,
                status=final_status
            )

            await self.emit('agent_completed', result.to_dict())
            current_app.logger.info(f"Agent run_loop completed: session={session_id}, status={final_status}")

            return result

        except Exception as e:
            current_app.logger.error(f"Agent run_loop failed: {e}", exc_info=True)
            fail_agent_session(self.db, session_id=session_id, error=str(e))
            self.db.commit()

            result = AgentResult(
                final_thought=Thought(content=f"Fatal error: {str(e)}", confidence=0.0),
                steps=list(zip(thoughts, actions, observations)),
                summary=f"Agent failed: {str(e)}",
                session_id=session_id,
                status='failed'
            )
            await self.emit('agent_failed', result.to_dict())
            return result

    async def _wait_for_approval(self, tool_call_id: int, timeout_seconds: int = 600):
        """
        Wait for human approval of a tool call.

        This blocks the agent loop until:
        - Approval granted
        - Approval denied
        - Timeout occurs
        """
        import time
        start_time = time.time()
        poll_interval = 1  # Check every second

        while time.time() - start_time < timeout_seconds:
            # Check approval status
            self.db.refresh()  # Refresh session
            tool_call = ToolCall.query.get(tool_call_id)

            if tool_call.approval_status == 'approved':
                return True
            elif tool_call.approval_status == 'denied':
                raise ApprovalDeniedError(f"Tool call {tool_call_id} was denied")
            elif tool_call.approval_status == 'timeout':
                raise ApprovalDeniedError(f"Tool call {tool_call_id} timed out")

            await asyncio.sleep(poll_interval)

        raise ApprovalDeniedError(f"Tool call {tool_call_id} timed out after {timeout_seconds}s")

    async def _generate_summary(
        self,
        goal: str,
        thoughts: List[Thought],
        actions: List[Action],
        observations: List[Observation]
    ) -> str:
        """Generate a human-readable summary of the agent's execution"""
        lines = [
            f"Goal: {goal}",
            f"Steps taken: {len(actions)}",
            "",
            "Actions:"
        ]

        for idx, (action, obs) in enumerate(zip(actions, observations), 1):
            status = "✓" if obs.success else "✗"
            lines.append(f"{idx}. {status} {action.tool_name}")
            if not obs.success:
                lines.append(f"   Error: {obs.error}")

        return "\n".join(lines)


def create_agent(
    session_id: str,
    user_id: int,
    db_session,
    tool_registry: ToolRegistry = None,
    max_steps: int = 30,
    stream_callback = None
) -> Agent:
    """Factory function to create an agent instance"""
    return Agent(
        session_id=session_id,
        user_id=user_id,
        db_session=db_session,
        tool_registry=tool_registry,
        max_steps=max_steps,
        stream_callback=stream_callback
    )
