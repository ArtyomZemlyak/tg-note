#!/usr/bin/env python3
"""
Standalone MCP Server for mem-agent

This server runs as a separate process and provides memory storage/retrieval tools
via the Model Context Protocol (MCP).

Can be run as:
- Subprocess from qwen CLI (via .qwen/settings.json)
- Docker container (future)
- Standalone daemon

Usage:
    python -m src.agents.mcp.mem_agent_server [--user-id USER_ID]
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

# Import shared memory storage
from src.mem_agent.storage import MemoryStorage

# Configure logger for standalone mode
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


class MemAgentMCPServer:
    """MCP Server for mem-agent"""
    
    def __init__(self, user_id: Optional[int] = None):
        """
        Initialize MCP server
        
        Args:
            user_id: Optional user ID for per-user storage
        """
        self.user_id = user_id
        
        # Setup storage directory
        # Priority:
        # 1. KB_PATH env var (set by memory_agent_tool.py for user-specific KB)
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
        
        # MemoryStorage will create the directory automatically
        self.storage = MemoryStorage(data_dir)
        
        logger.info(f"MCP Server initialized (user_id={user_id}, data_dir={data_dir})")
    
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
                        "content": {
                            "type": "string",
                            "description": "Content to store in memory"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category for organization (e.g., 'tasks', 'notes', 'ideas')",
                            "default": "general"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags for categorization",
                            "default": []
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional metadata (optional)",
                            "default": {}
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "retrieve_memory",
                "description": "Retrieve information from memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (optional - returns all if not specified)"
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category (optional)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "list_categories",
                "description": "List all memory categories with counts",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
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
                result = self.storage.store(
                    content=arguments.get("content", ""),
                    category=arguments.get("category", "general"),
                    tags=arguments.get("tags"),
                    metadata=arguments.get("metadata")
                )
            
            elif name == "retrieve_memory":
                result = self.storage.retrieve(
                    query=arguments.get("query"),
                    category=arguments.get("category"),
                    tags=arguments.get("tags"),
                    limit=arguments.get("limit", 10)
                )
            
            elif name == "list_categories":
                result = self.storage.list_categories()
            
            else:
                result = {
                    "success": False,
                    "error": f"Unknown tool: {name}"
                }
            
            # Return as MCP content
            return [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }
            ]
        
        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            return [
                {
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": str(e)
                    })
                }
            ]
    
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
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "mem-agent",
                        "version": "1.0.0"
                    }
                }
            
            # Handle tools/list
            elif method == "tools/list":
                tools = await self.handle_list_tools()
                result = {"tools": tools}
            
            # Handle tools/call
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                content = await self.handle_call_tool(tool_name, arguments)
                result = {"content": content}
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        
        except Exception as e:
            logger.error(f"Request handling error: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def run(self):
        """
        Run the MCP server (stdio transport)
        
        Reads JSON-RPC requests from stdin, sends responses to stdout
        """
        logger.info("MCP Server started (stdio transport)")
        logger.info(f"Ready to accept requests for user_id={self.user_id}")
        
        # Send initialization notification
        init_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
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
        description="Mem-agent MCP Server - Memory storage and retrieval via MCP"
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
    
    # Create and run server
    server = MemAgentMCPServer(user_id=args.user_id)
    
    try:
        asyncio.run(server.run())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()