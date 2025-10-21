"""
Vector Search HTTP Tool - Knowledge Base Vector Search

This tool provides vector search capabilities for the knowledge base via HTTP API.
The agent can use it to:
- Perform semantic search in the knowledge base
- Reindex knowledge base for vector search

This integrates the vector search functionality through HTTP endpoints.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

import httpx
from loguru import logger

from ..base_mcp_tool import BaseMCPTool
from ..client import MCPServerConfig


class VectorSearchHTTPTool:
    """
    Vector Search HTTP Tool - Semantic Search in Knowledge Base

    This tool provides semantic vector search capabilities for the knowledge base via HTTP API.
    The agent can use it to find relevant information using natural language queries.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize HTTP tool
        
        Args:
            base_url: Base URL for MCP hub server (default: auto-detect)
        """
        self.base_url = base_url or self._get_base_url()

    def _get_base_url(self) -> str:
        """Get MCP hub base URL from configuration or environment"""
        # Prefer explicit MCP_HUB_URL in Docker mode
        mcp_hub_url = os.getenv("MCP_HUB_URL")
        if mcp_hub_url:
            # Convert SSE URL to HTTP base URL
            if mcp_hub_url.endswith("/sse"):
                return mcp_hub_url[:-4]  # Remove /sse suffix
            return mcp_hub_url

        # Try to load from config file
        config_file = Path("data/mcp_servers/mcp-hub.json")
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                mcp_servers = config_data.get("mcpServers", {})
                hub_config = mcp_servers.get("mcp-hub")

                if hub_config and "url" in hub_config:
                    url = hub_config["url"]
                    if url.endswith("/sse"):
                        return url[:-4]  # Remove /sse suffix
                    return url
            except Exception as e:
                logger.warning(f"Failed to load config from {config_file}: {e}")

        # Default fallback
        return "http://127.0.0.1:8765"

    async def search(self, query: str, top_k: int = 5, user_id: int = None, kb_id: str = "default") -> Dict[str, Any]:
        """
        Perform semantic vector search

        Args:
            query: Search query
            top_k: Number of results to return
            user_id: User ID (optional)
            kb_id: Knowledge base ID

        Returns:
            Dict with search results
        """
        if not query:
            return {"success": False, "error": "Query is required"}

        payload = {
            "query": query,
            "top_k": top_k,
            "kb_id": kb_id,
        }
        
        if user_id:
            payload["user_id"] = user_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/vector/search",
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in vector search: {e}")
            return {"success": False, "error": f"HTTP error: {e}"}
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return {"success": False, "error": str(e)}

    async def reindex(self, documents: list = None, force: bool = False, user_id: int = None, kb_id: str = "default") -> Dict[str, Any]:
        """
        Reindex knowledge base for vector search

        Args:
            documents: List of documents to index
            force: Force reindexing
            user_id: User ID (optional)
            kb_id: Knowledge base ID

        Returns:
            Dict with reindexing results
        """
        payload = {
            "force": force,
            "kb_id": kb_id,
        }
        
        if documents:
            payload["documents"] = documents
        if user_id:
            payload["user_id"] = user_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/vector/reindex",
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in vector reindex: {e}")
            return {"success": False, "error": f"HTTP error: {e}"}
        except Exception as e:
            logger.error(f"Error in vector reindex: {e}")
            return {"success": False, "error": str(e)}

    async def add_documents(self, documents: list, user_id: int = None, kb_id: str = "default") -> Dict[str, Any]:
        """
        Add documents to vector search index

        Args:
            documents: List of documents to add
            user_id: User ID (optional)
            kb_id: Knowledge base ID

        Returns:
            Dict with operation results
        """
        payload = {
            "documents": documents,
            "kb_id": kb_id,
        }
        
        if user_id:
            payload["user_id"] = user_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/vector/documents",
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in add documents: {e}")
            return {"success": False, "error": f"HTTP error: {e}"}
        except Exception as e:
            logger.error(f"Error in add documents: {e}")
            return {"success": False, "error": str(e)}

    async def delete_documents(self, document_ids: list, user_id: int = None, kb_id: str = "default") -> Dict[str, Any]:
        """
        Delete documents from vector search index

        Args:
            document_ids: List of document IDs to delete
            user_id: User ID (optional)
            kb_id: Knowledge base ID

        Returns:
            Dict with operation results
        """
        payload = {
            "document_ids": document_ids,
            "kb_id": kb_id,
        }
        
        if user_id:
            payload["user_id"] = user_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/vector/documents",
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in delete documents: {e}")
            return {"success": False, "error": f"HTTP error: {e}"}
        except Exception as e:
            logger.error(f"Error in delete documents: {e}")
            return {"success": False, "error": str(e)}

    async def update_documents(self, documents: list, user_id: int = None, kb_id: str = "default") -> Dict[str, Any]:
        """
        Update documents in vector search index

        Args:
            documents: List of documents to update
            user_id: User ID (optional)
            kb_id: Knowledge base ID

        Returns:
            Dict with operation results
        """
        payload = {
            "documents": documents,
            "kb_id": kb_id,
        }
        
        if user_id:
            payload["user_id"] = user_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/vector/documents",
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in update documents: {e}")
            return {"success": False, "error": f"HTTP error: {e}"}
        except Exception as e:
            logger.error(f"Error in update documents: {e}")
            return {"success": False, "error": str(e)}


class VectorSearchMCPTool(BaseMCPTool):
    """
    Vector Search MCP Tool - Semantic Search in Knowledge Base

    This tool provides semantic vector search capabilities for the knowledge base.
    The agent can use it to find relevant information using natural language queries.
    """

    def __init__(self, base_url: str = None):
        super().__init__()
        self.http_tool = VectorSearchHTTPTool(base_url)

    @property
    def name(self) -> str:
        return "kb_vector_search"

    @property
    def description(self) -> str:
        return (
            "Semantic vector search in knowledge base. "
            "Use this tool to search for relevant information using natural language queries. "
            "This performs AI-powered semantic search that understands meaning, not just keywords."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - describe what you're looking for in natural language",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """Not used for HTTP-based tool"""
        return None

    @property
    def mcp_tool_name(self) -> str:
        """Not used for HTTP-based tool"""
        return None

    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute vector search via HTTP

        Args:
            params: Search parameters (query, top_k)
            context: Tool execution context

        Returns:
            Dict with search results
        """
        query = params.get("query", "")
        top_k = params.get("top_k", 5)

        if not query:
            return {"success": False, "error": "Query is required"}

        # Get user_id and kb_id from context if available
        user_id = getattr(context, "user_id", None)
        kb_id = getattr(context, "kb_id", "default")

        # Use HTTP tool for search
        result = await self.http_tool.search(
            query=query, 
            top_k=top_k, 
            user_id=user_id, 
            kb_id=kb_id
        )

        # Add helpful information to the result
        if result.get("success"):
            result["message"] = f"Vector search completed for: {query}"

        return result


