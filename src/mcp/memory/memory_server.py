#!/usr/bin/env python3
"""
Standalone MCP Server for Memory Storage

This server runs as a separate process and provides memory storage/retrieval tools
via the Model Context Protocol (MCP).

Can be run as:
- Subprocess from qwen CLI (via .qwen/settings.json)
- Docker container (future)
- Standalone daemon

Usage:
    python -m src.mcp.memory.memory_server [--user-id USER_ID]
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.mcp.memory.memory_factory import MemoryStorageFactory

# Import shared memory storage and factory
from src.mcp.memory.memory_storage import MemoryStorage

# Configure logger for standalone mode
logger.remove()

# Console logging (stderr)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
)

# File logging for errors and debugging
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    log_dir / "memory_mcp.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)

# Separate error log for critical issues
logger.add(
    log_dir / "memory_mcp_errors.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)


class MemoryMCPServer:
    """MCP Server for memory storage"""

    def __init__(self, user_id: Optional[int] = None):
        """
        Initialize MCP server

        Args:
            user_id: User ID for per-user storage (required)
        """
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING MCP MEMORY SERVER (STDIO)")
        logger.info("=" * 80)

        # User-specific storage directory
        # Each user must have their own isolated memory
        if not user_id:
            logger.error("❌ user_id is required for memory storage")
            raise ValueError(
                "user_id is required for memory storage. Shared memory is not allowed."
            )

        self.user_id = user_id
        logger.info(f"✓ User ID: {user_id}")

        # Use isolated tmp dir during pytest, otherwise use data/memory/user_{user_id}
        if os.getenv("PYTEST_CURRENT_TEST"):
            data_dir = Path(tempfile.mkdtemp(prefix=f"memsrv_user_{user_id}_"))
            logger.info(f"🧪 Test mode: Using temporary directory")
        else:
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
        logger.info(
            f"  - MEM_AGENT_MAX_TOOL_TURNS: {os.getenv('MEM_AGENT_MAX_TOOL_TURNS', '20 (default)')}"
        )
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

                self.storage = MemoryStorageFactory.create(
                    storage_type=storage_type,
                    data_dir=data_dir,
                    model_name=model_name,
                    backend=backend,
                )
                logger.info(f"✅ Successfully created {storage_type} storage")
            except Exception as e:
                logger.error(f"❌ Failed to create {storage_type} storage: {e}", exc_info=True)
                logger.warning("⚠️  Falling back to JSON storage")
                self.storage = MemoryStorage(data_dir)
        else:
            # Use legacy wrapper for JSON (default)
            logger.info("🔧 Creating JSON storage (default)...")
            self.storage = MemoryStorage(data_dir)
            logger.info("✅ JSON storage created successfully")

        logger.info("")
        logger.info("✅ MCP Memory Server initialized successfully")
        logger.info("=" * 80)

    async def handle_list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools

        Returns:
            List of tool schemas
        """
        return [
            {
                "name": "store_memory",
                "description": "Store information in memory for later retrieval",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Content to store in memory"},
                        "category": {
                            "type": "string",
                            "description": "Category for organization (e.g., 'tasks', 'notes', 'ideas')",
                            "default": "general",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags for categorization",
                            "default": [],
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional metadata (optional)",
                            "default": {},
                        },
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "retrieve_memory",
                "description": "Retrieve information from memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (optional - returns all if not specified)",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category (optional)",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags (optional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "list_categories",
                "description": "List all memory categories with counts",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
        ]

    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Call a tool

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result as MCP content
        """
        logger.info("=" * 60)
        logger.info(f"🔧 TOOL CALL: {name}")
        logger.info(f"📥 Arguments: {json.dumps(arguments, ensure_ascii=False, indent=2)}")

        try:
            if name == "store_memory":
                logger.info("💾 Executing store_memory...")
                logger.debug(f"  Content length: {len(arguments.get('content', ''))} chars")
                logger.debug(f"  Category: {arguments.get('category', 'general')}")
                logger.debug(f"  Tags: {arguments.get('tags', [])}")

                result = self.storage.store(
                    content=arguments.get("content", ""),
                    category=arguments.get("category", "general"),
                    tags=arguments.get("tags"),
                    metadata=arguments.get("metadata"),
                )
                logger.info(f"✅ Store successful: {result.get('id', 'N/A')}")
                logger.debug(f"📤 Result: {json.dumps(result, ensure_ascii=False)}")

            elif name == "retrieve_memory":
                logger.info("🔍 Executing retrieve_memory...")
                logger.debug(f"  Query: {arguments.get('query', 'all')}")
                logger.debug(f"  Category: {arguments.get('category', 'any')}")
                logger.debug(f"  Limit: {arguments.get('limit', 10)}")

                result = self.storage.retrieve(
                    query=arguments.get("query"),
                    category=arguments.get("category"),
                    tags=arguments.get("tags"),
                    limit=arguments.get("limit", 10),
                )
                count = result.get("count", 0)
                logger.info(f"✅ Retrieve successful: found {count} memories")
                if count > 0:
                    logger.debug(
                        f"📤 First result preview: {str(result.get('memories', [{}])[0])[:200]}..."
                    )

            elif name == "list_categories":
                logger.info("📋 Executing list_categories...")
                result = self.storage.list_categories()
                categories = result.get("categories", [])
                # categories is a list of {name,count} dicts in JsonMemoryStorage
                num_categories = len(categories) if isinstance(categories, list) else 0
                logger.info(f"✅ Categories retrieved: {num_categories} categories")
                try:
                    category_names = (
                        [c.get("name") for c in categories] if isinstance(categories, list) else []
                    )
                    logger.debug(f"📤 Categories: {category_names}")
                except Exception:
                    pass

            else:
                logger.warning(f"❌ Unknown tool requested: {name}")
                result = {"success": False, "error": f"Unknown tool: {name}"}

            # Return as MCP content
            response = [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]
            logger.info(f"📤 Response prepared (length: {len(response[0]['text'])} chars)")
            logger.info("=" * 60)
            return response

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ TOOL EXECUTION ERROR: {name}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error(f"Arguments were: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
            logger.error("=" * 60, exc_info=True)

            error_result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "tool": name,
            }
            return [{"type": "text", "text": json.dumps(error_result)}]

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP request

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.info(f"📨 Request received: method={method}, id={request_id}")
        logger.debug(f"  Params: {json.dumps(params, ensure_ascii=False)}")

        try:
            # Handle initialization
            if method == "initialize":
                logger.info(f"🔄 Initializing MCP server (request_id={request_id})")
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "memory", "version": "1.0.0"},
                }
                logger.info(f"✅ Initialization complete")

            # Handle tools/list
            elif method == "tools/list":
                logger.info(f"📋 Listing tools (request_id={request_id})")
                tools = await self.handle_list_tools()
                result = {"tools": tools}
                logger.info(f"✅ Returned {len(tools)} tools")

            # Handle tools/call
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                logger.info(f"🔧 Calling tool '{tool_name}' (request_id={request_id})")
                content = await self.handle_call_tool(tool_name, arguments)
                result = {"content": content}
                logger.info(f"✅ Tool '{tool_name}' completed successfully")

            else:
                logger.warning(f"❌ Unknown method '{method}' (request_id={request_id})")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

            logger.debug(f"📤 Sending response for request_id={request_id}")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        except Exception as e:
            logger.error(f"❌ Request handling error for method '{method}': {e}", exc_info=True)
            logger.error(f"Request params: {json.dumps(params, ensure_ascii=False, indent=2)}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                    "data": {"error_type": type(e).__name__},
                },
            }

    async def run(self):
        """
        Run the MCP server (stdio transport)

        Reads JSON-RPC requests from stdin, sends responses to stdout
        """
        logger.info("=" * 60)
        logger.info("MCP Memory Server started (stdio transport)")
        logger.info("=" * 60)
        logger.info(f"Ready to accept requests for user_id={self.user_id}")
        logger.info(f"Storage type: {os.getenv('MEM_AGENT_STORAGE_TYPE', 'json')}")
        logger.info(f"Backend: {os.getenv('MEM_AGENT_BACKEND', 'auto')}")
        logger.info(f"Model: {os.getenv('MEM_AGENT_MODEL', 'default')}")
        logger.info("=" * 60)

        # Send initialization notification
        init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        print(json.dumps(init_notification), flush=True)

        # Process requests from stdin
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)

                    # Handle notification (no response needed)
                    if "id" not in request:
                        logger.debug(f"Notification: {request.get('method')}")
                        continue

                    # Handle request
                    response = await self.handle_request(request)

                    # Send response to stdout
                    print(json.dumps(response), flush=True)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"Request processing error: {e}", exc_info=True)

        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            logger.info("MCP Server stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Memory MCP Server - Memory storage and retrieval via MCP"
    )
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

    # Create and run server
    server = MemoryMCPServer(user_id=args.user_id)

    try:
        asyncio.run(server.run())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
