"""
Memory Agent

A local memory agent that provides intelligent memory management using
a local LLM model through vLLM or MLX backends.

This module is adapted from https://github.com/firstbatchxyz/mem-agent-mcp
to work as an integrated component of the tg-note system.
"""

from .agent import MemoryAgent
from .server import MemoryAgentMCPServer
from .settings import MemoryAgentSettings

__all__ = [
    "MemoryAgent",
    "MemoryAgentMCPServer",
    "MemoryAgentSettings",
]