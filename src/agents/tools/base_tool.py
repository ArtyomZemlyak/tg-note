"""
Base Tool class for autonomous agent tools.

Each tool encapsulates its own metadata (name, description, schema) and execution logic.
This ensures each tool is self-contained and follows single responsibility principle.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from loguru import logger


@dataclass
class ToolSpec:
    """Tool specification with metadata for OpenAI function calling"""

    name: str
    description: str
    parameters_schema: Dict[str, Any]

    def to_openai_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


class BaseTool(ABC):
    """
    Base class for all autonomous agent tools.

    Each tool must define:
    - name: Tool identifier
    - description: What the tool does
    - parameters_schema: JSON schema for parameters
    - execute: The actual tool logic

    This ensures tools are self-contained and encapsulate both
    their metadata and implementation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (unique identifier)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description (for LLM to understand when to use it)"""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON schema for tool parameters"""
        pass

    @abstractmethod
    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute the tool with given parameters and context

        Args:
            params: Tool parameters (validated against schema)
            context: Execution context with dependencies

        Returns:
            Dict with execution result (should include 'success' key)
        """
        pass

    def get_spec(self) -> ToolSpec:
        """Get tool specification for registration"""
        return ToolSpec(
            name=self.name, description=self.description, parameters_schema=self.parameters_schema
        )

    def to_openai_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return self.get_spec().to_openai_function()

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"


@dataclass
class ToolContext:
    """
    Execution context passed to tools.

    Contains all dependencies tools might need:
    - kb_root_path: Knowledge base root directory
    - base_agent_class: BaseAgent class for utility methods
    - github_token: Optional GitHub API token
    - enable_shell: Whether shell commands are allowed
    - vector_search_manager: Optional vector search manager
    - get_current_plan: Callback to get current TODO plan
    - set_current_plan: Callback to set current TODO plan
    - user_id: Optional user ID for per-user resources (like MCP servers)
    """

    kb_root_path: Any  # Path
    base_agent_class: Any
    github_token: Optional[str] = None
    enable_shell: bool = False
    vector_search_manager: Optional[Any] = None
    get_current_plan: Optional[Any] = None
    set_current_plan: Optional[Any] = None
    user_id: Optional[int] = None
