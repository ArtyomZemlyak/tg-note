"""
MCP Servers Manager

High-level interface for managing MCP servers.
Integrates with the agent system and provides lifecycle management.
"""

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .registry import MCPServerRegistry, MCPServerSpec


class MCPServersManager:
    """
    Manager for MCP servers
    
    Provides high-level interface for:
    - Discovering and loading MCP servers
    - Enabling/disabling servers
    - Adding custom MCP servers
    - Integration with agent tools
    """
    
    def __init__(self, servers_dir: Optional[Path] = None, user_id: Optional[int] = None):
        """
        Initialize MCP servers manager
        
        Args:
            servers_dir: Directory containing MCP server configs (default: data/mcp_servers)
            user_id: Optional user ID for per-user server discovery
        """
        if servers_dir is None:
            servers_dir = Path("data/mcp_servers")
        
        self.servers_dir = servers_dir
        self.user_id = user_id
        self.registry = MCPServerRegistry(servers_dir, user_id=user_id)
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the manager by discovering available servers"""
        if self._initialized:
            return
        
        user_info = f" for user {self.user_id}" if self.user_id else ""
        logger.info(f"[MCPManager] Initializing MCP servers manager{user_info}")
        self.registry.discover_servers()
        self._initialized = True
        
        # Log summary
        all_servers = self.registry.get_all_servers()
        enabled_servers = self.registry.get_enabled_servers()
        logger.info(
            f"[MCPManager] Discovered {len(all_servers)} servers, "
            f"{len(enabled_servers)} enabled{user_info}"
        )
    
    def get_enabled_servers(self) -> List[MCPServerSpec]:
        """
        Get all enabled MCP servers
        
        Returns:
            List of enabled server specs
        """
        if not self._initialized:
            self.initialize()
        
        return self.registry.get_enabled_servers()
    
    def get_all_servers(self) -> List[MCPServerSpec]:
        """
        Get all registered MCP servers
        
        Returns:
            List of all server specs
        """
        if not self._initialized:
            self.initialize()
        
        return self.registry.get_all_servers()
    
    def get_server(self, name: str) -> Optional[MCPServerSpec]:
        """
        Get server by name
        
        Args:
            name: Server name
            
        Returns:
            Server spec or None if not found
        """
        if not self._initialized:
            self.initialize()
        
        return self.registry.get_server(name)
    
    def enable_server(self, name: str) -> bool:
        """
        Enable an MCP server
        
        Args:
            name: Server name
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            self.initialize()
        
        return self.registry.enable_server(name)
    
    def disable_server(self, name: str) -> bool:
        """
        Disable an MCP server
        
        Args:
            name: Server name
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            self.initialize()
        
        return self.registry.disable_server(name)
    
    def add_server_from_json(self, json_content: str, name: Optional[str] = None) -> bool:
        """
        Add a new MCP server from JSON content
        
        This is useful for allowing users to upload MCP server configurations.
        
        Args:
            json_content: JSON configuration as string
            name: Optional server name (if not provided, extracted from JSON)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            self.initialize()
        
        import json
        
        try:
            # Parse JSON
            data = json.loads(json_content)
            
            # Create spec
            spec = MCPServerSpec.from_dict(data)
            
            # Override name if provided
            if name:
                spec.name = name
            
            # Add to registry
            return self.registry.add_server(spec)
            
        except json.JSONDecodeError as e:
            logger.error(f"[MCPManager] Invalid JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"[MCPManager] Failed to add server: {e}")
            return False
    
    def remove_server(self, name: str) -> bool:
        """
        Remove an MCP server
        
        Args:
            name: Server name
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            self.initialize()
        
        return self.registry.remove_server(name)
    
    def get_servers_summary(self) -> Dict[str, int]:
        """
        Get a summary of registered servers
        
        Returns:
            Dict with counts of total and enabled servers
        """
        if not self._initialized:
            self.initialize()
        
        all_servers = self.registry.get_all_servers()
        enabled_servers = self.registry.get_enabled_servers()
        
        return {
            "total": len(all_servers),
            "enabled": len(enabled_servers),
            "disabled": len(all_servers) - len(enabled_servers),
        }