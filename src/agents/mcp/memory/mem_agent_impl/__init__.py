"""
Memory Agent package - LLM-based agent for interacting with Obsidian-like memory systems.

This is the mem-agent implementation that provides LLM-based memory management
with Obsidian-style markdown files and sandboxed code execution.

Part of the memory storage architecture:
- memory/json: JsonMemoryStorage (simple JSON-based)
- memory/vector: VectorBasedMemoryStorage (semantic search)
- memory/mem-agent: MemAgentStorage (LLM-based agent with tools)
"""

try:
    from .agent import Agent
    from .engine import execute_sandboxed_code
    from .schemas import AgentResponse, ChatMessage, Role, StaticMemory

    __all__ = [
        "Agent",
        "execute_sandboxed_code",
        "AgentResponse",
        "ChatMessage",
        "Role",
        "StaticMemory",
    ]
except ImportError as e:
    # If some modules can't be imported, just make the package importable
    import warnings

    warnings.warn(f"Some mem_agent modules could not be imported: {e}")
    __all__ = []
