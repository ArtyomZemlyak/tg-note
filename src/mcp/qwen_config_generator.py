"""
Qwen CLI MCP Configuration Generator

Generates .qwen/settings.json configuration for qwen CLI to connect to MCP servers.
Supports both per-user and shared MCP servers.

Transport Modes:
- HTTP/SSE (default): Uses Server-Sent Events over HTTP for better compatibility
- STDIO (legacy): Uses stdio-based JSON-RPC communication

Default: HTTP/SSE mode (use_http=True)
For STDIO mode, set use_http=False
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class QwenMCPConfigGenerator:
    """Generator for qwen CLI MCP configuration"""

    def __init__(
        self,
        user_id: Optional[int] = None,
        use_http: bool = True,
        http_port: int = 8765,
        mcp_hub_url: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
    ):
        """
        Initialize config generator

        Args:
            user_id: Optional user ID for per-user MCP servers
            use_http: Use HTTP/SSE transport instead of stdio (default: True)
            http_port: Port for HTTP server (default: 8765)
            mcp_hub_url: Custom MCP Hub URL (for Docker environments). If not provided, auto-detected.
            available_tools: List of available tools (if None, will be auto-detected)
        """
        self.user_id = user_id
        self.use_http = use_http
        self.http_port = http_port
        self.mcp_hub_url = mcp_hub_url
        self.available_tools = available_tools
        # Project root directory (tg-note repository root)
        # __file__ = src/mcp/qwen_config_generator.py → parent (mcp) → parent (src) → parent (repo root)
        self.project_root = Path(__file__).parent.parent.parent.resolve()

        # Auto-detect Docker environment if URL not provided
        if self.use_http and self.mcp_hub_url is None:
            self.mcp_hub_url = self._detect_mcp_hub_url()

        # Auto-detect available tools if not provided
        if self.available_tools is None:
            self.available_tools = self._detect_available_tools()

    def generate_config(self) -> Dict:
        """
        Generate qwen CLI MCP configuration

        Returns:
            Configuration dict with mcpServers
        """
        config: Dict[str, Any] = {"mcpServers": {}}

        # Add MCP Hub server configuration (single canonical name)
        memory_config = self._generate_memory_config()
        if memory_config:
            config["mcpServers"]["mcp-hub"] = memory_config

        # Add other MCP servers here in the future
        # config["mcpServers"]["filesystem"] = ...
        # config["mcpServers"]["web-search"] = ...

        # Add allowMCPServers list
        if config["mcpServers"]:
            servers: List[str] = list(config["mcpServers"].keys())
            config["allowMCPServers"] = servers

        return config

    def _detect_available_tools(self) -> List[str]:
        """
        Detect available MCP tools based on current configuration

        Returns:
            List of available tool names
        """
        try:
            # Try to import and call get_builtin_tools from mcp_hub_server
            # This ensures we always use the current available tools
            import sys
            from pathlib import Path

            # Add src to path if not already there
            src_path = str(Path(__file__).parent.parent.resolve())
            if src_path not in sys.path:
                sys.path.insert(0, src_path)

            # Try to import - this may fail if fastmcp/starlette not installed
            try:
                from mcp.mcp_hub_server import get_builtin_tools

                tools = get_builtin_tools()
                logger.info(f"[QwenMCPConfig] Detected {len(tools)} available tools: {tools}")
                return tools
            except ImportError as import_err:
                logger.warning(
                    f"[QwenMCPConfig] Cannot import mcp_hub_server (missing dependencies: {import_err}). "
                    f"Using fallback tool list. Install with: pip install fastmcp"
                )
                # Fallback to basic memory tools when mcp_hub_server can't be imported
                return ["store_memory", "retrieve_memory", "list_categories"]
        except Exception as e:
            logger.warning(f"[QwenMCPConfig] Failed to detect available tools: {e}")
            # Fallback to basic memory tools
            return ["store_memory", "retrieve_memory", "list_categories"]

    def _detect_mcp_hub_url(self) -> str:
        """
        Detect MCP Hub URL based on environment

        Returns:
            MCP Hub URL (Docker internal or localhost)
        """
        import os

        # Prefer explicit environment first to ensure deterministic tests
        mcp_hub_env = os.getenv("MCP_HUB_URL")
        if mcp_hub_env:
            logger.info(f"[QwenMCPConfig] Using MCP_HUB_URL from environment: {mcp_hub_env}")
            return mcp_hub_env

        # Default: assume host environment for deterministic behavior in tests/CI
        logger.info("[QwenMCPConfig] Using localhost (host environment)")
        return f"http://127.0.0.1:{self.http_port}/sse"

    def _generate_memory_config(self) -> Optional[Dict]:
        """
        Generate configuration for memory MCP server

        Returns:
            Server configuration or None if not available
        """
        # Build tools description
        tools_desc = ", ".join(self.available_tools) if self.available_tools else "various tools"

        # Use HTTP/SSE transport
        if self.use_http:
            return {
                "url": self.mcp_hub_url,
                "timeout": 99999,
                "trust": True,
                "description": (
                    f"MCP Hub - Unified MCP gateway (HTTP/SSE). "
                    f"Provides built-in tools: {tools_desc}"
                ),
                "tools": self.available_tools or [],
            }

        # Use stdio transport (default)
        # Path to memory server script (relative to project root)
        server_script = self.project_root / "src" / "mcp" / "memory" / "memory_server.py"

        if not server_script.exists():
            logger.warning(f"Memory server script not found: {server_script}")
            return None

        # Use python3 command with relative path to script (relative to cwd)
        # This allows the configuration to work on any system where the project is located
        args_list: List[str] = [str(server_script.relative_to(self.project_root).as_posix())]

        # Add user-id argument if specified
        if self.user_id:
            args_list.extend(["--user-id", str(self.user_id)])

        config: Dict[str, Any] = {
            "command": "python3",
            "args": args_list,
            "cwd": str(self.project_root),
            "timeout": 99999,  # ~100 seconds
            "trust": True,  # Trust our own server
            "description": f"MCP Hub - Unified MCP gateway. Provides: {', '.join(self.available_tools) if self.available_tools else 'various tools'}",
            "tools": self.available_tools or [],
        }

        return config

    def save_to_qwen_dir(self, qwen_dir: Optional[Path] = None) -> Path:
        """
        Save configuration to ~/.qwen/settings.json

        Args:
            qwen_dir: Optional custom qwen directory (default: ~/.qwen)

        Returns:
            Path to saved configuration file
        """
        # Use default qwen directory if not specified
        if qwen_dir is None:
            qwen_dir = Path.home() / ".qwen"

        # Create directory if needed
        qwen_dir.mkdir(parents=True, exist_ok=True)

        # Generate configuration
        config = self.generate_config()

        # Path to settings file
        settings_file = qwen_dir / "settings.json"

        # ALWAYS regenerate to ensure tools are up to date
        # Load existing settings if present
        existing_config = {}
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)
                logger.info(
                    f"Loaded existing qwen config from {settings_file} (will update with current tools)"
                )
            except Exception as e:
                logger.warning(f"Failed to load existing config: {e}")

        # Merge configurations (our MCP servers take precedence)
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}

        existing_config["mcpServers"].update(config.get("mcpServers", {}))

        # Update allowMCPServers
        existing_allowed = set(existing_config.get("allowMCPServers", []))
        new_allowed = set(config.get("allowMCPServers", []))
        existing_config["allowMCPServers"] = list(existing_allowed | new_allowed)

        # Save merged configuration
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved qwen MCP config to {settings_file}")
        logger.info(f"Configured MCP servers: {list(config.get('mcpServers', {}).keys())}")

        return settings_file

    def get_config_json(self) -> str:
        """
        Get configuration as JSON string

        Returns:
            JSON string
        """
        config = self.generate_config()
        return json.dumps(config, indent=2, ensure_ascii=False)


def setup_qwen_mcp_config(
    user_id: Optional[int] = None,
    use_http: bool = True,
    http_port: int = 8765,
    mcp_hub_url: Optional[str] = None,
    available_tools: Optional[List[str]] = None,
) -> Path:
    """
    Setup qwen MCP configuration

    This is a convenience function that:
    1. Generates MCP server configuration
    2. Saves to global ~/.qwen/settings.json

    Args:
        user_id: Optional user ID for per-user MCP servers
        use_http: Use HTTP/SSE transport instead of stdio (default: True)
        http_port: Port for HTTP server (default: 8765)
        mcp_hub_url: Custom MCP Hub URL (for Docker environments). If not provided, auto-detected.
        available_tools: List of available tools (if None, will be auto-detected)

    Returns:
        Path to saved configuration file
    """
    generator = QwenMCPConfigGenerator(
        user_id=user_id,
        use_http=use_http,
        http_port=http_port,
        mcp_hub_url=mcp_hub_url,
        available_tools=available_tools,
    )

    # Always save to global ~/.qwen/settings.json
    return generator.save_to_qwen_dir()


def main():
    """CLI entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate qwen CLI MCP configuration")
    parser.add_argument("--user-id", type=int, help="User ID for per-user MCP servers")
    parser.add_argument(
        "--output", type=Path, help="Output file path (default: ~/.qwen/settings.json)"
    )
    parser.add_argument(
        "--print", action="store_true", help="Print configuration to stdout instead of saving"
    )
    parser.add_argument(
        "--http", action="store_true", help="Use HTTP/SSE transport instead of stdio"
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="Port for HTTP server (default: 8765)"
    )
    parser.add_argument("--url", type=str, help="Custom MCP Hub URL (for Docker environments)")

    args = parser.parse_args()

    generator = QwenMCPConfigGenerator(
        user_id=args.user_id, use_http=args.http, http_port=args.port, mcp_hub_url=args.url
    )

    if args.print:
        # Just print the configuration
        print(generator.get_config_json())
    else:
        # Save configuration
        if args.output:
            qwen_dir = args.output.parent
            generator.save_to_qwen_dir(qwen_dir)
        else:
            generator.save_to_qwen_dir()


if __name__ == "__main__":
    main()
