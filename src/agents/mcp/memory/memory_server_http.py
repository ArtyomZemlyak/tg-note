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

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


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
    kb_path = os.getenv('KB_PATH')
    memory_postfix = os.getenv('MEM_AGENT_MEMORY_POSTFIX', 'memory')
    
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
    content: str,
    category: str = "general",
    tags: list[str] = None,
    metadata: dict = None
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
    if storage is None:
        return {
            "success": False,
            "error": "Storage not initialized"
        }
    
    return storage.store(
        content=content,
        category=category,
        tags=tags or [],
        metadata=metadata or {}
    )


@mcp.tool()
def retrieve_memory(
    query: str = None,
    category: str = None,
    tags: list[str] = None,
    limit: int = 10
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
    if storage is None:
        return {
            "success": False,
            "error": "Storage not initialized"
        }
    
    return storage.retrieve(
        query=query,
        category=category,
        tags=tags,
        limit=limit
    )


@mcp.tool()
def list_categories() -> dict:
    """
    List all memory categories with counts
    
    Returns:
        List of categories with their memory counts
    """
    if storage is None:
        return {
            "success": False,
            "error": "Storage not initialized"
        }
    
    return storage.list_categories()


def main():
    """Main entry point"""
    global storage
    
    parser = argparse.ArgumentParser(
        description="Memory HTTP MCP Server - Memory storage via HTTP/SSE"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="User ID for per-user memory storage (optional)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=args.log_level
    )
    
    # Initialize storage
    storage = init_storage(user_id=args.user_id)
    
    logger.info(f"Starting memory HTTP MCP server")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"User ID: {args.user_id or 'shared'}")
    
    # Run server
    try:
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port
        )
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
