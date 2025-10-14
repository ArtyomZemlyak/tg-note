#!/usr/bin/env python3
"""
MCP Hub Server - Unified MCP Gateway

This server provides:
1. MCP Server Registry - Register and discover MCP servers
2. Built-in MCP Tools - Memory and other common tools
3. HTTP/SSE API - For all MCP operations

Architecture:
- Single entry point for all MCP operations
- Hosts built-in tools (memory, etc.)
- Manages registry of external MCP servers
- Per-user isolation for both tools and servers

Usage:
    python -m src.mcp.mcp_hub_server [--port PORT] [--host HOST]

Default:
    Host: 127.0.0.1
    Port: 8765
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

try:
    from fastmcp import FastMCP
except ImportError:
    print("Error: fastmcp not installed. Install with: pip install fastmcp")
    sys.exit(1)

# Import memory storage components
from src.mcp.memory.memory_factory import MemoryStorageFactory
from src.mcp.memory.memory_storage import MemoryStorage

# Import registry components
from src.mcp.registry.registry import MCPServerRegistry, MCPServerSpec

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
    log_dir / "mcp_hub.log",
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
    log_dir / "mcp_hub_errors.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)


# Initialize FastMCP server
mcp = FastMCP("mcp-hub", version="1.0.0")

# Per-user storage instances (user_id -> MemoryStorage)
_storages: Dict[int, MemoryStorage] = {}

# Global registry instance
_registry: Optional[MCPServerRegistry] = None


def get_registry() -> MCPServerRegistry:
    """
    Get or create global MCP server registry

    Returns:
        MCPServerRegistry instance
    """
    global _registry
    if _registry is None:
        servers_dir = Path("data/mcp_servers")
        _registry = MCPServerRegistry(servers_dir, user_id=None)
        _registry.discover_servers()
        logger.info(
            f"📋 Registry initialized: {len(_registry.get_all_servers())} servers discovered"
        )
    return _registry


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
    logger.info("=" * 60)
    logger.info(f"🚀 INITIALIZING STORAGE FOR USER {user_id}")
    logger.info("=" * 60)

    data_dir = Path(f"data/memory/user_{user_id}")
    logger.info(f"📁 Data directory: {data_dir.absolute()}")

    # Get storage type from environment (default: json)
    # Can be "json", "vector", or "mem-agent"
    storage_type = os.getenv("MEM_AGENT_STORAGE_TYPE", "json")
    logger.info(f"💾 Storage type: {storage_type}")

    # Log all relevant environment variables
    logger.info("")
    logger.info("📋 Configuration:")
    logger.info(
        f"  - MEM_AGENT_STORAGE_TYPE: {os.getenv('MEM_AGENT_STORAGE_TYPE', 'json (default)')}"
    )
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
            logger.info("=" * 60)
            return storage
        except Exception as e:
            logger.error(f"❌ Failed to create {storage_type} storage: {e}", exc_info=True)
            logger.warning("⚠️  Falling back to JSON storage")
            storage = MemoryStorage(data_dir)
            _storages[user_id] = storage
            logger.info("=" * 60)
            return storage
    else:
        # Use legacy wrapper for JSON (default)
        logger.info("🔧 Creating JSON storage (default)...")
        storage = MemoryStorage(data_dir)
        _storages[user_id] = storage
        logger.info(f"✅ JSON storage created successfully for user {user_id}")
        logger.info("=" * 60)
        return storage


# ============================================================================
# Health Check Endpoint
# ============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for container orchestration"""
    try:
        registry = get_registry()
        return {
            "status": "ok",
            "service": "mcp-hub",
            "version": "1.0.0",
            "registry": {
                "servers_total": len(registry.get_all_servers()),
                "servers_enabled": len(registry.get_enabled_servers()),
            },
            "storage": {
                "active_users": len(_storages),
            },
        }
    except Exception as e:
        logger.error(f"❌ Exception in health check endpoint: {e}", exc_info=True)
        return {
            "status": "error",
            "service": "mcp-hub",
            "version": "1.0.0",
            "error": str(e),
            "error_type": type(e).__name__,
        }


# ============================================================================
# Memory Tools - Built-in MCP Tools
# ============================================================================