class VectorReindexMCPTool(BaseMCPTool):
    """
    Vector Reindex MCP Tool - Reindex Knowledge Base

    This tool reindexes the knowledge base for vector search via HTTP API.
    """

    def __init__(self, base_url: str = None):
        super().__init__()
        self.http_tool = VectorSearchHTTPTool(base_url)

    @property
    def name(self) -> str:
        return "kb_reindex_vector"

    @property
    def description(self) -> str:
        return (
            "Reindex knowledge base for vector search. "
            "Use this tool when the knowledge base has been updated and needs to be reindexed. "
            "This rebuilds the vector index for semantic search."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Force reindexing even if index exists (default: false)",
                    "default": False,
                },
                "documents": {
                    "type": "array",
                    "description": "List of documents to index (optional)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "content": {"type": "string"},
                            "metadata": {"type": "object"}
                        },
                        "required": ["id", "content"]
                    }
                },
            },
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """Not used for HTTP-based tool"""
        return None

    @property
    def mcp_tool_name(self) -> str:
        """Not used for HTTP-based tool"""
        return None

    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute vector reindexing via HTTP

        Args:
            params: Reindex parameters (force, documents)
            context: Tool execution context

        Returns:
            Dict with reindexing results
        """
        force = params.get("force", False)
        documents = params.get("documents")

        # Get user_id and kb_id from context if available
        user_id = getattr(context, "user_id", None)
        kb_id = getattr(context, "kb_id", "default")

        # Use HTTP tool for reindexing
        result = await self.http_tool.reindex(
            documents=documents,
            force=force,
            user_id=user_id,
            kb_id=kb_id
        )

        # Add helpful information to the result
        if result.get("success"):
            result["message"] = "Knowledge base reindexing completed"

        return result


class VectorAddDocumentsMCPTool(BaseMCPTool):
    """
    Vector Add Documents MCP Tool - Add Documents to Vector Index

    This tool adds documents to the vector search index via HTTP API.
    """

    def __init__(self, base_url: str = None):
        super().__init__()
        self.http_tool = VectorSearchHTTPTool(base_url)

    @property
    def name(self) -> str:
        return "kb_add_vector_documents"

    @property
    def description(self) -> str:
        return (
            "Add documents to vector search index. "
            "Use this tool to add new documents to the knowledge base vector index. "
            "Documents will be chunked and embedded for semantic search."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "description": "List of documents to add",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique document identifier"},
                            "content": {"type": "string", "description": "Document text content"},
                            "metadata": {"type": "object", "description": "Additional metadata (optional)"}
                        },
                        "required": ["id", "content"]
                    }
                },
            },
            "required": ["documents"],
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """Not used for HTTP-based tool"""
        return None

    @property
    def mcp_tool_name(self) -> str:
        """Not used for HTTP-based tool"""
        return None

    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute add documents via HTTP

        Args:
            params: Add parameters (documents)
            context: Tool execution context

        Returns:
            Dict with operation results
        """
        documents = params.get("documents", [])

        if not documents:
            return {"success": False, "error": "Documents are required"}

        # Get user_id and kb_id from context if available
        user_id = getattr(context, "user_id", None)
        kb_id = getattr(context, "kb_id", "default")

        # Use HTTP tool for adding documents
        result = await self.http_tool.add_documents(
            documents=documents,
            user_id=user_id,
            kb_id=kb_id
        )

        # Add helpful information to the result
        if result.get("success"):
            stats = result.get("stats", {})
            result["message"] = f"Successfully added {stats.get('documents_processed', 0)} documents"

        return result


