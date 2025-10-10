#!/usr/bin/env python3
"""
HTTP/SSE MCP Server for Memory Storage

This server provides memory storage/retrieval via HTTP using Server-Sent Events (SSE).
Alternative to stdio-based memory_server.py for better compatibility with some clients.

Usage:
    python -m src.agents.mcp.memory.memory_server_http [--port PORT] [--host HOST] [--user-id USER_ID]

Default:
    Host: 127.0.0.1
    Port: 8765
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

try:
    from fastmcp import FastMCP
except ImportError:
    print("Error: fastmcp not installed. Install with: pip install fastmcp")
    sys.exit(1)

# Import shared memory storage
from src.agents.mcp.memory.memory_storage import MemoryStorage

# Configure logger (will be reconfigured in main with file logging)
logger.remove()


# Initialize FastMCP server
mcp = FastMCP("memory", version="1.0.0")

# Global storage (will be initialized in main)
storage: Optional[MemoryStorage] = None


def init_storage(user_id: Optional[int] = None) -> MemoryStorage:
    """
    Initialize memory storage

    Args:
        user_id: Optional user ID for per-user storage

    Returns:
        Initialized MemoryStorage
    """
    # Setup storage directory
    # Priority:
    # 1. KB_PATH env var (set by memory_tool.py for user-specific KB)
    # 2. Legacy user_id-based path (for backward compatibility)
    # 3. Shared memory (fallback)
    kb_path = os.getenv("KB_PATH")
    memory_postfix = os.getenv("MEM_AGENT_MEMORY_POSTFIX", "memory")

    if kb_path:
        # Use KB-based path: {kb_path}/{memory_postfix}
        data_dir = Path(kb_path) / memory_postfix
        logger.info(f"Using KB-based memory path: {data_dir}")
    elif user_id:
        # Legacy: user_id-based path
        data_dir = Path(f"data/memory/user_{user_id}")
        logger.info(f"Using legacy user-based memory path: {data_dir}")
    else:
        # Fallback: shared memory
        data_dir = Path("data/memory/shared")
        logger.info(f"Using shared memory path: {data_dir}")

    return MemoryStorage(data_dir)


@mcp.tool()
def store_memory(
    content: str, category: str = "general", tags: list[str] = None, metadata: dict = None
) -> dict:
    """
    Store information in memory for later retrieval

    Args:
        content: Content to store in memory
        category: Category for organization (e.g., 'tasks', 'notes', 'ideas')
        tags: Optional tags for categorization
        metadata: Additional metadata (optional)

    Returns:
        Result with memory ID
    """
    try:
        if storage is None:
            logger.error("Storage not initialized when calling store_memory")
            return {"success": False, "error": "Storage not initialized"}

        logger.debug(f"Storing memory: category={category}, content_length={len(content)}")
        result = storage.store(
            content=content, category=category, tags=tags or [], metadata=metadata or {}
        )
        logger.info(f"Memory stored successfully: {result.get('id', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"Error storing memory: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to store memory: {str(e)}"}


@mcp.tool()
def retrieve_memory(
    query: str = None, category: str = None, tags: list[str] = None, limit: int = 10
) -> dict:
    """
    Retrieve information from memory

    Args:
        query: Search query (optional - returns all if not specified)
        category: Filter by category (optional)
        tags: Filter by tags (optional)
        limit: Maximum number of results

    Returns:
        List of matching memories
    """
    try:
        if storage is None:
            logger.error("Storage not initialized when calling retrieve_memory")
            return {"success": False, "error": "Storage not initialized"}

        logger.debug(f"Retrieving memory: query={query}, category={category}, limit={limit}")
        result = storage.retrieve(query=query, category=category, tags=tags, limit=limit)
        logger.info(f"Memory retrieved: {len(result.get('memories', []))} results")
        return result
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to retrieve memory: {str(e)}"}


@mcp.tool()
def list_categories() -> dict:
    """
    List all memory categories with counts

    Returns:
        List of categories with their memory counts
    """
    try:
        if storage is None:
            logger.error("Storage not initialized when calling list_categories")
            return {"success": False, "error": "Storage not initialized"}

        logger.debug("Listing categories")
        result = storage.list_categories()
        logger.info(f"Categories listed: {len(result.get('categories', []))} categories")
        return result
    except Exception as e:
        logger.error(f"Error listing categories: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to list categories: {str(e)}"}


def main():
    """Main entry point"""
    global storage

    parser = argparse.ArgumentParser(
        description="Memory HTTP MCP Server - Memory storage via HTTP/SSE"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to (default: 8765)")
    parser.add_argument(
        "--user-id", type=int, help="User ID for per-user memory storage (optional)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    parser.add_argument(
        "--log-file",
        default="logs/mcp_servers/memory_mcp.log",
        help="Log file path (default: logs/mcp_servers/memory_mcp.log)",
    )

    args = parser.parse_args()

    # Ensure log directory exists
    log_file = Path(args.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging with both file and console output
    logger.remove()
    
    # File logging with rotation (keep last 7 days, max 10MB per file)
    logger.add(
        args.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=args.log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
    
    # Console logging (less verbose, INFO and above)
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    # Initialize storage
    storage = init_storage(user_id=args.user_id)

    logger.info(f"Starting memory HTTP MCP server")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"User ID: {args.user_id or 'shared'}")

    # Run server
    try:
        mcp.run(transport="sse", host=args.host, port=args.port)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
