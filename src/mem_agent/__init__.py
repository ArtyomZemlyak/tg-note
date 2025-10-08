"""
Memory Agent - Personal Note-Taking System for Autonomous Agents

A local note-taking and search system specifically designed for the main agent.

Purpose:
  The agent uses this tool to:
  - Record notes: Write down important findings, context, or information during task execution
  - Search notes: Find and recall previously recorded information to "remember" details
  - Maintain working memory: Keep context across multiple LLM calls within a single session

Use Cases:
  - Autonomous agents (like qwen code cli) making many LLM calls in one session
  - Complex multi-step tasks where the agent needs to remember earlier findings
  - Maintaining context when the agent discovers information it needs later

Architecture (SOLID principles):
  - BaseMemoryStorage: Abstract interface for all storage implementations
  - JsonMemoryStorage: Simple JSON-based storage with substring search
  - ModelBasedMemoryStorage: AI-powered storage with semantic search using driaforall/mem-agent
  - MemoryStorageFactory: Factory for creating appropriate storage instances
  - MemoryStorage: Legacy compatibility class (delegates to factory)

Storage Types:
  - "json": Fast, lightweight, no ML dependencies (default)
  - "model": Semantic search using AI model, requires transformers/sentence-transformers

Settings are in config.settings module (MEM_AGENT_STORAGE_TYPE).

Installation:
  Run: python scripts/install_mem_agent.py
"""

# Core interfaces and implementations
from .base import BaseMemoryStorage
from .json_storage import JsonMemoryStorage
from .model_storage import ModelBasedMemoryStorage
from .factory import MemoryStorageFactory, create_memory_storage

# Legacy compatibility
from .storage import MemoryStorage

__all__ = [
    # Abstract interface
    "BaseMemoryStorage",
    
    # Concrete implementations
    "JsonMemoryStorage",
    "ModelBasedMemoryStorage",
    
    # Factory
    "MemoryStorageFactory",
    "create_memory_storage",
    
    # Legacy compatibility
    "MemoryStorage",
]