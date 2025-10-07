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

Technical:
  - Shared MemoryStorage class for both Python and MCP server versions
  - MCP server for autonomous operation
  - Integrated as MCP server component of the tg-note system
  - Settings are in config.settings module

Installation:
  Run: python scripts/install_mem_agent.py
"""

from .storage import MemoryStorage

__all__ = [
    "MemoryStorage",
]