class VectorDeleteDocumentsMCPTool(BaseMCPTool):
    """
    Vector Delete Documents MCP Tool - Delete Documents from Vector Index

    This tool deletes documents from the vector search index via HTTP API.
    """

    def __init__(self, base_url: str = None):
        super().__init__()
        self.http_tool = VectorSearchHTTPTool(base_url)

    @property
    def name(self) -> str:
        return "kb_delete_vector_documents"

    @property
    def description(self) -> str:
        return (
            "Delete documents from vector search index. "
            "Use this tool to remove documents from the knowledge base vector index. "
            "Documents will be permanently removed from semantic search."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_ids": {
                    "type": "array",
                    "description": "List of document IDs to delete",
                    "items": {"type": "string"}
                },
            },
            "required": ["document_ids"],
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """Not used for HTTP-based tool"""
        return None

    @property
    def mcp_tool_name(self) -> str:
        """Not used for HTTP-based tool"""
        return None

    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute delete documents via HTTP

        Args:
            params: Delete parameters (document_ids)
            context: Tool execution context

        Returns:
            Dict with operation results
        """
        document_ids = params.get("document_ids", [])

        if not document_ids:
            return {"success": False, "error": "Document IDs are required"}

        # Get user_id and kb_id from context if available
        user_id = getattr(context, "user_id", None)
        kb_id = getattr(context, "kb_id", "default")

        # Use HTTP tool for deleting documents
        result = await self.http_tool.delete_documents(
            document_ids=document_ids,
            user_id=user_id,
            kb_id=kb_id
        )

        # Add helpful information to the result
        if result.get("success"):
            stats = result.get("stats", {})
            result["message"] = f"Successfully deleted {stats.get('documents_deleted', 0)} documents"

        return result


class VectorUpdateDocumentsMCPTool(BaseMCPTool):
    """
    Vector Update Documents MCP Tool - Update Documents in Vector Index

    This tool updates documents in the vector search index via HTTP API.
    """

    def __init__(self, base_url: str = None):
        super().__init__()
        self.http_tool = VectorSearchHTTPTool(base_url)

    @property
    def name(self) -> str:
        return "kb_update_vector_documents"

    @property
    def description(self) -> str:
        return (
            "Update documents in vector search index. "
            "Use this tool to update existing documents in the knowledge base vector index. "
            "Documents will be re-chunked and re-embedded for semantic search."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "description": "List of documents to update",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique document identifier"},
                            "content": {"type": "string", "description": "Document text content"},
                            "metadata": {"type": "object", "description": "Additional metadata (optional)"}
                        },
                        "required": ["id", "content"]
                    }
                },
            },
            "required": ["documents"],
        }

    @property
    def mcp_server_config(self) -> MCPServerConfig:
        """Not used for HTTP-based tool"""
        return None

    @property
    def mcp_tool_name(self) -> str:
        """Not used for HTTP-based tool"""
        return None

    async def execute(self, params: Dict[str, Any], context: "ToolContext") -> Dict[str, Any]:
        """
        Execute update documents via HTTP

        Args:
            params: Update parameters (documents)
            context: Tool execution context

        Returns:
            Dict with operation results
        """
        documents = params.get("documents", [])

        if not documents:
            return {"success": False, "error": "Documents are required"}

        # Get user_id and kb_id from context if available
        user_id = getattr(context, "user_id", None)
        kb_id = getattr(context, "kb_id", "default")

        # Use HTTP tool for updating documents
        result = await self.http_tool.update_documents(
            documents=documents,
            user_id=user_id,
            kb_id=kb_id
        )

        # Add helpful information to the result
        if result.get("success"):
            stats = result.get("stats", {})
            result["message"] = f"Successfully updated {stats.get('documents_updated', 0)} documents"

        return result


# Export all vector search tools for agents
# AICODE-NOTE: All vector search operations are now HTTP-based
ALL_TOOLS = [
    VectorSearchMCPTool(),
    VectorReindexMCPTool(),
    VectorAddDocumentsMCPTool(),
    VectorDeleteDocumentsMCPTool(),
    VectorUpdateDocumentsMCPTool(),
]
