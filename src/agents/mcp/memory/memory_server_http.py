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

# Import shared memory storage and factory
from src.agents.mcp.memory.memory_factory import MemoryStorageFactory
from src.agents.mcp.memory.memory_storage import MemoryStorage

# Configure logger
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

logger.remove()

# Console logging
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
)

# File logging for errors and debugging
logger.add(
    log_dir / "memory_http.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)

# Separate error log
logger.add(
    log_dir / "memory_http_errors.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)


# Initialize FastMCP server
mcp = FastMCP("memory", version="1.0.0")

# Global storage (will be initialized in main)
storage: Optional[MemoryStorage] = None


def init_storage(user_id: Optional[int] = None):
    """
    Initialize memory storage using the factory pattern

    Args:
        user_id: Optional user ID for per-user storage

    Returns:
        Initialized memory storage (type depends on MEM_AGENT_STORAGE_TYPE env var)
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

    # Get storage type from environment (default: json)
    # Can be "json", "vector", or "mem-agent"
    storage_type = os.getenv("MEM_AGENT_STORAGE_TYPE", "json")
    logger.info(f"Initializing storage type: {storage_type}")

    # Create storage using factory or legacy wrapper
    if storage_type != "json":
        # Use factory for non-default storage types
        try:
            model_name = os.getenv("MEM_AGENT_MODEL", None)
            backend = os.getenv("MEM_AGENT_BACKEND", "auto")

            storage = MemoryStorageFactory.create(
                storage_type=storage_type,
                data_dir=data_dir,
                model_name=model_name,
                backend=backend,
            )
            logger.info(f"Created {storage_type} storage via factory with backend={backend}")
            return storage
        except Exception as e:
            logger.error(
                f"Failed to create {storage_type} storage: {e}. Falling back to json.",
                exc_info=True,
            )
            return MemoryStorage(data_dir)
    else:
        # Use legacy wrapper for JSON (default)
        logger.info("Using default JSON storage")
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
    logger.debug(f"store_memory called: content={content[:100]}..., category={category}")
    
    if storage is None:
        logger.error("Storage not initialized")
        return {"success": False, "error": "Storage not initialized"}

    try:
        result = storage.store(
            content=content, category=category, tags=tags or [], metadata=metadata or {}
        )
        logger.debug(f"Store successful: {result}")
        return result
    except Exception as e:
        logger.error(f"Error storing memory: {e}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


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
    logger.debug(f"retrieve_memory called: query={query}, category={category}, limit={limit}")
    
    if storage is None:
        logger.error("Storage not initialized")
        return {"success": False, "error": "Storage not initialized"}

    try:
        result = storage.retrieve(query=query, category=category, tags=tags, limit=limit)
        logger.debug(f"Retrieve successful: found {result.get('count', 0)} memories")
        return result
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool()
def list_categories() -> dict:
    """
    List all memory categories with counts

    Returns:
        List of categories with their memory counts
    """
    logger.debug("list_categories called")
    
    if storage is None:
        logger.error("Storage not initialized")
        return {"success": False, "error": "Storage not initialized"}

    try:
        result = storage.list_categories()
        logger.debug(f"Categories retrieved: {result}")
        return result
    except Exception as e:
        logger.error(f"Error listing categories: {e}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


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

    args = parser.parse_args()

    # Configure logging level
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=args.log_level,
    )

    # Initialize storage
    logger.info("="*60)
    logger.info("Starting MCP Memory Server (HTTP/SSE)")
    logger.info("="*60)
    logger.info("Initializing memory storage...")
    try:
        storage = init_storage(user_id=args.user_id)
        storage_type_name = type(storage).__name__
        logger.info(f"Storage initialized successfully: {storage_type_name}")
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}", exc_info=True)
        sys.exit(1)

    logger.info("")
    logger.info("Server Configuration:")
    logger.info(f"  Host: {args.host}")
    logger.info(f"  Port: {args.port}")
    logger.info(f"  User ID: {args.user_id or 'shared'}")
    logger.info(f"  Storage type: {os.getenv('MEM_AGENT_STORAGE_TYPE', 'json')}")
    logger.info(f"  Backend: {os.getenv('MEM_AGENT_BACKEND', 'auto')}")
    logger.info(f"  Model: {os.getenv('MEM_AGENT_MODEL', 'default')}")
    logger.info("="*60)

    # Run server
    try:
        logger.info(f"Server listening on http://{args.host}:{args.port}/sse")
        mcp.run(transport="sse", host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