@mcp.tool()
def store_memory(
    content: str,
    user_id: int,
    category: str = "general",
    tags: list[str] = None,
    metadata: dict = None,
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
    user_id: int, query: str = None, category: str = None, tags: list[str] = None, limit: int = 10
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
        count = result.get("count", 0)
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
        categories = result.get("categories", {})
        logger.info(f"✅ Categories retrieved: {len(categories)} categories")
        logger.debug(f"  Categories: {list(categories.keys())}")
        return result
    except Exception as e:
        logger.error(f"❌ Error listing categories: {e}", exc_info=True)
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


# ============================================================================
# Registry Tools - MCP Server Management
# ============================================================================


@mcp.tool()
def list_mcp_servers(user_id: int = None) -> dict:
    """
    List all registered MCP servers

    Args:
        user_id: Optional user ID for user-specific servers

    Returns:
        List of registered servers with their status
    """
    logger.info("📋 LIST_MCP_SERVERS called")
    logger.info(f"  User: {user_id or 'global'}")

    try:
        registry = get_registry()
        servers = registry.get_all_servers()

        result = {
            "success": True,
            "total": len(servers),
            "servers": [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "enabled": spec.enabled,
                    "command": spec.command,
                }
                for spec in servers
            ],
        }

        logger.info(f"✅ Listed {len(servers)} servers")
        return result

    except Exception as e:
        logger.error(f"❌ Error listing servers: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_mcp_server(name: str) -> dict:
    """
    Get details of a specific MCP server

    Args:
        name: Server name

    Returns:
        Server details
    """
    logger.info(f"🔍 GET_MCP_SERVER called: {name}")

    try:
        registry = get_registry()
        spec = registry.get_server(name)

        if not spec:
            return {"success": False, "error": f"Server '{name}' not found"}

        result = {
            "success": True,
            "server": {
                "name": spec.name,
                "description": spec.description,
                "enabled": spec.enabled,
                "command": spec.command,
                "args": spec.args,
                "env": spec.env or {},
                "working_dir": spec.working_dir,
            },
        }

        logger.info(f"✅ Retrieved server: {name}")
        return result

    except Exception as e:
        logger.error(f"❌ Error getting server: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
def register_mcp_server(
    name: str,
    description: str,
    command: str,
    args: list[str],
    env: dict = None,
    working_dir: str = None,
    enabled: bool = True,
) -> dict:
    """
    Register a new MCP server

    Args:
        name: Server name (unique identifier)
        description: Human-readable description
        command: Command to execute
        args: Command-line arguments
        env: Environment variables (optional)
        working_dir: Working directory (optional)
        enabled: Whether to enable the server

    Returns:
        Success status
    """
    logger.info(f"➕ REGISTER_MCP_SERVER called: {name}")

    try:
        registry = get_registry()

        spec = MCPServerSpec(
            name=name,
            description=description,
            command=command,
            args=args,
            env=env,
            working_dir=working_dir,
            enabled=enabled,
        )

        success = registry.add_server(spec)

        if success:
            logger.info(f"✅ Registered server: {name}")
            return {"success": True, "message": f"Server '{name}' registered successfully"}
        else:
            return {"success": False, "error": f"Server '{name}' already exists"}

    except Exception as e:
        logger.error(f"❌ Error registering server: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
def enable_mcp_server(name: str) -> dict:
    """
    Enable an MCP server

    Args:
        name: Server name

    Returns:
        Success status
    """
    logger.info(f"✅ ENABLE_MCP_SERVER called: {name}")

    try:
        registry = get_registry()
        success = registry.enable_server(name)

        if success:
            return {"success": True, "message": f"Server '{name}' enabled"}
        else:
            return {"success": False, "error": f"Server '{name}' not found"}

    except Exception as e:
        logger.error(f"❌ Error enabling server: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
def disable_mcp_server(name: str) -> dict:
    """
    Disable an MCP server

    Args:
        name: Server name

    Returns:
        Success status
    """
    logger.info(f"❌ DISABLE_MCP_SERVER called: {name}")

    try:
        registry = get_registry()
        success = registry.disable_server(name)

        if success:
            return {"success": True, "message": f"Server '{name}' disabled"}
        else:
            return {"success": False, "error": f"Server '{name}' not found"}

    except Exception as e:
        logger.error(f"❌ Error disabling server: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MCP Hub Server - Unified MCP gateway with registry and built-in tools"
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

    logger.info("=" * 80)
    logger.info("🚀 STARTING MCP HUB SERVER")
    logger.info("=" * 80)
    logger.info("")
    logger.info("🔧 Server Configuration:")
    logger.info(f"  🏗️  Host: {args.host}")
    logger.info(f"  🔌 Port: {args.port}")
    logger.info(f"  👥 Mode: Multi-user (per-user storage)")
    logger.info("")
    logger.info("📦 Features:")
    logger.info(f"  ✅ Memory Tools (json/vector/mem-agent)")
    logger.info(f"  ✅ MCP Server Registry")
    logger.info(f"  ✅ Per-user isolation")
    logger.info("")
    logger.info("💾 Storage Configuration:")
    logger.info(f"  - Storage type: {os.getenv('MEM_AGENT_STORAGE_TYPE', 'json')}")
    logger.info(f"  - Backend: {os.getenv('MEM_AGENT_BACKEND', 'auto')}")
    logger.info(f"  - Model: {os.getenv('MEM_AGENT_MODEL', 'default')}")
    logger.info("")
    logger.info("📋 Environment Variables:")
    logger.info(
        f"  - MEM_AGENT_STORAGE_TYPE: {os.getenv('MEM_AGENT_STORAGE_TYPE', 'not set (default: json)')}"
    )
    logger.info(f"  - MEM_AGENT_MODEL: {os.getenv('MEM_AGENT_MODEL', 'not set')}")
    logger.info(
        f"  - MEM_AGENT_BACKEND: {os.getenv('MEM_AGENT_BACKEND', 'not set (default: auto)')}"
    )
    logger.info(
        f"  - MEM_AGENT_MAX_TOOL_TURNS: {os.getenv('MEM_AGENT_MAX_TOOL_TURNS', 'not set (default: 20)')}"
    )
    logger.info("")
    logger.info("ℹ️  Notes:")
    logger.info("  - User storage: data/memory/user_{user_id}/")
    logger.info("  - Server configs: data/mcp_servers/*.json")
    logger.info("=" * 80)

    # Initialize registry
    get_registry()

    # Run server
    try:
        logger.info(f"🌐 Server listening on http://{args.host}:{args.port}/sse")
        logger.info(f"🏥 Health check: http://{args.host}:{args.port}/health")
        mcp.run(transport="sse", host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("⏹️  Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
