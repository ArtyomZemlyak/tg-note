"""
MCP Server for Memory Agent

This module provides an MCP (Model Context Protocol) server interface for the
mem-agent, allowing it to be used as a tool by other agents through the MCP protocol.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from fastmcp import Context, FastMCP
except Exception:  # pragma: no cover - optional dependency for tests
    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self, *args, **kwargs):
            def _wrap(fn):
                return fn

            return _wrap

        def run(self, *args, **kwargs):
            pass

    Context = object  # type: ignore
    FastMCP = _Dummy  # type: ignore

from src.agents.mcp.memory.mem_agent_impl.agent import Agent
from src.agents.mcp.memory.mem_agent_impl.settings import get_memory_path

# Initialize FastMCP server
mcp = FastMCP("mem-agent")


# Global agent instance (will be initialized per request or shared)
_agent_instances: Dict[str, Agent] = {}


def get_agent(
    memory_path: Optional[str] = None, use_vllm: bool = True, model: Optional[str] = None
) -> Agent:
    """
    Get or create an agent instance for the given memory path.

    Args:
        memory_path: Path to memory directory. If None, uses default.
        use_vllm: Whether to use vLLM backend (default True)
        model: Model name to use. If None, uses default from settings.

    Returns:
        Agent instance
    """
    # Use memory path as key for caching agents
    key = memory_path or "default"

    if key not in _agent_instances:
        _agent_instances[key] = Agent(
            memory_path=memory_path, use_vllm=use_vllm, model=model, predetermined_memory_path=False
        )

    return _agent_instances[key]


@mcp.tool()
async def chat_with_memory(question: str, memory_path: Optional[str] = None) -> str:
    """
    Chat with the memory agent. The agent can read from and write to its memory
    (Obsidian-style markdown files) to remember information across conversations.

    Args:
        question: The question or instruction for the memory agent
        memory_path: Optional path to a specific memory directory. If not provided,
                    uses the default memory location.

    Returns:
        The agent's response after interacting with memory

    Example:
        >>> await chat_with_memory("Remember that my favorite color is blue")
        "I've recorded that your favorite color is blue in my memory."

        >>> await chat_with_memory("What's my favorite color?")
        "According to my memory, your favorite color is blue."
    """
    try:
        # Get or create agent instance
        agent = get_agent(memory_path=memory_path)

        # Run agent chat (this is synchronous, so we run it in executor)
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, agent.chat, question)

        # Return the reply part of the response
        return response.reply or "I processed your request but have no specific reply."

    except Exception as e:
        return f"Error communicating with memory agent: {str(e)}"


@mcp.tool()
async def query_memory(query: str, memory_path: Optional[str] = None) -> str:
    """
    Query the memory agent to retrieve information without modifying memory.

    This is a read-only operation that searches through the agent's memory
    to find relevant information.

    Args:
        query: The query to search for in memory
        memory_path: Optional path to a specific memory directory

    Returns:
        Information retrieved from memory

    Example:
        >>> await query_memory("What do you know about my work?")
        "You work at Acme Corp as a senior engineer..."
    """
    try:
        # Prefix the query to indicate we only want retrieval
        retrieval_query = f"Please search your memory and tell me: {query}. Do not add any new information to memory."

        agent = get_agent(memory_path=memory_path)
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, agent.chat, retrieval_query)

        return response.reply or "No information found in memory."

    except Exception as e:
        return f"Error querying memory: {str(e)}"


@mcp.tool()
async def save_to_memory(information: str, memory_path: Optional[str] = None) -> str:
    """
    Save specific information to the agent's memory.

    Args:
        information: The information to save
        memory_path: Optional path to a specific memory directory

    Returns:
        Confirmation that information was saved

    Example:
        >>> await save_to_memory("The user's name is Alice and she works at Google")
        "I've saved that information to memory."
    """
    try:
        save_instruction = f"Please save the following information to memory: {information}"

        agent = get_agent(memory_path=memory_path)
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, agent.chat, save_instruction)

        return response.reply or "Information saved to memory."

    except Exception as e:
        return f"Error saving to memory: {str(e)}"


@mcp.tool()
async def list_memory_structure(memory_path: Optional[str] = None) -> str:
    """
    List the current memory structure (files and directories).

    Args:
        memory_path: Optional path to a specific memory directory

    Returns:
        A tree structure of the memory directory

    Example:
        >>> await list_memory_structure()
        ./
        ├── user.md
        └── entities/
            ├── alice.md
            └── google.md
    """
    try:
        list_instruction = "Please show me the current structure of your memory using list_files()."

        agent = get_agent(memory_path=memory_path)
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, agent.chat, list_instruction)

        return response.reply or "Memory structure not available."

    except Exception as e:
        return f"Error listing memory structure: {str(e)}"


def run_server(host: str = "127.0.0.1", port: int = 8766):
    """
    Run the MCP server for mem-agent.

    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8766)
    """
    print(f"Starting mem-agent MCP server on {host}:{port}")
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run mem-agent MCP server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8766, help="Port to bind to")

    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
