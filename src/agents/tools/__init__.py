"""
Tools module for autonomous agent.

This module contains all tools organized by category. Each tool is self-contained
with its own metadata (name, description, schema) and implementation logic.

Tool architecture:
- BaseTool: Base class for all tools
- ToolContext: Execution context with dependencies
- ToolManager: Registry and executor for tools
- Tool modules: Each module contains related tools

Tools are auto-discovered by the registry and registered based on configuration.
This ensures clean separation of concerns and single responsibility principle.
"""

from .base_tool import BaseTool, ToolContext, ToolSpec
from .registry import ToolManager, build_default_tool_manager

# Export base classes and registry
__all__ = [
    "BaseTool",
    "ToolContext", 
    "ToolSpec",
    "ToolManager",
    "build_default_tool_manager",
]
