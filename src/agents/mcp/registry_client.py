"""
MCP Registry Client

Connects MCP tools to the MCP servers registry.
Automatically discovers and connects to enabled MCP servers.
"""

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from src.mcp_registry import MCPServersManager, MCPServerSpec
from .client import MCPClient, MCPServerConfig


class MCPRegistryClient:
    """
    Client that connects to MCP servers discovered from the registry
    
    This class bridges the MCP servers registry with the agent's MCP client.
    It automatically discovers enabled servers and creates MCP clients for them.
    """
    
    def __init__(self, servers_dir: Optional[Path] = None):
        """
        Initialize registry client
        
        Args:
            servers_dir: Directory containing MCP server configs (default: data/mcp_servers)
        """
        self.manager = MCPServersManager(servers_dir)
        self.clients: Dict[str, MCPClient] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize by discovering available MCP servers"""
        if self._initialized:
            return
        
        logger.info("[MCPRegistryClient] Initializing MCP registry client")
        self.manager.initialize()
        self._initialized = True
    
    def get_enabled_servers(self) -> List[MCPServerSpec]:
        """
        Get all enabled MCP servers
        
        Returns:
            List of enabled server specs
        """
        if not self._initialized:
            self.initialize()
        
        return self.manager.get_enabled_servers()
    
    def create_client_for_server(self, spec: MCPServerSpec) -> Optional[MCPClient]:
        """
        Create an MCP client for a server spec
        
        Args:
            spec: Server specification
            
        Returns:
            MCP client or None if creation failed
        """
        try:
            # Convert server spec to MCP client config
            config = MCPServerConfig(
                command=spec.command,
                args=spec.args,
                env=spec.env,
                cwd=Path(spec.working_dir) if spec.working_dir else None
            )
            
            # Create and return client
            client = MCPClient(config)
            logger.debug(f"[MCPRegistryClient] Created client for server: {spec.name}")
            return client
            
        except Exception as e:
            logger.error(f"[MCPRegistryClient] Failed to create client for {spec.name}: {e}")
            return None
    
    async def connect_to_server(self, spec: MCPServerSpec) -> Optional[MCPClient]:
        """
        Connect to an MCP server
        
        Args:
            spec: Server specification
            
        Returns:
            Connected MCP client or None if connection failed
        """
        # Check if already connected
        if spec.name in self.clients:
            client = self.clients[spec.name]
            if client.is_connected:
                return client
        
        # Create new client
        client = self.create_client_for_server(spec)
        if not client:
            return None
        
        # Connect
        if await client.connect():
            self.clients[spec.name] = client
            logger.info(f"[MCPRegistryClient] ✓ Connected to server: {spec.name}")
            return client
        else:
            logger.warning(f"[MCPRegistryClient] Failed to connect to server: {spec.name}")
            return None
    
    async def connect_all_enabled(self) -> Dict[str, MCPClient]:
        """
        Connect to all enabled MCP servers
        
        Returns:
            Dict of server name -> connected client
        """
        if not self._initialized:
            self.initialize()
        
        enabled_servers = self.get_enabled_servers()
        
        if not enabled_servers:
            logger.info("[MCPRegistryClient] No enabled MCP servers found")
            return {}
        
        logger.info(f"[MCPRegistryClient] Connecting to {len(enabled_servers)} enabled servers...")
        
        connected = {}
        for spec in enabled_servers:
            client = await self.connect_to_server(spec)
            if client:
                connected[spec.name] = client
        
        logger.info(f"[MCPRegistryClient] Connected to {len(connected)} / {len(enabled_servers)} servers")
        return connected
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers"""
        for name, client in self.clients.items():
            try:
                await client.disconnect()
                logger.debug(f"[MCPRegistryClient] Disconnected from {name}")
            except Exception as e:
                logger.error(f"[MCPRegistryClient] Error disconnecting from {name}: {e}")
        
        self.clients.clear()
        logger.info("[MCPRegistryClient] Disconnected from all servers")
    
    def get_client(self, server_name: str) -> Optional[MCPClient]:
        """
        Get connected client by server name
        
        Args:
            server_name: Name of the server
            
        Returns:
            MCP client or None if not connected
        """
        return self.clients.get(server_name)
    
    def is_server_connected(self, server_name: str) -> bool:
        """
        Check if a server is connected
        
        Args:
            server_name: Name of the server
            
        Returns:
            True if connected, False otherwise
        """
        client = self.clients.get(server_name)
        return client is not None and client.is_connected