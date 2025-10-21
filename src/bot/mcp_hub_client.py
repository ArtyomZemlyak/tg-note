"""
Unified HTTP Client for MCP Hub Communication

This module provides a centralized HTTP client for all communication between
the bot container and the MCP Hub server. It eliminates boilerplate code
and provides consistent error handling, logging, and configuration.

Features:
- Unified API for all HTTP operations (GET, POST, PUT, DELETE)
- Centralized timeout and retry configuration
- Consistent error handling and logging
- Type-safe response handling
- Support for different MCP Hub endpoints (vector search, registry, health)

Usage:
    client = MCPHubClient("http://mcp-hub:8765")
    
    # Vector search operations
    result = await client.vector_reindex(documents, force=True)
    result = await client.vector_add_documents(documents)
    result = await client.vector_delete_documents(document_ids)
    result = await client.vector_update_documents(documents)
    
    # Registry operations
    servers = await client.registry_list_servers()
    await client.registry_register_server(server_config)
    await client.registry_enable_server(server_name)
    
    # Health check
    health = await client.health_check()
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import aiohttp
from loguru import logger

from config import settings


class MCPHubError(Exception):
    """Base exception for MCP Hub communication errors"""
    pass


class MCPHubTimeoutError(MCPHubError):
    """Timeout error for MCP Hub operations"""
    pass


class MCPHubUnavailableError(MCPHubError):
    """MCP Hub service unavailable error"""
    pass


class MCPHubClient:
    """
    Unified HTTP client for MCP Hub communication
    
    Provides a centralized interface for all HTTP operations between
    the bot container and the MCP Hub server.
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: Optional[float] = None,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize MCP Hub client
        
        Args:
            base_url: Base URL of MCP Hub server (e.g., "http://mcp-hub:8765")
            timeout: Request timeout in seconds (default: settings.MCP_TIMEOUT)
            retry_attempts: Number of retry attempts for failed requests
            retry_delay: Delay between retry attempts in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or settings.MCP_TIMEOUT
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Session will be created on first use
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"🔗 MCP Hub client initialized: {self.base_url}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.debug("📡 Created new aiohttp session")
        return self._session
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("📡 Closed aiohttp session")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/vector/reindex")
            json_data: JSON payload for request body
            params: Query parameters
            expected_status: Expected HTTP status code
            
        Returns:
            Parsed JSON response
            
        Raises:
            MCPHubError: For various HTTP and communication errors
            MCPHubTimeoutError: For timeout errors
            MCPHubUnavailableError: For service unavailable errors
        """
        url = urljoin(self.base_url, endpoint)
        session = await self._get_session()
        
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"🌐 {method} {url} (attempt {attempt + 1}/{self.retry_attempts})")
                
                async with session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                ) as response:
                    # Log response status
                    logger.debug(f"📊 Response: {response.status}")
                    
                    # Handle different status codes
                    if response.status == expected_status:
                        try:
                            result = await response.json()
                            logger.debug(f"✅ Request successful: {method} {endpoint}")
                            return result
                        except json.JSONDecodeError as e:
                            error_text = await response.text()
                            raise MCPHubError(f"Invalid JSON response: {e}. Response: {error_text}")
                    
                    elif response.status == 503:
                        error_text = await response.text()
                        logger.warning(f"⚠️ Service unavailable (503): {error_text}")
                        raise MCPHubUnavailableError(f"Service unavailable: {error_text}")
                    
                    elif response.status == 404:
                        error_text = await response.text()
                        logger.warning(f"⚠️ Not found (404): {error_text}")
                        raise MCPHubError(f"Endpoint not found: {error_text}")
                    
                    else:
                        error_text = await response.text()
                        logger.warning(f"⚠️ HTTP {response.status}: {error_text}")
                        raise MCPHubError(f"HTTP {response.status}: {error_text}")
            
            except asyncio.TimeoutError as e:
                last_error = MCPHubTimeoutError(f"Request timeout: {e}")
                logger.warning(f"⏰ Timeout on attempt {attempt + 1}: {e}")
            
            except aiohttp.ClientError as e:
                last_error = MCPHubError(f"HTTP client error: {e}")
                logger.warning(f"🌐 Client error on attempt {attempt + 1}: {e}")
            
            except MCPHubUnavailableError:
                # Don't retry service unavailable errors
                raise
            
            except MCPHubError as e:
                # Don't retry other MCP Hub errors
                raise
            
            except Exception as e:
                last_error = MCPHubError(f"Unexpected error: {e}")
                logger.warning(f"❌ Unexpected error on attempt {attempt + 1}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.retry_attempts - 1:
                logger.debug(f"⏳ Waiting {self.retry_delay}s before retry...")
                await asyncio.sleep(self.retry_delay)
        
        # All retries failed
        logger.error(f"❌ All {self.retry_attempts} attempts failed for {method} {endpoint}")
        raise last_error or MCPHubError("All retry attempts failed")
    
    # ============================================================================
    # Health Check
    # ============================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check MCP Hub health status
        
        Returns:
            Health status information
        """
        logger.info("🏥 Checking MCP Hub health...")
        return await self._make_request("GET", "/health")
    
    # ============================================================================
    # Vector Search API
    # ============================================================================
    
    async def vector_reindex(
        self,
        documents: List[Dict[str, Any]],
        force: bool = False,
        kb_id: str = "default",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Reindex knowledge base for vector search
        
        Args:
            documents: List of documents to index
            force: Force reindexing even if index exists
            kb_id: Knowledge base ID
            user_id: User ID (optional)
            
        Returns:
            Reindexing results
        """
        logger.info(f"🔄 Vector reindex: {len(documents)} documents, force={force}")
        
        payload = {
            "documents": documents,
            "force": force,
            "kb_id": kb_id,
        }
        if user_id is not None:
            payload["user_id"] = user_id
        
        return await self._make_request("POST", "/vector/reindex", json_data=payload)
    
    async def vector_add_documents(
        self,
        documents: List[Dict[str, Any]],
        kb_id: str = "default",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Add documents to vector search index
        
        Args:
            documents: List of documents to add
            kb_id: Knowledge base ID
            user_id: User ID (optional)
            
        Returns:
            Addition results
        """
        logger.info(f"➕ Vector add documents: {len(documents)} documents")
        
        payload = {
            "documents": documents,
            "kb_id": kb_id,
        }
        if user_id is not None:
            payload["user_id"] = user_id
        
        return await self._make_request("POST", "/vector/documents", json_data=payload)
    
    async def vector_delete_documents(
        self,
        document_ids: List[str],
        kb_id: str = "default",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Delete documents from vector search index
        
        Args:
            document_ids: List of document IDs to delete
            kb_id: Knowledge base ID
            user_id: User ID (optional)
            
        Returns:
            Deletion results
        """
        logger.info(f"🗑️ Vector delete documents: {len(document_ids)} documents")
        
        payload = {
            "document_ids": document_ids,
            "kb_id": kb_id,
        }
        if user_id is not None:
            payload["user_id"] = user_id
        
        return await self._make_request("DELETE", "/vector/documents", json_data=payload)
    
    async def vector_update_documents(
        self,
        documents: List[Dict[str, Any]],
        kb_id: str = "default",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update documents in vector search index
        
        Args:
            documents: List of documents to update
            kb_id: Knowledge base ID
            user_id: User ID (optional)
            
        Returns:
            Update results
        """
        logger.info(f"🔄 Vector update documents: {len(documents)} documents")
        
        payload = {
            "documents": documents,
            "kb_id": kb_id,
        }
        if user_id is not None:
            payload["user_id"] = user_id
        
        return await self._make_request("PUT", "/vector/documents", json_data=payload)
    
    # ============================================================================
    # Registry API
    # ============================================================================
    
    async def registry_list_servers(self) -> Dict[str, Any]:
        """
        List all registered MCP servers
        
        Returns:
            List of servers
        """
        logger.info("📋 Registry list servers")
        return await self._make_request("GET", "/registry/servers")
    
    async def registry_register_server(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new MCP server
        
        Args:
            server_config: Server configuration
            
        Returns:
            Registration results
        """
        logger.info(f"➕ Registry register server: {server_config.get('name', 'unknown')}")
        return await self._make_request("POST", "/registry/servers", json_data=server_config)
    
    async def registry_get_server(self, server_name: str) -> Dict[str, Any]:
        """
        Get specific server details
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server details
        """
        logger.info(f"📄 Registry get server: {server_name}")
        return await self._make_request("GET", f"/registry/servers/{server_name}")
    
    async def registry_enable_server(self, server_name: str) -> Dict[str, Any]:
        """
        Enable a server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Enable results
        """
        logger.info(f"✅ Registry enable server: {server_name}")
        return await self._make_request("POST", f"/registry/servers/{server_name}/enable")
    
    async def registry_disable_server(self, server_name: str) -> Dict[str, Any]:
        """
        Disable a server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Disable results
        """
        logger.info(f"❌ Registry disable server: {server_name}")
        return await self._make_request("POST", f"/registry/servers/{server_name}/disable")
    
    async def registry_remove_server(self, server_name: str) -> Dict[str, Any]:
        """
        Remove a server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Removal results
        """
        logger.info(f"🗑️ Registry remove server: {server_name}")
        return await self._make_request("DELETE", f"/registry/servers/{server_name}")
    
    # ============================================================================
    # Configuration API
    # ============================================================================
    
    async def get_client_config(self, client_type: str, format_type: str = "json") -> Dict[str, Any]:
        """
        Get client configuration
        
        Args:
            client_type: Type of client (standard, lmstudio, openai)
            format_type: Format type (json, raw)
            
        Returns:
            Client configuration
        """
        logger.info(f"⚙️ Get client config: {client_type}")
        params = {"format": format_type} if format_type != "json" else None
        return await self._make_request("GET", f"/config/client/{client_type}", params=params)


# ============================================================================
# Convenience functions for backward compatibility
# ============================================================================

async def create_mcp_hub_client(base_url: str) -> MCPHubClient:
    """
    Create MCP Hub client with default settings
    
    Args:
        base_url: Base URL of MCP Hub server
        
    Returns:
        Configured MCP Hub client
    """
    return MCPHubClient(base_url)


async def check_mcp_hub_health(base_url: str, timeout: float = 10.0) -> bool:
    """
    Check if MCP Hub is healthy
    
    Args:
        base_url: Base URL of MCP Hub server
        timeout: Timeout in seconds
        
    Returns:
        True if healthy, False otherwise
    """
    try:
        async with MCPHubClient(base_url, timeout=timeout) as client:
            health = await client.health_check()
            return health.get("status") == "ok"
    except Exception as e:
        logger.warning(f"⚠️ MCP Hub health check failed: {e}")
        return False