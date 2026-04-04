"""
Tool Registry System for Autonomous Agent Framework

Provides a decorator-based registration system for tools that the agent can use.
Tools are registered with descriptions that the LLM uses to decide when to use them.
"""

from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, asdict
import json


@dataclass
class ToolDefinition:
    """Definition of a tool that can be used by the agent"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    func: Callable
    requires_approval: bool = False
    risk_level: str = "medium"  # low, medium, high


class ToolRegistry:
    """
    Registry for agent tools using decorator pattern.

    Example:
        registry = ToolRegistry()

        @registry.register(
            name="execute_shell",
            description="Execute a shell command",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run"}
                },
                "required": ["command"]
            },
            requires_approval=True,
            risk_level="high"
        )
        async def execute_shell(command: str):
            # Implementation
            pass
    """

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        requires_approval: bool = False,
        risk_level: str = "medium"
    ) -> Callable:
        """
        Decorator to register a function as an agent tool.

        Args:
            name: Unique tool name (used by LLM to reference tool)
            description: Human-readable description of what the tool does
            parameters: JSON Schema for the tool's parameters
            requires_approval: If True, human approval required before execution
            risk_level: Risk classification ("low", "medium", "high")

        Returns:
            Decorator function that registers the decorated function
        """
        def decorator(func: Callable) -> Callable:
            if name in self.tools:
                raise ValueError(f"Tool '{name}' is already registered")

            self.tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                func=func,
                requires_approval=requires_approval,
                risk_level=risk_level
            )
            return func

        return decorator

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools (for LLM schema)"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
                "requires_approval": tool.requires_approval,
                "risk_level": tool.risk_level
            }
            for tool in self.tools.values()
        ]

    def get_schema_for_llm(self) -> List[Dict[str, Any]]:
        """
        Get tool schemas in OpenAI/Anthropic function calling format.

        Returns:
            List of tool schema dicts with name, description, and parameters
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self.tools.values()
        ]

    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        session_id: str,
        user_id: int,
        db_session=None
    ) -> Any:
        """
        Execute a tool by name with approval check.

        Args:
            name: Tool name
            arguments: Arguments to pass to the tool
            session_id: Agent session ID (for logging)
            user_id: User executing the tool
            db_session: Optional database session for approval checks

        Returns:
            Tool execution result

        Raises:
            ToolNotFoundError: If tool not registered
            ApprovalRequiredError: If tool requires approval but not approved
            ApprovalDeniedError: If tool was explicitly denied
        """
        tool = self.get_tool(name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{name}' not found in registry")

        # Check approval if required
        if tool.requires_approval and db_session:
            from agent_framework.database.handler import check_approval_status
            approval = check_approval_status(db_session, session_id, name)

            if not approval:
                raise ApprovalRequiredError(
                    f"Tool '{name}' requires approval before execution"
                )
            elif approval.status == 'denied':
                raise ApprovalDeniedError(
                    f"Tool '{name}' was denied by user"
                )
            # If approved, continue execution

        # Execute the tool
        try:
            result = await tool.func(**arguments)
            return result
        except Exception as e:
            # Log error but re-raise
            print(f"Tool execution error for {name}: {e}")
            raise

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered"""
        return name in self.tools

    def get_approval_required_tools(self) -> List[str]:
        """Get list of tool names that require approval"""
        return [name for name, tool in self.tools.items() if tool.requires_approval]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to dict (for debugging)"""
        return {
            name: asdict(tool)
            for name, tool in self.tools.items()
        }


class ToolNotFoundError(Exception):
    """Raised when requested tool is not found in registry"""
    pass


class ApprovalRequiredError(Exception):
    """Raised when tool requires approval but not yet approved"""
    pass


class ApprovalDeniedError(Exception):
    """Raised when tool execution was denied by user"""
    pass


# Global registry instance (can be imported and extended)
default_registry = ToolRegistry()
