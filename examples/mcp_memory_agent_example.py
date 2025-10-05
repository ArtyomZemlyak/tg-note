"""
Example: Using MCP Memory Agent with Autonomous Agent

This example demonstrates how to use the MCP (Model Context Protocol) 
memory agent tool with the autonomous agent.

The memory agent uses the driaforall/mem-agent model from HuggingFace
to provide intelligent memory storage and retrieval.

Prerequisites:
1. Install Node.js and npm
2. Install the mem-agent-mcp server:
   npm install -g @firstbatch/mem-agent-mcp
3. Set up API keys in .env:
   OPENAI_API_KEY=your_key_here
   MEM_AGENT_MCP_PROVIDER=openai
   MEM_AGENT_MCP_MODEL=gpt-4

References:
- Model: https://huggingface.co/driaforall/mem-agent
- MCP Server: https://github.com/firstbatchxyz/mem-agent-mcp
"""

import asyncio
import os
from pathlib import Path

from src.agents.autonomous_agent import AutonomousAgent
from src.agents.llm_connectors import OpenAIConnector
from loguru import logger


async def example_memory_storage():
    """Example: Store and retrieve memories"""
    
    logger.info("=== Memory Agent Example: Storage ===")
    
    # Create agent with MCP memory enabled
    agent = AutonomousAgent(
        llm_connector=OpenAIConnector(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4"
        ),
        config={},
        enable_mcp=True,
        enable_mcp_memory=True,
        max_iterations=5
    )
    
    # Store a memory
    logger.info("Storing a memory...")
    result = await agent.tool_manager.execute(
        "memory_store",
        {
            "content": "The user prefers Python over JavaScript for backend development",
            "tags": ["preferences", "programming"]
        }
    )
    logger.info(f"Store result: {result}")
    
    # Store another memory
    logger.info("Storing another memory...")
    result = await agent.tool_manager.execute(
        "memory_store",
        {
            "content": "The project uses PostgreSQL database with SQLAlchemy ORM",
            "tags": ["project", "database"]
        }
    )
    logger.info(f"Store result: {result}")
    
    # Search for memories
    logger.info("Searching memories about programming...")
    result = await agent.tool_manager.execute(
        "memory_search",
        {
            "query": "What are the user's programming preferences?",
            "limit": 5
        }
    )
    logger.info(f"Search result: {result}")


async def example_autonomous_agent_with_memory():
    """Example: Autonomous agent using memory to maintain context"""
    
    logger.info("=== Memory Agent Example: Autonomous Agent ===")
    
    # Create agent with MCP memory enabled
    agent = AutonomousAgent(
        llm_connector=OpenAIConnector(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4"
        ),
        config={},
        enable_mcp=True,
        enable_mcp_memory=True,
        enable_file_management=True,
        max_iterations=10
    )
    
    # First task: Learn about user preferences
    logger.info("\n--- Task 1: Learning preferences ---")
    content1 = {
        "text": """
        I prefer working with Python and FastAPI for backend development.
        I like to use SQLAlchemy for database operations.
        Please remember these preferences for future tasks.
        """
    }
    
    result1 = await agent.process(content1)
    logger.info(f"Task 1 completed: {result1.get('title')}")
    
    # Second task: Use the remembered preferences
    logger.info("\n--- Task 2: Using remembered preferences ---")
    content2 = {
        "text": """
        Based on my preferences, create a simple API endpoint example.
        Use the framework and database tools I prefer.
        """
    }
    
    result2 = await agent.process(content2)
    logger.info(f"Task 2 completed: {result2.get('title')}")
    logger.info(f"Markdown preview:\n{result2.get('markdown')[:500]}...")


async def example_memory_agent_direct():
    """Example: Using the memory agent tool directly"""
    
    logger.info("=== Memory Agent Example: Direct Usage ===")
    
    # Create agent with MCP memory enabled
    agent = AutonomousAgent(
        llm_connector=OpenAIConnector(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4"
        ),
        config={},
        enable_mcp=True,
        enable_mcp_memory=True,
        max_iterations=5
    )
    
    # Use the unified memory agent tool
    logger.info("Using unified memory agent tool...")
    
    # Store a memory
    result = await agent.tool_manager.execute(
        "mcp_memory_agent",
        {
            "action": "store",
            "content": "User is building a Telegram bot with knowledge base",
            "context": "Project context"
        }
    )
    logger.info(f"Store result: {result}")
    
    # Search memories
    result = await agent.tool_manager.execute(
        "mcp_memory_agent",
        {
            "action": "search",
            "content": "What is the user building?"
        }
    )
    logger.info(f"Search result: {result}")
    
    # List all memories
    result = await agent.tool_manager.execute(
        "mcp_memory_agent",
        {
            "action": "list"
        }
    )
    logger.info(f"List result: {result}")


async def main():
    """Run all examples"""
    
    # Check prerequisites
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found in environment")
        return
    
    try:
        # Example 1: Basic memory storage and retrieval
        await example_memory_storage()
        
        # Example 2: Autonomous agent with memory
        await example_autonomous_agent_with_memory()
        
        # Example 3: Direct usage of memory agent tool
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
        level="INFO"
    )
    
    # Run examples
    asyncio.run(main())
