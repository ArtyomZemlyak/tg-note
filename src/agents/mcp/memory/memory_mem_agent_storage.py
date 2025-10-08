"""
Mem-Agent Storage Implementation

This module provides a memory storage implementation that uses the mem-agent
(LLM-based agent) for intelligent memory management with Obsidian-style markdown files.

Key Features:
- LLM-powered memory operations (intelligent organization)
- Obsidian-style markdown with wiki-links
- Sandboxed code execution for file operations
- Natural language interface for memory management

Architecture:
- MemAgentStorage: Adapter that implements BaseMemoryStorage interface
- Uses mem_agent_impl.Agent internally for LLM-based operations
- Converts structured calls to natural language queries for the agent
- Follows SOLID principles (adapter pattern, minimal changes to original code)

Usage:
    storage = MemAgentStorage(
        data_dir=Path("data/memory"),
        use_vllm=True,
        model="driaforall/mem-agent"
    )
    
    # Store information
    result = storage.store(
        content="Important information about user preferences",
        category="user",
        tags=["preferences"]
    )
    
    # Retrieve information
    results = storage.retrieve(query="user preferences", limit=5)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .memory_base import BaseMemoryStorage

# Import mem-agent components (lazy import to avoid circular dependencies)
try:
    from .mem_agent_impl.agent import Agent
    from .mem_agent_impl.schemas import AgentResponse
    MEM_AGENT_AVAILABLE = True
except ImportError as e:
    logging.warning(f"mem-agent components not available: {e}")
    MEM_AGENT_AVAILABLE = False
    Agent = None
    AgentResponse = None


logger = logging.getLogger(__name__)


class MemAgentStorage(BaseMemoryStorage):
    """
    Memory storage implementation using mem-agent (LLM-based agent)
    
    This class adapts the mem-agent to the BaseMemoryStorage interface,
    allowing it to be used interchangeably with other storage implementations.
    
    The mem-agent uses:
    - Obsidian-style markdown files for memory storage
    - LLM for intelligent memory organization and retrieval
    - Sandboxed Python execution for file operations
    - Natural language interface
    
    Implementation Note:
    This is an adapter pattern - we minimize changes to the original mem-agent code
    and instead wrap it to fit our SOLID architecture.
    """
    
    def __init__(
        self,
        data_dir: Path,
        use_vllm: bool = True,
        model: Optional[str] = None,
        max_tool_turns: int = 20,
        **kwargs
    ):
        """
        Initialize MemAgentStorage
        
        Args:
            data_dir: Directory for memory storage
            use_vllm: Whether to use vLLM backend (default True)
            model: Model name (default: driaforall/mem-agent)
            max_tool_turns: Maximum tool execution turns
            **kwargs: Additional arguments (for compatibility)
        """
        if not MEM_AGENT_AVAILABLE:
            raise ImportError(
                "mem-agent components are not available. "
                "Please ensure mem_agent_impl is properly installed."
            )
        
        super().__init__(data_dir)
        
        # Initialize the mem-agent
        # The agent will use data_dir as its memory path
        self.agent = Agent(
            memory_path=str(data_dir),
            use_vllm=use_vllm,
            model=model,
            max_tool_turns=max_tool_turns,
            predetermined_memory_path=False
        )
        
        logger.info(f"MemAgentStorage initialized at {data_dir}")
        logger.info(f"Using model: {model or 'default'}, vLLM: {use_vllm}")
    
    def _chat_with_agent(self, message: str) -> AgentResponse:
        """
        Internal helper to chat with the agent
        
        Args:
            message: Message to send to agent
            
        Returns:
            Agent response
        """
        try:
            response = self.agent.chat(message)
            logger.debug(f"Agent response: {response.reply[:100]}...")
            return response
        except Exception as e:
            logger.error(f"Error chatting with agent: {e}", exc_info=True)
            raise
    
    def store(
        self,
        content: str,
        category: str = "general",
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Store information using mem-agent
        
        The agent will intelligently organize the information into appropriate
        markdown files (user.md, entities/*.md, etc.)
        
        Args:
            content: Content to store
            category: Category hint for organization
            metadata: Additional metadata
            tags: Optional tags
            
        Returns:
            Result with success status
        """
        try:
            # Build natural language instruction for the agent
            instruction = f"Please save the following information to memory: {content}"
            
            if category and category != "general":
                instruction += f"\n\nCategory: {category}"
            
            if tags:
                instruction += f"\nTags: {', '.join(tags)}"
            
            if metadata:
                metadata_str = json.dumps(metadata, ensure_ascii=False)
                instruction += f"\nMetadata: {metadata_str}"
            
            # Chat with agent to store the information
            response = self._chat_with_agent(instruction)
            
            return {
                "success": True,
                "message": "Information stored successfully via mem-agent",
                "agent_reply": response.reply,
                "agent_thoughts": response.thoughts,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error storing memory: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def retrieve(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve information using mem-agent
        
        The agent will search through its memory files and return relevant information.
        
        Args:
            query: Search query
            category: Filter by category
            tags: Filter by tags
            limit: Maximum number of results (hint to agent)
            
        Returns:
            Dict with retrieved memories
        """
        try:
            # Build natural language query for the agent
            if query:
                instruction = f"Please search your memory and tell me about: {query}"
            else:
                instruction = "Please show me what you have in your memory"
            
            if category:
                instruction += f"\n\nFocus on category: {category}"
            
            if tags:
                instruction += f"\nLooking for tags: {', '.join(tags)}"
            
            instruction += f"\n\nPlease provide up to {limit} relevant pieces of information."
            instruction += "\n\nIMPORTANT: Only retrieve information, do not add anything new to memory."
            
            # Chat with agent to retrieve information
            response = self._chat_with_agent(instruction)
            
            # Parse agent response into structured format
            # Note: The agent's reply is natural language, we return it as-is
            # The consumer can parse it or use it directly
            return {
                "success": True,
                "count": 1,  # We don't have exact count from agent
                "memories": [{
                    "content": response.reply,
                    "metadata": {
                        "agent_thoughts": response.thoughts,
                        "python_executed": bool(response.python_block)
                    },
                    "retrieved_at": datetime.now().isoformat()
                }],
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "count": 0,
                "memories": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search memories (convenience method)
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results
        """
        return self.retrieve(query=query, limit=limit)
    
    def list_all(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List all memories using mem-agent
        
        Args:
            limit: Optional limit on number of results
            
        Returns:
            All memories
        """
        try:
            instruction = "Please show me the current structure and contents of your memory using list_files()."
            
            if limit:
                instruction += f"\n\nPlease provide up to {limit} items."
            
            response = self._chat_with_agent(instruction)
            
            return {
                "success": True,
                "count": 1,
                "memories": [{
                    "content": response.reply,
                    "metadata": {
                        "type": "memory_structure",
                        "agent_thoughts": response.thoughts
                    },
                    "retrieved_at": datetime.now().isoformat()
                }],
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error listing memories: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "count": 0,
                "memories": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def list_categories(self) -> Dict[str, Any]:
        """
        List all available categories
        
        For mem-agent, categories are implicitly the file/directory structure.
        
        Returns:
            List of categories
        """
        try:
            instruction = "Please list all the files and directories in your memory, grouped by type."
            
            response = self._chat_with_agent(instruction)
            
            # Parse the response to extract categories
            # For now, return as a single category
            return {
                "success": True,
                "categories": {
                    "memory_files": {
                        "count": 1,
                        "description": response.reply
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error listing categories: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "categories": {},
                "timestamp": datetime.now().isoformat()
            }
    
    def delete(self, memory_id: int) -> Dict[str, Any]:
        """
        Delete a memory by ID
        
        Note: mem-agent uses file-based storage, not IDs.
        This operation would need to be adapted.
        
        Args:
            memory_id: ID of memory to delete
            
        Returns:
            Result of deletion
        """
        logger.warning("delete() by ID not directly supported by mem-agent")
        return {
            "success": False,
            "error": "Delete by ID not supported. Use natural language to delete specific files.",
            "message": "Use agent chat to delete specific memory files",
            "timestamp": datetime.now().isoformat()
        }
    
    def clear(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear memories (all or by category)
        
        Args:
            category: Optional category to clear
            
        Returns:
            Result of clearing
        """
        try:
            if category:
                instruction = f"Please delete all files related to category: {category}"
            else:
                instruction = "Please delete all memory files. Clear everything."
            
            instruction += "\n\nBe careful and confirm what you're deleting."
            
            response = self._chat_with_agent(instruction)
            
            return {
                "success": True,
                "message": f"Clear operation completed for category: {category or 'all'}",
                "agent_reply": response.reply,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error clearing memory: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
