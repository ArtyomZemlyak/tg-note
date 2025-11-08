"""
MCP Server Registry

Manages registration and discovery of MCP servers from JSON configuration files.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class MCPServerSpec:
    """
    Specification for an MCP server

    Attributes:
        name: Server name (unique identifier)
        description: Human-readable description
        command: Command to execute the server
        args: Command-line arguments
        env: Environment variables (optional)
        working_dir: Working directory (optional)
        enabled: Whether the server is enabled
        config_file: Path to the JSON config file
    """

    name: str
    description: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    working_dir: Optional[str] = None
    enabled: bool = True
    transport: str = "stdio"
    url: Optional[str] = None
    timeout: Optional[int] = None
    config_file: Optional[Path] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_file: Optional[Path] = None) -> "MCPServerSpec":
        """Create MCPServerSpec from dictionary"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            command=data.get("command", ""),
            args=data.get("args", []) or [],
            env=data.get("env"),
            working_dir=data.get("working_dir"),
            enabled=data.get("enabled", True),
            transport=data.get("transport", data.get("mode", "stdio")),
            url=data.get("url"),
            timeout=data.get("timeout"),
            config_file=config_file,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "transport": self.transport,
        }
        if self.transport == "stdio":
            result["command"] = self.command
            result["args"] = self.args
            if self.env:
                result["env"] = self.env
            if self.working_dir:
                result["working_dir"] = self.working_dir
        elif self.transport == "sse":
            if self.url:
                result["url"] = self.url
        else:
            # Preserve any unknown transport details
            if self.command:
                result["command"] = self.command
            if self.args:
                result["args"] = self.args
            if self.env:
                result["env"] = self.env
            if self.working_dir:
                result["working_dir"] = self.working_dir

        if self.env:
            result["env"] = self.env
        if self.working_dir:
            result["working_dir"] = self.working_dir
        if self.timeout is not None:
            result["timeout"] = self.timeout
        if self.url and self.transport != "sse":
            result["url"] = self.url
        return result


