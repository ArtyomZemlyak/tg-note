"""
Memory Agent package - LLM-based agent for interacting with Obsidian-like memory systems.
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
