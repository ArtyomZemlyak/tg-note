"""
Example: Using MCP Memory Agent - Agent's Personal Note-Taking System

This example demonstrates how the autonomous agent can use the mem-agent tool
to record notes and search through them during task execution.

The mem-agent provides a personal note-taking and search system specifically
for the agent to:
- Record important findings, context, or information during task execution
- Search through recorded notes to "remember" what was found earlier
- Maintain working memory across multiple LLM calls within one session

This is especially useful for autonomous agents (like qwen code cli) that make
many LLM calls within a single session.

The memory agent uses embeddings (e.g., BAAI/bge-m3) from HuggingFace.

Prerequisites:
1. Run: python scripts/install_mem_agent.py
2. Set up API keys in .env:
   OPENAI_API_KEY=your_key_here

References:
- Model: https://huggingface.co/BAAI/bge-m3
- Installation: scripts/install_mem_agent.py
"""

import asyncio
import os
from pathlib import Path

from loguru import logger

from src.agents.autonomous_agent import AutonomousAgent
from src.agents.llm_connectors import OpenAIConnector


async def example_memory_storage():
    """Example: Agent recording and searching notes"""

    logger.info("=== Memory Agent Example: Agent Note-Taking ===")

    # Create agent with MCP memory enabled
    agent = AutonomousAgent(
        llm_connector=OpenAIConnector(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4"),
        config={},
        enable_mcp=True,
        enable_mcp_memory=True,
        max_iterations=5,
    )

    # Agent records a note (finding during code analysis)
    logger.info("Agent recording a note about a finding...")
    result = await agent.tool_manager.execute(
        "memory_store",
        {
            "content": "Found SQL injection vulnerability in /api/auth/login endpoint - user input not sanitized",
            "tags": ["security", "vulnerability"],
        },
    )
    logger.info(f"Note recorded: {result}")

    # Agent records another note
    logger.info("Agent recording another note...")
    result = await agent.tool_manager.execute(
        "memory_store",
        {
            "content": "Database uses PostgreSQL 14 with pgvector extension for vector search",
            "tags": ["infrastructure", "database"],
        },
    )
    logger.info(f"Note recorded: {result}")

    # Agent searches its notes to remember
    logger.info("Agent searching notes to recall security issues...")
    result = await agent.tool_manager.execute(
        "memory_search", {"query": "What security vulnerabilities did I find?", "limit": 5}
    )
    logger.info(f"Search result: {result}")


async def example_autonomous_agent_with_memory():
    """Example: Autonomous agent using notes to maintain context during tasks"""

    logger.info("=== Memory Agent Example: Agent Session with Notes ===")

    # Create agent with MCP memory enabled
    agent = AutonomousAgent(
        llm_connector=OpenAIConnector(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4"),
        config={},
        enable_mcp=True,
        enable_mcp_memory=True,
        enable_file_management=True,
        max_iterations=10,
    )

    # Task 1: Analyze codebase (agent records findings as notes)
    logger.info("\n--- Task 1: Code Analysis (agent records notes) ---")
    content1 = {
        "text": """
        Analyze the authentication module in this codebase.
        Record any important findings, vulnerabilities, or patterns you discover.
        (Note: Agent will internally use memory_store to record findings)
        """
    }

    result1 = await agent.process(content1)
    logger.info(f"Task 1 completed: {result1.get('title')}")

    # Task 2: Generate report (agent searches notes to recall findings)
    logger.info("\n--- Task 2: Report Generation (agent searches notes) ---")
    content2 = {
        "text": """
        Generate a security report based on the findings from the code analysis.
        What vulnerabilities did you discover?
        (Note: Agent will internally use memory_search to recall previous findings)
        """
    }

    result2 = await agent.process(content2)
    logger.info(f"Task 2 completed: {result2.get('title')}")
    logger.info(f"Markdown preview:\n{result2.get('markdown')[:500]}...")


async def example_memory_agent_direct():
    """Example: Direct usage of agent's note-taking tool"""

    logger.info("=== Memory Agent Example: Direct Note-Taking ===")

    # Create agent with MCP memory enabled
    agent = AutonomousAgent(
        llm_connector=OpenAIConnector(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4"),
        config={},
        enable_mcp=True,
        enable_mcp_memory=True,
        max_iterations=5,
    )

    # Use the unified note-taking tool
    logger.info("Using unified note-taking tool...")

    # Agent records a note
    result = await agent.tool_manager.execute(
        "mcp_memory_agent",
        {
            "action": "store",
            "content": "API endpoint /api/users has rate limiting disabled - potential DoS vulnerability",
            "context": "Security audit findings",
        },
    )
    logger.info(f"Note recorded: {result}")

    # Agent searches its notes
    result = await agent.tool_manager.execute(
        "mcp_memory_agent", {"action": "search", "content": "What DoS vulnerabilities did I find?"}
    )
    logger.info(f"Search result: {result}")

    # List all recorded notes
    result = await agent.tool_manager.execute("mcp_memory_agent", {"action": "list"})
    logger.info(f"All notes: {result}")


async def main():
    """Run all examples"""

    # Check prerequisites
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found in environment")
        return

    try:
        # Example 1: Agent recording and searching notes
        await example_memory_storage()

        # Example 2: Autonomous agent maintaining context with notes
        await example_autonomous_agent_with_memory()

        # Example 3: Direct usage of note-taking tool
        await example_memory_agent_direct()

        logger.info("\n=== All examples completed successfully! ===")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO",
    )

    # Run examples
    asyncio.run(main())
