"""
Tool registry and manager for autonomous agents.

The registry auto-discovers tools from tool modules and provides:
- Unified Tool interface (via BaseTool)
- Contextual dependency injection (via ToolContext)
- OpenAI-compatible tool schemas
- Single execution entrypoint

Each tool is self-contained in its own module with metadata and implementation.
The registry simply collects and registers them.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from loguru import logger

from .base_tool import BaseTool, ToolContext


class ToolManager:
    """
    Tool manager for autonomous agents.
    
    Manages tool registration, discovery, and execution.
    Tools are auto-discovered from tool modules and registered with their metadata.
    """
    
    def __init__(self, context: ToolContext):
        """
        Initialize tool manager with execution context
        
        Args:
            context: Tool execution context with dependencies
        """
        self._context = context
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a single tool
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        logger.debug(f"[ToolManager] Registered tool: {tool.name}")
    
    def register_many(self, tools: List[BaseTool]) -> None:
        """
        Register multiple tools at once
        
        Args:
            tools: List of tool instances to register
        """
        for tool in tools:
            self.register(tool)
    
    def has(self, name: str) -> bool:
        """
        Check if a tool is registered
        
        Args:
            name: Tool name
            
        Returns:
            True if tool is registered
        """
        return name in self._tools
    
    def names(self) -> List[str]:
        """
        Get list of registered tool names
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def build_llm_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Build OpenAI-compatible function calling schemas for all registered tools
        
        Returns:
            List of OpenAI function schemas
        """
        return [tool.to_openai_function() for tool in self._tools.values()]
    
    async def execute(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with given parameters
        
        Args:
            name: Tool name
            params: Tool parameters
            
        Returns:
            Dict with execution result
        """
        if name not in self._tools:
            return {"success": False, "error": f"Tool not found: {name}"}
        
        return await self._tools[name].execute(params, self._context)


def build_default_tool_manager(
    kb_root_path: Any,  # Path
    base_agent_class: Any,
    *,
    enable_web_search: bool = True,
    enable_git: bool = True,
    enable_github: bool = True,
    enable_shell: bool = False,
    enable_file_management: bool = True,
    enable_folder_management: bool = True,
    enable_vector_search: bool = False,
    enable_mcp: bool = False,
    enable_mcp_memory: bool = False,
    github_token: Optional[str] = None,
    vector_search_manager: Optional[Any] = None,
    get_current_plan: Optional[Any] = None,
    set_current_plan: Optional[Any] = None,
) -> ToolManager:
    """
    Create a ToolManager with the default toolset based on flags.
    
    Auto-discovers tools from tool modules and registers them based on configuration.
    
    Args:
        kb_root_path: Root path of knowledge base
        base_agent_class: BaseAgent class for utility methods
        enable_web_search: Enable web search tool
        enable_git: Enable git command tool
        enable_github: Enable GitHub API tool
        enable_shell: Enable shell command tool (security risk)
        enable_file_management: Enable file management tools
        enable_folder_management: Enable folder management tools
        enable_vector_search: Enable vector search tools
        enable_mcp: Enable MCP (Model Context Protocol) support
        enable_mcp_memory: Enable MCP memory agent tool
        github_token: Optional GitHub API token
        vector_search_manager: Optional vector search manager
        get_current_plan: Callback to get current TODO plan
        set_current_plan: Callback to set current TODO plan
        
    Returns:
        Configured ToolManager instance
    """
    # Create execution context
    ctx = ToolContext(
        kb_root_path=kb_root_path,
        base_agent_class=base_agent_class,
        github_token=github_token,
        enable_shell=enable_shell,
        vector_search_manager=vector_search_manager,
        get_current_plan=get_current_plan,
        set_current_plan=set_current_plan,
    )
    
    manager = ToolManager(context=ctx)
    
    # Auto-discover and register tools from modules
    # Each module exports ALL_TOOLS list with tool instances
    
    # Planning tools (always enabled)
    from . import planning_tools
    manager.register_many(planning_tools.ALL_TOOLS)
    
    # KB reading tools (always enabled)
    from . import kb_reading_tools
    manager.register_many(kb_reading_tools.ALL_TOOLS)
    
    # File management tools
    if enable_file_management:
        from . import file_tools
        manager.register_many(file_tools.ALL_TOOLS)
    
    # Folder management tools
    if enable_folder_management:
        from . import folder_tools
        manager.register_many(folder_tools.ALL_TOOLS)
    
    # Web search tools
    if enable_web_search:
        from . import web_tools
        manager.register_many(web_tools.ALL_TOOLS)
    
    # Git tools
    if enable_git:
        from . import git_tools
        manager.register_many(git_tools.ALL_TOOLS)
    
    # GitHub tools
    if enable_github:
        from . import github_tools
        manager.register_many(github_tools.ALL_TOOLS)
    
    # Shell tools (disabled by default for security)
    if enable_shell:
        from . import shell_tools
        manager.register_many(shell_tools.ALL_TOOLS)
    
    # Vector search tools
    if enable_vector_search:
        from . import vector_search_tools
        manager.register_many(vector_search_tools.ALL_TOOLS)
    
    # MCP tools
    if enable_mcp and enable_mcp_memory:
        try:
            from ..mcp import memory_agent_tool
            # Enable MCP tools before registering
            for tool in memory_agent_tool.ALL_TOOLS:
                tool.enable()
            manager.register_many(memory_agent_tool.ALL_TOOLS)
            logger.info("[ToolManager] MCP memory agent tools enabled")
        except ImportError as e:
            logger.warning(f"[ToolManager] Failed to import MCP tools: {e}")
        except Exception as e:
            logger.error(f"[ToolManager] Failed to initialize MCP tools: {e}")
    
    logger.info(f"[ToolManager] Initialized with {len(manager.names())} tools")
    
    return manager
