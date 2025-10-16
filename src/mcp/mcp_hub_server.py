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
from starlette.responses import JSONResponse
from starlette.requests import Request

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

# Built-in tools count (tools provided by MCP Hub itself)
# These are registered via @mcp.tool() decorator
BUILTIN_TOOLS = [
    "store_memory",
    "retrieve_memory",
    "list_categories",
]


def get_builtin_tools_count() -> int:
    """Get count of built-in MCP tools provided by the hub"""
    return len(BUILTIN_TOOLS)


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

    # Get settings from config.yaml (preferred) or environment variables (fallback)
    try:
        from config import settings as app_settings
        storage_type = app_settings.MEM_AGENT_STORAGE_TYPE
        model_name = app_settings.MEM_AGENT_MODEL
        backend = app_settings.MEM_AGENT_BACKEND
        logger.info("📋 Using configuration from config.yaml")
    except Exception:
        # Fallback to environment variables
        storage_type = os.getenv("MEM_AGENT_STORAGE_TYPE", "json")
        model_name = os.getenv("MEM_AGENT_MODEL", None)
        backend = os.getenv("MEM_AGENT_BACKEND", "auto")
        logger.info("📋 Using configuration from environment variables")
    
    logger.info(f"💾 Storage type: {storage_type}")
    logger.info("")
    logger.info("📋 Configuration:")
    logger.info(f"  - MEM_AGENT_STORAGE_TYPE: {storage_type}")
    logger.info(f"  - MEM_AGENT_MODEL: {model_name or 'default'}")
    logger.info(f"  - MEM_AGENT_BACKEND: {backend}")
    logger.info("")

    # Create storage using factory or legacy wrapper
    if storage_type != "json":
        # Use factory for non-default storage types
        logger.info(f"🔧 Creating {storage_type} storage via factory...")
        try:
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
    """Health check endpoint for container orchestration
    
    Returns comprehensive health information including:
    - Built-in MCP tools (provided by hub itself)
    - External MCP servers (registered by users)
    - Active storage sessions
    
    This allows proper distinction between:
    1. Hub's own tools (memory, server management) - always available
    2. User-registered MCP servers - optional external integrations
    """
    try:
        registry = get_registry()
        return JSONResponse(
            {
                "status": "ok",
                "service": "mcp-hub",
                "version": "1.0.0",
                "builtin_tools": {
                    "total": get_builtin_tools_count(),
                    "names": BUILTIN_TOOLS,
                },
                "registry": {
                    "servers_total": len(registry.get_all_servers()),
                    "servers_enabled": len(registry.get_enabled_servers()),
                },
                "storage": {
                    "active_users": len(_storages),
                },
                # Ready once registry initialized and discovered
                "ready": True,
            }
        )
    except Exception as e:
        logger.error(f"❌ Exception in health check endpoint: {e}", exc_info=True)
        return JSONResponse(
            {
                "status": "error",
                "service": "mcp-hub",
                "version": "1.0.0",
                "error": str(e),
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


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
# AICODE-NOTE: MCP server management tools removed from MCP tools interface.
# These tools are only for managing the MCP hub itself and should not be
# exposed as MCP tools. They remain available via HTTP API for administration.


# ============================================================================
# Registry HTTP API - For bot/docker integration without MCP client
# ============================================================================


@mcp.custom_route("/registry/servers", methods=["GET"])
async def http_list_servers(request: Request):
    """HTTP: List all registered MCP servers"""
    try:
        registry = get_registry()
        servers = registry.get_all_servers()
        return JSONResponse(
            {
                "success": True,
                "total": len(servers),
                "servers": [
                    {
                        "name": spec.name,
                        "description": spec.description,
                        "enabled": spec.enabled,
                        "command": spec.command,
                        "args": spec.args,
                        "env": spec.env or {},
                        "working_dir": spec.working_dir,
                    }
                    for spec in servers
                ],
            }
        )
    except Exception as e:
        logger.error(f"❌ Error in http_list_servers: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@mcp.custom_route("/registry/servers", methods=["POST"])
async def http_register_server(request: Request):
    """HTTP: Register a new MCP server from JSON body"""
    try:
        payload = await request.json()
        required = ["name", "description", "command", "args"]
        missing = [k for k in required if k not in payload]
        if missing:
            return JSONResponse(
                {"success": False, "error": f"Missing required fields: {', '.join(missing)}"},
                status_code=422,
            )

        registry = get_registry()
        spec = MCPServerSpec(
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            command=payload.get("command", ""),
            args=payload.get("args", []),
            env=payload.get("env"),
            working_dir=payload.get("working_dir"),
            enabled=payload.get("enabled", True),
        )

        success = registry.add_server(spec)
        if not success:
            return JSONResponse(
                {"success": False, "error": f"Server '{spec.name}' already exists"},
                status_code=409,
            )

        logger.info(f"✅ [HTTP] Registered server via API: {spec.name}")
        return JSONResponse(
            {"success": True, "message": f"Server '{spec.name}' registered successfully"},
            status_code=201,
        )
    except Exception as e:
        logger.error(f"❌ Error in http_register_server: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@mcp.custom_route("/registry/servers/{name}", methods=["GET"])
async def http_get_server(request: Request):
    """HTTP: Get a specific MCP server details"""
    try:
        name = request.path_params.get("name")
        registry = get_registry()
        spec = registry.get_server(name)
        if not spec:
            return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
        return JSONResponse(
            {
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
        )
    except Exception as e:
        logger.error(f"❌ Error in http_get_server: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@mcp.custom_route("/registry/servers/{name}/enable", methods=["POST"])
async def http_enable_server(request: Request):
    """HTTP: Enable a server by name"""
    try:
        name = request.path_params.get("name")
        registry = get_registry()
        if registry.enable_server(name):
            return JSONResponse({"success": True, "message": f"Server '{name}' enabled"})
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
    except Exception as e:
        logger.error(f"❌ Error in http_enable_server: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@mcp.custom_route("/registry/servers/{name}/disable", methods=["POST"])
async def http_disable_server(request: Request):
    """HTTP: Disable a server by name"""
    try:
        name = request.path_params.get("name")
        registry = get_registry()
        if registry.disable_server(name):
            return JSONResponse({"success": True, "message": f"Server '{name}' disabled"})
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
    except Exception as e:
        logger.error(f"❌ Error in http_disable_server: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@mcp.custom_route("/registry/servers/{name}", methods=["DELETE"])
async def http_remove_server(request: Request):
    """HTTP: Remove a server by name"""
    try:
        name = request.path_params.get("name")
        registry = get_registry()
        if registry.remove_server(name):
            return JSONResponse({"success": True, "message": f"Server '{name}' removed"})
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
    except Exception as e:
        logger.error(f"❌ Error in http_remove_server: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ============================================================================
# Configuration API - Dynamic Config Generation
# ============================================================================


@mcp.custom_route("/config/client/{client_type}", methods=["GET"])
async def http_get_client_config(request: Request):
    """
    HTTP: Get client configuration for a specific client type

    Supported client types:
    - standard: Standard MCP format (Cursor, Claude Desktop, Qwen CLI)
    - lmstudio: LM Studio specific format
    - openai: OpenAI-compatible format

    Query parameters:
    - format: json (default) or raw (for direct file download)
    """
    try:
        from src.mcp.universal_config_generator import UniversalMCPConfigGenerator

        client_type = request.path_params.get("client_type")
        format_type = request.query_params.get("format", "json")

        # Determine MCP Hub URL
        mcp_hub_url = os.getenv("MCP_HUB_URL")
        if not mcp_hub_url:
            # Use request host/port if available
            host = request.url.hostname or "127.0.0.1"
            port = request.url.port or 8765
            mcp_hub_url = f"http://{host}:{port}/sse"

        # Generate config
        generator = UniversalMCPConfigGenerator(
            user_id=None,
            http_port=request.url.port or 8765,
            mcp_hub_url=mcp_hub_url,
        )

        # Select appropriate config based on client type
        if client_type == "standard":
            config = generator.generate_standard_config()
        elif client_type == "lmstudio":
            config = generator.generate_lm_studio_config()
        elif client_type == "openai":
            config = generator.generate_openai_compatible_config()
        else:
            return JSONResponse(
                {
                    "success": False,
                    "error": f"Unknown client type: {client_type}. Supported: standard, lmstudio, openai",
                },
                status_code=400,
            )

        if format_type == "raw":
            # Return as downloadable file
            import json as json_module

            return JSONResponse(
                config,
                headers={
                    "Content-Disposition": f'attachment; filename="mcp-hub-{client_type}.json"'
                },
            )
        else:
            # Return as API response
            return JSONResponse({"success": True, "client_type": client_type, "config": config})

    except Exception as e:
        logger.error(f"❌ Error in http_get_client_config: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)



# ============================================================================
# Client Configuration Generation
# ============================================================================


def _generate_client_configs(host: str, port: int) -> None:
    """
    Generate MCP client configurations for various clients

    This is the MCP Hub's responsibility - it knows its URL and should
    generate configs for clients to connect to it.

    Args:
        host: Host the server is running on
        port: Port the server is running on
    """
    try:
        from src.mcp.qwen_config_generator import setup_qwen_mcp_config
        from src.mcp.universal_config_generator import UniversalMCPConfigGenerator

        # Determine MCP Hub URL based on environment
        mcp_hub_url = os.getenv("MCP_HUB_URL")
        if not mcp_hub_url:
            # Standalone mode - use the host and port we're binding to
            mcp_hub_url = f"http://{host}:{port}/sse"

        logger.info("📝 Generating client configurations...")
        logger.info(f"   MCP Hub URL: {mcp_hub_url}")

        # Generate Qwen CLI config
        logger.info("   Creating Qwen CLI config...")
        saved_paths = setup_qwen_mcp_config(
            user_id=None,
            kb_path=None,
            global_config=True,
            use_http=True,
            http_port=port,
            mcp_hub_url=mcp_hub_url,
        )
        logger.info(f"   ✓ Qwen CLI config: {saved_paths}")

        # Generate universal configs for other clients (only in standalone mode)
        if not os.getenv("MCP_HUB_URL"):
            logger.info("   Creating universal MCP configs...")
            universal_gen = UniversalMCPConfigGenerator(
                user_id=None,
                http_port=port,
                mcp_hub_url=mcp_hub_url,
            )
            data_config_path = universal_gen.save_for_data_directory()
            logger.info(f"   ✓ Universal config: {data_config_path}")
        else:
            logger.info("   Docker mode: Skipping universal config generation")

        logger.info("✓ Client configurations generated successfully")

    except Exception as e:
        logger.warning(f"⚠️  Failed to generate client configs (non-critical): {e}")
        logger.debug("Config generation error details:", exc_info=True)


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
    parser.add_argument(
        "--skip-config-gen",
        action="store_true",
        help="Skip client configuration generation on startup",
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
    # Display effective values from config.settings when available to avoid confusing "not set" logs
    try:
        from config import settings as app_settings

        logger.info("📋 Environment Variables (effective):")
        logger.info(f"  - MEM_AGENT_STORAGE_TYPE: {app_settings.MEM_AGENT_STORAGE_TYPE}")
        logger.info(f"  - MEM_AGENT_MODEL: {app_settings.MEM_AGENT_MODEL}")
        logger.info(f"  - MEM_AGENT_BACKEND: {app_settings.MEM_AGENT_BACKEND}")
        logger.info(f"  - MEM_AGENT_MAX_TOOL_TURNS: {app_settings.MEM_AGENT_MAX_TOOL_TURNS}")
    except Exception:
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

    # Generate client configurations (unless skipped)
    if not args.skip_config_gen:
        logger.info("")
        _generate_client_configs(args.host, args.port)
        logger.info("")
    else:
        logger.info("")
        logger.info("⏭️  Skipping client configuration generation (--skip-config-gen)")
        logger.info("")

    # Run server
    try:
        logger.info(f"🌐 Server listening on http://{args.host}:{args.port}/sse")
        logger.info(f"🏥 Health check: http://{args.host}:{args.port}/health")
        logger.info(f"📋 Registry API: http://{args.host}:{args.port}/registry/servers")
        mcp.run(transport="sse", host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("⏹️  Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
