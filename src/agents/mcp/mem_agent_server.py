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
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

# Configure logger for standalone mode
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


class MemoryStorage:
    """Simple file-based memory storage"""
    
    def __init__(self, data_dir: Path):
        """
        Initialize memory storage
        
        Args:
            data_dir: Directory for storing memory files
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.data_dir / "memory.json"
        
        # Load existing memory
        self.memories: List[Dict[str, Any]] = []
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
                logger.info(f"Loaded {len(self.memories)} memories from {self.memory_file}")
            except Exception as e:
                logger.error(f"Failed to load memories: {e}")
    
    def _save(self) -> None:
        """Save memories to file"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")
    
    def store(self, content: str, category: str = "general", metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Store information in memory
        
        Args:
            content: Content to store
            category: Category for organization
            metadata: Additional metadata
            
        Returns:
            Result with memory ID
        """
        memory_id = len(self.memories) + 1
        
        memory = {
            "id": memory_id,
            "content": content,
            "category": category,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.memories.append(memory)
        self._save()
        
        logger.info(f"Stored memory #{memory_id} in category '{category}'")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"Memory stored successfully (ID: {memory_id})"
        }
    
    def retrieve(self, query: Optional[str] = None, category: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Retrieve information from memory
        
        Args:
            query: Search query (simple substring match)
            category: Filter by category
            limit: Maximum number of results
            
        Returns:
            List of matching memories
        """
        results = self.memories.copy()
        
        # Filter by category
        if category:
            results = [m for m in results if m.get("category") == category]
        
        # Filter by query (simple substring search)
        if query:
            query_lower = query.lower()
            results = [
                m for m in results
                if query_lower in m.get("content", "").lower()
                or query_lower in m.get("category", "").lower()
            ]
        
        # Limit results
        results = results[-limit:]  # Get last N results
        
        logger.info(f"Retrieved {len(results)} memories (query='{query}', category='{category}')")
        
        return {
            "success": True,
            "count": len(results),
            "memories": results
        }
    
    def list_categories(self) -> Dict[str, Any]:
        """
        List all available categories
        
        Returns:
            List of categories with counts
        """
        categories: Dict[str, int] = {}
        
        for memory in self.memories:
            cat = memory.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "success": True,
            "categories": [
                {"name": cat, "count": count}
                for cat, count in sorted(categories.items())
            ]
        }


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
        if user_id:
            data_dir = Path(f"data/memory/user_{user_id}")
        else:
            data_dir = Path("data/memory/shared")
        
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
                    metadata=arguments.get("metadata")
                )
            
            elif name == "retrieve_memory":
                result = self.storage.retrieve(
                    query=arguments.get("query"),
                    category=arguments.get("category"),
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