class MCPServerRegistry:
    """
    Registry for MCP servers

    Discovers and manages MCP servers from JSON configuration files.
    Configuration files should be placed in the servers_dir (default: data/mcp_servers/).

    JSON format:
    {
        "name": "server-name",
        "description": "Server description",
        "command": "python3",
        "args": ["-m", "package.server"],
        "env": {
            "VAR_NAME": "value"
        },
        "working_dir": "/path/to/dir",
        "enabled": true
    }
    """

    def __init__(self, servers_dir: Path, user_id: Optional[int] = None):
        """
        Initialize registry

        Args:
            servers_dir: Directory containing MCP server JSON configs
            user_id: Optional user ID for per-user server discovery
        """
        self.servers_dir = Path(servers_dir)
        self.user_id = user_id
        self.servers: Dict[str, MCPServerSpec] = {}

        # Ensure servers directory exists
        self.servers_dir.mkdir(parents=True, exist_ok=True)

    def discover_servers(self) -> None:
        """
        Discover all MCP servers from JSON configuration files

        Scans the servers_dir for *.json files and loads them as server specs.
        If user_id is set, also scans user-specific directory.

        Discovery order:
        1. Shared servers in servers_dir/ (e.g., data/mcp_servers/)
        2. User-specific servers in servers_dir/user_{user_id}/ (if user_id is set)

        User-specific servers override shared servers with the same name.
        """
        logger.info(f"[MCPRegistry] Discovering MCP servers in {self.servers_dir}")

        # Discover shared servers
        self._discover_from_directory(self.servers_dir, scope="shared")

        # Discover user-specific servers if user_id is set
        if self.user_id is not None:
            user_dir = self.servers_dir / f"user_{self.user_id}"
            if user_dir.exists():
                logger.info(
                    f"[MCPRegistry] Discovering user-specific MCP servers for user {self.user_id}"
                )
                self._discover_from_directory(user_dir, scope=f"user_{self.user_id}")
            else:
                logger.debug(
                    f"[MCPRegistry] No user-specific servers directory for user {self.user_id}"
                )

    def _discover_from_directory(self, directory: Path, scope: str) -> None:
        """
        Discover servers from a specific directory

        Args:
            directory: Directory to scan for JSON configs
            scope: Scope label for logging (e.g., 'shared', 'user_123')
        """
        if not directory.exists():
            logger.debug(f"[MCPRegistry] Directory does not exist: {directory}")
            return

        # Find all JSON files (non-recursive)
        json_files = list(directory.glob("*.json"))

        if not json_files:
            logger.debug(f"[MCPRegistry] No MCP server configuration files in {directory}")
            return

        # Load each JSON file
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Skip client-style configs that use the standard MCP client format
                # {"mcpServers": {"server-name": { ... }}}
                if isinstance(data, dict) and "mcpServers" in data:
                    logger.info(
                        f"[MCPRegistry] Skipping {json_file}: detected client config format ('mcpServers')"
                    )
                    continue

                # Create server spec
                spec = MCPServerSpec.from_dict(data, config_file=json_file)

                # Validate spec
                if not spec.name:
                    logger.warning(f"[MCPRegistry] Skipping {json_file}: missing 'name' field")
                    continue

                # Normalise transport type
                transport = (spec.transport or "stdio").lower()

                if transport not in {"stdio", "sse"}:
                    logger.warning(
                        f"[MCPRegistry] Skipping {json_file}: unsupported transport '{spec.transport}'"
                    )
                    continue

                if transport == "stdio":
                    if not spec.command:
                        logger.warning(
                            f"[MCPRegistry] Skipping {json_file}: missing 'command' field for stdio transport"
                        )
                        continue
                elif transport == "sse":
                    if not spec.url:
                        if spec.enabled:
                            logger.warning(
                                f"[MCPRegistry] Skipping {json_file}: enabled SSE server missing 'url'"
                            )
                            continue
                        logger.info(
                            f"[MCPRegistry] Loaded disabled SSE server '{spec.name}' without URL (scope={scope})"
                        )

                # Register server (user-specific servers override shared ones)
                if spec.name in self.servers:
                    logger.info(
                        f"[MCPRegistry] Overriding server '{spec.name}' with {scope} version"
                    )
                spec.transport = transport
                self.servers[spec.name] = spec
                status = "enabled" if spec.enabled else "disabled"
                logger.info(
                    f"[MCPRegistry] ✓ Registered server: {spec.name} "
                    f"(transport={transport}, {status}, scope={scope})"
                )

            except json.JSONDecodeError as e:
                logger.error(f"[MCPRegistry] Failed to parse {json_file}: {e}")
            except Exception as e:
                logger.error(f"[MCPRegistry] Failed to load {json_file}: {e}")

    def get_server(self, name: str) -> Optional[MCPServerSpec]:
        """
        Get server spec by name

        Args:
            name: Server name

        Returns:
            Server spec or None if not found
        """
        return self.servers.get(name)

    def get_enabled_servers(self) -> List[MCPServerSpec]:
        """
        Get all enabled servers

        Returns:
            List of enabled server specs
        """
        return [spec for spec in self.servers.values() if spec.enabled]

    def get_all_servers(self) -> List[MCPServerSpec]:
        """
        Get all registered servers

        Returns:
            List of all server specs
        """
        return list(self.servers.values())

    def enable_server(self, name: str) -> bool:
        """
        Enable a server

        Args:
            name: Server name

        Returns:
            True if successful, False otherwise
        """
        spec = self.servers.get(name)
        if not spec:
            logger.warning(f"[MCPRegistry] Server not found: {name}")
            return False

        spec.enabled = True
        self._save_server_config(spec)
        logger.info(f"[MCPRegistry] Enabled server: {name}")
        return True

    def disable_server(self, name: str) -> bool:
        """
        Disable a server

        Args:
            name: Server name

        Returns:
            True if successful, False otherwise
        """
        spec = self.servers.get(name)
        if not spec:
            logger.warning(f"[MCPRegistry] Server not found: {name}")
            return False

        spec.enabled = False
        self._save_server_config(spec)
        logger.info(f"[MCPRegistry] Disabled server: {name}")
        return True

    def add_server(self, spec: MCPServerSpec) -> bool:
        """
        Add a new server to the registry

        Args:
            spec: Server specification

        Returns:
            True if successful, False otherwise
        """
        if spec.name in self.servers:
            logger.warning(f"[MCPRegistry] Server already exists: {spec.name}")
            return False

        # Create config file path
        config_file = self.servers_dir / f"{spec.name}.json"
        spec.config_file = config_file

        # Save to file
        self._save_server_config(spec)

        # Add to registry
        self.servers[spec.name] = spec
        logger.info(f"[MCPRegistry] Added server: {spec.name}")
        return True

    def remove_server(self, name: str) -> bool:
        """
        Remove a server from the registry

        Args:
            name: Server name

        Returns:
            True if successful, False otherwise
        """
        spec = self.servers.get(name)
        if not spec:
            logger.warning(f"[MCPRegistry] Server not found: {name}")
            return False

        # Remove config file
        if spec.config_file and spec.config_file.exists():
            spec.config_file.unlink()

        # Remove from registry
        del self.servers[name]
        logger.info(f"[MCPRegistry] Removed server: {name}")
        return True

    def _save_server_config(self, spec: MCPServerSpec) -> None:
        """
        Save server configuration to JSON file

        Args:
            spec: Server specification
        """
        if not spec.config_file:
            spec.config_file = self.servers_dir / f"{spec.name}.json"

        try:
            with open(spec.config_file, "w", encoding="utf-8") as f:
                json.dump(spec.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"[MCPRegistry] Saved config: {spec.config_file}")
        except Exception as e:
            logger.error(f"[MCPRegistry] Failed to save config for {spec.name}: {e}")
