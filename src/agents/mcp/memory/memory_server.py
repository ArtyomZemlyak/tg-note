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
    python -m src.agents.mcp.memory.memory_server [--user-id USER_ID]
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

from src.agents.mcp.memory.memory_factory import MemoryStorageFactory

# Import shared memory storage and factory
from src.agents.mcp.memory.memory_storage import MemoryStorage

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
            user_id: Optional user ID for per-user storage
        """
        self.user_id = user_id

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
            # Legacy: user_id-based path (use isolated tmp dir during pytest)
            if os.getenv("PYTEST_CURRENT_TEST"):
                data_dir = Path(tempfile.mkdtemp(prefix=f"memsrv_user_{user_id}_"))
            else:
                data_dir = Path(f"data/memory/user_{user_id}")
            logger.info(f"Using legacy user-based memory path: {data_dir}")
        else:
            # Fallback: shared memory
            data_dir = Path("data/memory/shared")
            logger.info(f"Using shared memory path: {data_dir}")

        # Get storage type from environment (default: json)
        # Can be "json", "vector", or "mem-agent"
        storage_type = os.getenv("MEM_AGENT_STORAGE_TYPE", "json")

        # Create storage using factory or legacy wrapper
        if storage_type != "json":
            # Use factory for non-default storage types
            try:
                model_name = os.getenv("MEM_AGENT_MODEL", None)
                use_vllm = os.getenv("MEM_AGENT_USE_VLLM", "true").lower() == "true"

                self.storage = MemoryStorageFactory.create(
                    storage_type=storage_type,
                    data_dir=data_dir,
                    model_name=model_name,
                    use_vllm=use_vllm,
                )
                logger.info(f"Created {storage_type} storage via factory")
            except Exception as e:
                logger.warning(
                    f"Failed to create {storage_type} storage: {e}. Falling back to json."
                )
                self.storage = MemoryStorage(data_dir)
        else:
            # Use legacy wrapper for JSON (default)
            self.storage = MemoryStorage(data_dir)

        logger.info(
            f"MCP Server initialized (user_id={user_id}, storage_type={storage_type}, data_dir={data_dir})"
        )

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
        logger.info(f"Tool call: {name} with args: {arguments}")

        try:
            if name == "store_memory":
                logger.debug(f"Executing store_memory with args: {arguments}")
                result = self.storage.store(
                    content=arguments.get("content", ""),
                    category=arguments.get("category", "general"),
                    tags=arguments.get("tags"),
                    metadata=arguments.get("metadata"),
                )
                logger.debug(f"Store result: {result}")

            elif name == "retrieve_memory":
                logger.debug(f"Executing retrieve_memory with args: {arguments}")
                result = self.storage.retrieve(
                    query=arguments.get("query"),
                    category=arguments.get("category"),
                    tags=arguments.get("tags"),
                    limit=arguments.get("limit", 10),
                )
                logger.debug(f"Retrieve result count: {result.get('count', 0)}")

            elif name == "list_categories":
                logger.debug(f"Executing list_categories")
                result = self.storage.list_categories()
                logger.debug(f"Categories result: {result}")

            else:
                logger.warning(f"Unknown tool requested: {name}")
                result = {"success": False, "error": f"Unknown tool: {name}"}

            # Return as MCP content
            return [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]

        except Exception as e:
            logger.error(f"Tool execution error for {name}: {e}", exc_info=True)
            logger.error(f"Arguments were: {arguments}")
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

        logger.debug(f"Request: method={method}, id={request_id}")

        try:
            # Handle initialization
            if method == "initialize":
                logger.info(f"Initializing MCP server (request_id={request_id})")
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mem-agent", "version": "1.0.0"},
                }

            # Handle tools/list
            elif method == "tools/list":
                logger.debug(f"Listing tools (request_id={request_id})")
                tools = await self.handle_list_tools()
                result = {"tools": tools}

            # Handle tools/call
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                logger.info(f"Calling tool '{tool_name}' (request_id={request_id})")
                content = await self.handle_call_tool(tool_name, arguments)
                result = {"content": content}

            else:
                logger.warning(f"Unknown method '{method}' (request_id={request_id})")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        except Exception as e:
            logger.error(f"Request handling error for method '{method}': {e}", exc_info=True)
            logger.error(f"Request params: {params}")
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
        logger.info("MCP Server started (stdio transport)")
        logger.info(f"Ready to accept requests for user_id={self.user_id}")

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
