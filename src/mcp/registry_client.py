"""
MCP Registry Client

Connects MCP tools to the MCP servers registry.
Automatically discovers and connects to enabled MCP servers.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from src.mcp.registry import MCPServersManager, MCPServerSpec

from .client import MCPClient, MCPServerConfig


class MCPRegistryClient:
    """
    Client that connects to MCP servers discovered from the registry

    This class bridges the MCP servers registry with the agent's MCP client.
    It automatically discovers enabled servers and creates MCP clients for them.
    """

    def __init__(self, servers_dir: Optional[Path] = None, user_id: Optional[int] = None):
        """
        Initialize registry client

        Args:
            servers_dir: Directory containing MCP server configs (default: data/mcp_servers)
            user_id: Optional user ID for per-user server discovery
        """
        self.user_id = user_id
        self.manager = MCPServersManager(servers_dir, user_id=user_id)
        self.clients: Dict[str, MCPClient] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize by discovering available MCP servers"""
        if self._initialized:
            return

        user_info = f" for user {self.user_id}" if self.user_id else ""
        logger.info(f"[MCPRegistryClient] Initializing MCP registry client{user_info}")
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
            # Check if this is HTTP/SSE transport (look for URL in spec)
            # First check if config file has URL
            config_url = None
            if spec.config_file and spec.config_file.exists():
                try:
                    with open(spec.config_file, "r") as f:
                        config_data = json.load(f)
                        # Extract URL from mcpServers section
                        servers = config_data.get("mcpServers", {})
                        if spec.name in servers:
                            config_url = servers[spec.name].get("url")
                except:
                    pass
                    
            # Create config based on transport type
            if config_url:
                # HTTP/SSE transport
                config = MCPServerConfig(
                    transport="sse",
                    url=config_url,
                )
                logger.debug(f"[MCPRegistryClient] Created HTTP/SSE client for: {spec.name}")
            else:
                # stdio transport
                config = MCPServerConfig(
                    command=spec.command,
                    args=spec.args,
                    env=spec.env,
                    cwd=Path(spec.working_dir) if spec.working_dir else None,
                    transport="stdio",
                )
                logger.debug(f"[MCPRegistryClient] Created stdio client for: {spec.name}")

            # Create and return client
            client = MCPClient(config)
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
        try:
            if await client.connect():
                self.clients[spec.name] = client
                logger.info(f"[MCPRegistryClient] ✓ Connected to server: {spec.name}")
                return client
            else:
                logger.warning(
                    f"[MCPRegistryClient] Failed to connect to server: {spec.name}. "
                    f"Check if the server command '{spec.command}' is available and the server is running."
                )
                return None
        except Exception as e:
            logger.error(
                f"[MCPRegistryClient] Error connecting to server {spec.name}: {e}", exc_info=True
            )
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

        logger.info(
            f"[MCPRegistryClient] Connected to {len(connected)} / {len(enabled_servers)} servers"
        )
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
