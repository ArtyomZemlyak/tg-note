"""
Mem-Agent MCP Tools

This module provides MCP tools specifically for the mem-agent,
allowing direct natural language interaction with the LLM-based memory agent.

These tools complement the standard memory storage tools by providing
more flexible, conversational access to the mem-agent's capabilities.

Tools:
- chat_with_memory: Full bidirectional interaction with mem-agent
- query_memory_agent: Read-only query to mem-agent  
- save_to_memory_agent: Explicit save instruction to mem-agent
- list_memory_structure_agent: View memory file structure

Note: These tools use the mem-agent directly (not through MCP server),
providing lower latency and more control over the agent's behavior.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..base_mcp_tool import BaseMCPTool

# Lazy import of mem-agent components
try:
    from .mem_agent_impl.agent import Agent
    MEM_AGENT_AVAILABLE = True
except ImportError as e:
    logging.warning(f"mem-agent not available: {e}")
    MEM_AGENT_AVAILABLE = False
    Agent = None


logger = logging.getLogger(__name__)


class ChatWithMemoryTool(BaseMCPTool):
    """
    Tool for conversational interaction with mem-agent
    
    This tool allows the main agent to have a full conversation with
    the mem-agent, which can read from and write to its Obsidian-style
    memory files.
    
    Use cases:
    - Complex memory operations requiring reasoning
    - Natural language memory queries
    - Intelligent information organization
    """
    
    def __init__(self):
        super().__init__()
        self._agent_instance: Optional[Agent] = None
    
    @property
    def name(self) -> str:
        return "chat_with_memory_agent"
    
    @property
    def description(self) -> str:
        return (
            "Chat with the LLM-based memory agent. The agent can intelligently read from and write to "
            "its memory (Obsidian-style markdown files) to remember information across conversations. "
            "Use this for complex memory operations that require reasoning and organization."
        )
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Your message or instruction for the memory agent"
                },
                "use_vllm": {
                    "type": "boolean",
                    "description": "Whether to use vLLM backend (default: True)",
                    "default": True
                }
            },
            "required": ["message"]
        }
    
    @property
    def mcp_server_config(self):
        # Not used - this tool doesn't use MCP server
        return None
    
    @property
    def mcp_tool_name(self) -> str:
        # Not used
        return "chat_with_memory"
    
    def _get_or_create_agent(
        self, 
        memory_path: str, 
        use_vllm: bool = True
    ) -> Agent:
        """Get or create agent instance for the given memory path"""
        if not MEM_AGENT_AVAILABLE:
            raise ImportError("mem-agent is not available")
        
        # For simplicity, create a new agent each time
        # In production, you might want to cache agents per memory path
        return Agent(
            memory_path=memory_path,
            use_vllm=use_vllm,
            model=None,  # Use default
            predetermined_memory_path=False
        )
    
    async def execute(self, params: Dict[str, Any], context: 'ToolContext') -> Dict[str, Any]:
        """
        Execute chat with mem-agent
        
        Args:
            params: Tool parameters (message, use_vllm)
            context: Tool execution context (contains kb_root_path)
            
        Returns:
            Agent's response
        """
        if not MEM_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "mem-agent is not available. Please install mem-agent dependencies."
            }
        
        try:
            message = params.get("message", "")
            use_vllm = params.get("use_vllm", True)
            
            if not message:
                return {
                    "success": False,
                    "error": "Message is required"
                }
            
            # Get memory path from context
            if hasattr(context, 'kb_root_path') and context.kb_root_path:
                memory_path = str(Path(context.kb_root_path) / "memory")
            else:
                memory_path = "data/memory/default"
            
            logger.info(f"Chatting with mem-agent at {memory_path}")
            
            # Create agent and chat
            agent = self._get_or_create_agent(memory_path, use_vllm)
            response = agent.chat(message)
            
            return {
                "success": True,
                "reply": response.reply or "No reply from agent",
                "thoughts": response.thoughts,
                "python_executed": bool(response.python_block),
                "message": f"Successfully communicated with memory agent"
            }
        
        except Exception as e:
            logger.error(f"Error chatting with mem-agent: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


class QueryMemoryAgentTool(BaseMCPTool):
    """
    Tool for read-only queries to mem-agent
    
    Similar to ChatWithMemoryTool but explicitly instructs the agent
    to only retrieve information, not modify memory.
    """
    
    @property
    def name(self) -> str:
        return "query_memory_agent"
    
    @property
    def description(self) -> str:
        return (
            "Query the memory agent to retrieve information without modifying memory. "
            "This is a read-only operation that searches through the agent's Obsidian-style "
            "memory files to find relevant information."
        )
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Your query to search for in memory"
                }
            },
            "required": ["query"]
        }
    
    @property
    def mcp_server_config(self):
        return None
    
    @property
    def mcp_tool_name(self) -> str:
        return "query_memory"
    
    async def execute(self, params: Dict[str, Any], context: 'ToolContext') -> Dict[str, Any]:
        """Execute read-only query to mem-agent"""
        if not MEM_AGENT_AVAILABLE:
            return {
                "success": False,
                "error": "mem-agent is not available"
            }
        
        try:
            query = params.get("query", "")
            if not query:
                return {
                    "success": False,
                    "error": "Query is required"
                }
            
            # Prepend instruction for read-only operation
            query_message = (
                f"Please search your memory and tell me: {query}\n\n"
                "IMPORTANT: Only retrieve information, do not add anything new to memory."
            )
            
            # Use ChatWithMemoryTool with modified message
            chat_tool = ChatWithMemoryTool()
            return await chat_tool.execute(
                {"message": query_message, "use_vllm": True},
                context
            )
        
        except Exception as e:
            logger.error(f"Error querying mem-agent: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Export all mem-agent tools
ALL_TOOLS = [
    ChatWithMemoryTool(),
    QueryMemoryAgentTool(),
]
