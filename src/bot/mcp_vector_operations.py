"""
MCP Vector Operations

Responsible for calling MCP Hub for vector search operations.
Handles all communication with MCP Hub service.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .mcp_hub_client import MCPHubClient, MCPHubError, MCPHubUnavailableError


class MCPVectorOperations:
    """
    Handles vector search operations via MCP Hub.
    
    Responsibilities:
    - Call MCP Hub for vector operations (reindex, add, delete, update)
    - Handle MCP Hub communication errors
    - Provide consistent interface for vector operations
    """
    
    def __init__(self, mcp_client: MCPHubClient):
        """
        Initialize MCP vector operations
        
        Args:
            mcp_client: MCP Hub client for communication
        """
        self.mcp_client = mcp_client
    
    async def reindex_documents(
        self, 
        documents: List[Dict[str, Any]], 
        force: bool = False,
        kb_id: str = "default",
        user_id: Optional[int] = None
    ) -> bool:
        """
        Reindex documents via MCP Hub
        
        Args:
            documents: List of documents to index
            force: Force reindexing even if index exists
            kb_id: Knowledge base ID
            user_id: User ID (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.mcp_client.vector_reindex(
                documents=documents,
                force=force,
                kb_id=kb_id,
                user_id=user_id,
            )
            
            if result.get("success"):
                logger.info("✅ MCP reindex completed successfully")
                return True
            else:
                logger.warning(f"⚠️ MCP reindex failed: {result.get('error')}")
                return False
                
        except MCPHubUnavailableError as e:
            logger.warning(f"⚠️ Vector search not available: {e}")
            return False
        except MCPHubError as e:
            logger.warning(f"⚠️ MCP reindex failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Exception during MCP reindex: {e}", exc_info=True)
            return False
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        kb_id: str = "default",
        user_id: Optional[int] = None
    ) -> bool:
        """
        Add documents via MCP Hub
        
        Args:
            documents: List of documents to add
            kb_id: Knowledge base ID
            user_id: User ID (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.mcp_client.vector_add_documents(
                documents=documents,
                kb_id=kb_id,
                user_id=user_id,
            )
            
            if result.get("success"):
                logger.info(f"✅ MCP add documents completed: {result.get('message')}")
                return True
            else:
                logger.warning(f"⚠️ MCP add documents failed: {result.get('error')}")
                return False
                
        except MCPHubUnavailableError as e:
            logger.warning(f"⚠️ Vector search not available: {e}")
            return False
        except MCPHubError as e:
            logger.warning(f"⚠️ MCP add documents failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Exception during MCP add documents: {e}", exc_info=True)
            return False
    
    async def delete_documents(
        self,
        document_ids: List[str],
        kb_id: str = "default",
        user_id: Optional[int] = None
    ) -> bool:
        """
        Delete documents via MCP Hub
        
        Args:
            document_ids: List of document IDs to delete
            kb_id: Knowledge base ID
            user_id: User ID (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.mcp_client.vector_delete_documents(
                document_ids=document_ids,
                kb_id=kb_id,
                user_id=user_id,
            )
            
            if result.get("success"):
                logger.info(f"✅ MCP delete documents completed: {result.get('message')}")
                return True
            else:
                logger.warning(f"⚠️ MCP delete documents failed: {result.get('error')}")
                return False
                
        except MCPHubUnavailableError as e:
            logger.warning(f"⚠️ Vector search not available: {e}")
            return False
        except MCPHubError as e:
            logger.warning(f"⚠️ MCP delete documents failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Exception during MCP delete documents: {e}", exc_info=True)
            return False
    
    async def update_documents(
        self,
        documents: List[Dict[str, Any]],
        kb_id: str = "default",
        user_id: Optional[int] = None
    ) -> bool:
        """
        Update documents via MCP Hub
        
        Args:
            documents: List of documents to update
            kb_id: Knowledge base ID
            user_id: User ID (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.mcp_client.vector_update_documents(
                documents=documents,
                kb_id=kb_id,
                user_id=user_id,
            )
            
            if result.get("success"):
                logger.info(f"✅ MCP update documents completed: {result.get('message')}")
                return True
            else:
                logger.warning(f"⚠️ MCP update documents failed: {result.get('error')}")
                return False
                
        except MCPHubUnavailableError as e:
            logger.warning(f"⚠️ Vector search not available: {e}")
            return False
        except MCPHubError as e:
            logger.warning(f"⚠️ MCP update documents failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Exception during MCP update documents: {e}", exc_info=True)
            return False
    
    async def check_availability(self) -> bool:
        """
        Check if vector search is available via MCP Hub
        
        Returns:
            True if available, False otherwise
        """
        try:
            health_data = await self.mcp_client.health_check()
            builtin_tools = health_data.get("builtin_tools", {})
            available_tools = builtin_tools.get("names", [])
            
            # Check if vector search tools are available
            required_tools = ["vector_search"]
            has_vector_search = all(tool in available_tools for tool in required_tools)
            
            if has_vector_search:
                logger.info("✅ Vector search tools are available")
                return True
            else:
                missing = [t for t in required_tools if t not in available_tools]
                available = ", ".join(available_tools) if available_tools else "none"
                logger.info(
                    f"ℹ️  Vector search tools not available. "
                    f"Missing: {', '.join(missing)}. "
                    f"Available tools: {available}"
                )
                return False
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to check vector search availability: {e}")
            return False