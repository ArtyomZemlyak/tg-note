#!/usr/bin/env python3
"""
HTTP/SSE MCP Server for Memory Storage

This server provides memory storage/retrieval via HTTP using Server-Sent Events (SSE).
Alternative to stdio-based memory_server.py for better compatibility with some clients.

Usage:
    python -m src.agents.mcp.memory.memory_server_http [--port PORT] [--host HOST]

Default:
    Host: 127.0.0.1
    Port: 8765
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

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

# Per-user storage instances (user_id -> MemoryStorage)
_storages: Dict[int, MemoryStorage] = {}


def get_storage(user_id: int) -> MemoryStorage:
    """
    Get or create memory storage for a specific user

    Args:
        user_id: User ID for per-user storage (required)

    Returns:
        Initialized memory storage (type depends on MEM_AGENT_STORAGE_TYPE env var)
    """
    # Return existing storage if already initialized
    if user_id in _storages:
        logger.debug(f"♻️ Reusing existing storage for user {user_id}")
        return _storages[user_id]
    
    # Create new storage for this user
    logger.info("="*60)
    logger.info(f"🚀 INITIALIZING STORAGE FOR USER {user_id}")
    logger.info("="*60)
    
    data_dir = Path(f"data/memory/user_{user_id}")
    logger.info(f"📁 Data directory: {data_dir.absolute()}")

    # Get storage type from environment (default: json)
    # Can be "json", "vector", or "mem-agent"
    storage_type = os.getenv("MEM_AGENT_STORAGE_TYPE", "json")
    logger.info(f"💾 Storage type: {storage_type}")
    
    # Log all relevant environment variables
    logger.info("")
    logger.info("📋 Configuration:")
    logger.info(f"  - MEM_AGENT_STORAGE_TYPE: {os.getenv('MEM_AGENT_STORAGE_TYPE', 'json (default)')}")
    logger.info(f"  - MEM_AGENT_MODEL: {os.getenv('MEM_AGENT_MODEL', 'not set')}")
    logger.info(f"  - MEM_AGENT_BACKEND: {os.getenv('MEM_AGENT_BACKEND', 'auto (default)')}")
    logger.info("")

    # Create storage using factory or legacy wrapper
    if storage_type != "json":
        # Use factory for non-default storage types
        logger.info(f"🔧 Creating {storage_type} storage via factory...")
        try:
            model_name = os.getenv("MEM_AGENT_MODEL", None)
            backend = os.getenv("MEM_AGENT_BACKEND", "auto")
            
            if model_name:
                logger.info(f"  📦 Model: {model_name}")
                logger.info(f"  🎮 Backend: {backend}")
            else:
                logger.warning("  ⚠️  No model specified, using default")

            storage = MemoryStorageFactory.create(
                storage_type=storage_type,
                data_dir=data_dir,
                model_name=model_name,
                backend=backend,
            )
            logger.info(f"✅ Successfully created {storage_type} storage for user {user_id}")
            _storages[user_id] = storage
            logger.info("="*60)
            return storage
        except Exception as e:
            logger.error(f"❌ Failed to create {storage_type} storage: {e}", exc_info=True)
            logger.warning("⚠️  Falling back to JSON storage")
            storage = MemoryStorage(data_dir)
            _storages[user_id] = storage
            logger.info("="*60)
            return storage
    else:
        # Use legacy wrapper for JSON (default)
        logger.info("🔧 Creating JSON storage (default)...")
        storage = MemoryStorage(data_dir)
        _storages[user_id] = storage
        logger.info(f"✅ JSON storage created successfully for user {user_id}")
        logger.info("="*60)
        return storage


@mcp.tool()
def store_memory(
    content: str, 
    user_id: int,
    category: str = "general", 
    tags: list[str] = None, 
    metadata: dict = None
) -> dict:
    """
    Store information in memory for later retrieval

    Args:
        content: Content to store in memory
        user_id: User ID (required for per-user isolation)
        category: Category for organization (e.g., 'tasks', 'notes', 'ideas')
        tags: Optional tags for categorization
        metadata: Additional metadata (optional)

    Returns:
        Result with memory ID
    """
    logger.info("💾 STORE_MEMORY called")
    logger.info(f"  User: {user_id}")
    logger.info(f"  Category: {category}")
    logger.info(f"  Content length: {len(content)} chars")
    logger.debug(f"  Content preview: {content[:200]}...")
    logger.debug(f"  Tags: {tags}")
    
    try:
        storage = get_storage(user_id)
    except Exception as e:
        logger.error(f"❌ Failed to get storage for user {user_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

    try:
        result = storage.store(
            content=content, category=category, tags=tags or [], metadata=metadata or {}
        )
        logger.info(f"✅ Store successful: ID={result.get('id', 'N/A')}")
        logger.debug(f"  Result: {json.dumps(result, ensure_ascii=False)}")
        return result
    except Exception as e:
        logger.error(f"❌ Error storing memory: {e}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool()
def retrieve_memory(
    user_id: int,
    query: str = None, 
    category: str = None, 
    tags: list[str] = None, 
    limit: int = 10
) -> dict:
    """
    Retrieve information from memory

    Args:
        user_id: User ID (required for per-user isolation)
        query: Search query (optional - returns all if not specified)
        category: Filter by category (optional)
        tags: Filter by tags (optional)
        limit: Maximum number of results

    Returns:
        List of matching memories
    """
    logger.info("🔍 RETRIEVE_MEMORY called")
    logger.info(f"  User: {user_id}")
    logger.info(f"  Query: {query or 'all'}")
    logger.info(f"  Category: {category or 'any'}")
    logger.info(f"  Tags: {tags}")
    logger.info(f"  Limit: {limit}")
    
    try:
        storage = get_storage(user_id)
    except Exception as e:
        logger.error(f"❌ Failed to get storage for user {user_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

    try:
        result = storage.retrieve(query=query, category=category, tags=tags, limit=limit)
        count = result.get('count', 0)
        logger.info(f"✅ Retrieve successful: found {count} memories")
        if count > 0:
            logger.debug(f"  First result preview: {str(result.get('memories', [{}])[0])[:200]}...")
        return result
    except Exception as e:
        logger.error(f"❌ Error retrieving memory: {e}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


@mcp.tool()
def list_categories(user_id: int) -> dict:
    """
    List all memory categories with counts

    Args:
        user_id: User ID (required for per-user isolation)

    Returns:
        List of categories with their memory counts
    """
    logger.info("📋 LIST_CATEGORIES called")
    logger.info(f"  User: {user_id}")
    
    try:
        storage = get_storage(user_id)
    except Exception as e:
        logger.error(f"❌ Failed to get storage for user {user_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

    try:
        result = storage.list_categories()
        categories = result.get('categories', {})
        logger.info(f"✅ Categories retrieved: {len(categories)} categories")
        logger.debug(f"  Categories: {list(categories.keys())}")
        return result
    except Exception as e:
        logger.error(f"❌ Error listing categories: {e}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Memory HTTP MCP Server - Multi-user memory storage via HTTP/SSE"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to (default: 8765)")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )

    args = parser.parse_args()

    # Configure logging level
    # NOTE: Don't call logger.remove() here - file handlers are already configured at module level
    # Just update the log level if needed
    # logger.remove()
    # logger.add(
    #     sys.stderr,
    #     format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    #     level=args.log_level,
    # )

    logger.info("="*80)
    logger.info("🚀 STARTING MCP MEMORY SERVER (HTTP/SSE)")
    logger.info("="*80)
    logger.info("")
    logger.info("🔧 Server Configuration:")
    logger.info(f"  🏗️  Host: {args.host}")
    logger.info(f"  🔌 Port: {args.port}")
    logger.info(f"  👥 Mode: Multi-user (per-user storage)")
    logger.info(f"  💾 Storage type: {os.getenv('MEM_AGENT_STORAGE_TYPE', 'json')}")
    logger.info(f"  🎮 Backend: {os.getenv('MEM_AGENT_BACKEND', 'auto')}")
    logger.info(f"  📦 Model: {os.getenv('MEM_AGENT_MODEL', 'default')}")
    logger.info("")
    logger.info("📋 Environment Variables:")
    logger.info(f"  - MEM_AGENT_STORAGE_TYPE: {os.getenv('MEM_AGENT_STORAGE_TYPE', 'not set (default: json)')}")
    logger.info(f"  - MEM_AGENT_MODEL: {os.getenv('MEM_AGENT_MODEL', 'not set')}")
    logger.info(f"  - MEM_AGENT_BACKEND: {os.getenv('MEM_AGENT_BACKEND', 'not set (default: auto)')}")
    logger.info(f"  - MEM_AGENT_MAX_TOOL_TURNS: {os.getenv('MEM_AGENT_MAX_TOOL_TURNS', 'not set (default: 20)')}")
    logger.info("")
    logger.info("ℹ️  Note: Each user's storage is isolated at data/memory/user_{{user_id}}/")
    logger.info("="*80)

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
