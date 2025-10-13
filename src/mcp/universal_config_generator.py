"""
Universal MCP Configuration Generator

Generates MCP server configurations compatible with various LLM clients:
- Qwen CLI
- Cursor
- Claude Desktop  
- LM Studio
- Other OpenAI-compatible APIs with MCP support
- Any MCP-compatible client

This generator creates configurations in different formats for different clients.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class UniversalMCPConfigGenerator:
    """Universal MCP configuration generator for all LLM clients"""

    def __init__(
        self,
        user_id: Optional[int] = None,
        http_port: int = 8765,
        mcp_hub_url: Optional[str] = None,
    ):
        """
        Initialize universal config generator

        Args:
            user_id: Optional user ID for per-user MCP servers
            http_port: Port for HTTP server (default: 8765)
            mcp_hub_url: Custom MCP Hub URL (for Docker environments). If not provided, auto-detected.
        """
        self.user_id = user_id
        self.http_port = http_port
        self.mcp_hub_url = mcp_hub_url
        self.project_root = Path(__file__).parent.parent.parent.resolve()

        # Auto-detect Docker environment if URL not provided
        if self.mcp_hub_url is None:
            self.mcp_hub_url = self._detect_mcp_hub_url()

    def _detect_mcp_hub_url(self) -> str:
        """
        Detect MCP Hub URL based on environment

        Returns:
            MCP Hub URL (Docker internal or localhost)
        """
        # Check if running in Docker container
        # Method 1: Check for .dockerenv file
        if Path("/.dockerenv").exists():
            logger.info("[UniversalMCPConfig] Detected Docker environment (/.dockerenv)")
            return f"http://mcp-hub:{self.http_port}/sse"

        # Method 2: Check for MCP_HUB_URL environment variable
        mcp_hub_env = os.getenv("MCP_HUB_URL")
        if mcp_hub_env:
            logger.info(
                f"[UniversalMCPConfig] Using MCP_HUB_URL from environment: {mcp_hub_env}"
            )
            return mcp_hub_env

        # Method 3: Check /proc/1/cgroup for docker
        try:
            with open("/proc/1/cgroup", "r") as f:
                if "docker" in f.read():
                    logger.info("[UniversalMCPConfig] Detected Docker environment (/proc/1/cgroup)")
                    return f"http://mcp-hub:{self.http_port}/sse"
        except Exception:
            pass

        # Default: assume host environment
        logger.info("[UniversalMCPConfig] Using localhost (host environment)")
        return f"http://127.0.0.1:{self.http_port}/sse"

    def generate_standard_config(self) -> Dict[str, Any]:
        """
        Generate standard MCP configuration format
        
        This format is compatible with:
        - Cursor
        - Claude Desktop
        - Qwen CLI
        - Most MCP-compatible clients

        Returns:
            Configuration dict with mcpServers
        """
        config = {
            "mcpServers": {
                "mcp-hub": {
                    "url": self.mcp_hub_url,
                    "timeout": 10000,
                    "trust": True,
                    "description": (
                        "MCP Hub - Unified MCP gateway with built-in memory tools. "
                        "Provides: store_memory, retrieve_memory, list_categories"
                    ),
                }
            }
        }

        # Add allowMCPServers for clients that require it (e.g., Qwen CLI)
        config["allowMCPServers"] = ["mcp-hub"]

        return config

    def generate_lm_studio_config(self) -> Dict[str, Any]:
        """
        Generate LM Studio compatible configuration
        
        LM Studio supports MCP through a specific configuration format.
        
        Returns:
            LM Studio configuration dict
        """
        return {
            "mcp_servers": {
                "mcp-hub": {
                    "transport": "http",
                    "url": self.mcp_hub_url,
                    "timeout": 10000,
                    "enabled": True,
                    "description": "MCP Hub - Memory and tool gateway",
                }
            }
        }

    def generate_openai_compatible_config(self) -> Dict[str, Any]:
        """
        Generate configuration for OpenAI-compatible APIs with MCP support
        
        Some OpenAI-compatible inference servers support MCP servers
        as additional context providers.
        
        Returns:
            Configuration dict
        """
        return {
            "mcp": {
                "enabled": True,
                "servers": [
                    {
                        "name": "mcp-hub",
                        "url": self.mcp_hub_url,
                        "transport": "sse",
                        "timeout": 10000,
                        "description": "MCP Hub - Built-in memory and tools",
                    }
                ],
            }
        }

    def save_for_qwen_cli(self, qwen_dir: Optional[Path] = None) -> Path:
        """
        Save configuration for Qwen CLI

        Args:
            qwen_dir: Optional custom qwen directory (default: ~/.qwen)

        Returns:
            Path to saved configuration file
        """
        if qwen_dir is None:
            qwen_dir = Path.home() / ".qwen"

        qwen_dir.mkdir(parents=True, exist_ok=True)
        settings_file = qwen_dir / "settings.json"

        # Load existing settings if present
        existing_config = {}
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)
                logger.info(f"Loaded existing qwen config from {settings_file}")
            except Exception as e:
                logger.warning(f"Failed to load existing config: {e}")

        # Generate new config
        new_config = self.generate_standard_config()

        # Merge configurations
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}

        existing_config["mcpServers"].update(new_config.get("mcpServers", {}))

        # Update allowMCPServers
        existing_allowed = set(existing_config.get("allowMCPServers", []))
        new_allowed = set(new_config.get("allowMCPServers", []))
        existing_config["allowMCPServers"] = list(existing_allowed | new_allowed)

        # Save merged configuration
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved Qwen CLI MCP config to {settings_file}")
        return settings_file

    def save_for_cursor(self, cursor_config_path: Optional[Path] = None) -> Path:
        """
        Save configuration for Cursor

        Args:
            cursor_config_path: Optional custom path (default: .mcp.json in project root)

        Returns:
            Path to saved configuration file
        """
        if cursor_config_path is None:
            cursor_config_path = self.project_root / ".mcp.json"

        config = self.generate_standard_config()

        with open(cursor_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved Cursor MCP config to {cursor_config_path}")
        return cursor_config_path

    def save_for_claude_desktop(
        self, claude_config_path: Optional[Path] = None
    ) -> Path:
        """
        Save configuration for Claude Desktop

        Args:
            claude_config_path: Optional custom path
                              (default: ~/Library/Application Support/Claude/claude_desktop_config.json on macOS)

        Returns:
            Path to saved configuration file
        """
        if claude_config_path is None:
            # Default path for macOS
            claude_config_path = (
                Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
            )

        claude_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config if present
        existing_config = {}
        if claude_config_path.exists():
            try:
                with open(claude_config_path, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)
                logger.info(f"Loaded existing Claude config from {claude_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load existing Claude config: {e}")

        # Generate new config
        new_config = self.generate_standard_config()

        # Merge configurations
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}

        existing_config["mcpServers"].update(new_config.get("mcpServers", {}))

        # Save merged configuration
        with open(claude_config_path, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved Claude Desktop MCP config to {claude_config_path}")
        return claude_config_path

    def save_for_lm_studio(self, lm_studio_config_path: Optional[Path] = None) -> Path:
        """
        Save configuration for LM Studio

        Args:
            lm_studio_config_path: Optional custom path
                                  (default: ~/.lmstudio/mcp_config.json)

        Returns:
            Path to saved configuration file
        """
        if lm_studio_config_path is None:
            lm_studio_config_path = Path.home() / ".lmstudio" / "mcp_config.json"

        lm_studio_config_path.parent.mkdir(parents=True, exist_ok=True)

        config = self.generate_lm_studio_config()

        with open(lm_studio_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved LM Studio MCP config to {lm_studio_config_path}")
        return lm_studio_config_path

    def save_for_data_directory(
        self, data_dir: Optional[Path] = None, filename: str = "mcp-hub.json"
    ) -> Path:
        """
        Save configuration to data/mcp_servers directory

        This is used for:
        - Python MCP clients
        - Custom integrations
        - Programmatic access

        Args:
            data_dir: Optional custom data directory (default: data/mcp_servers)
            filename: Configuration filename (default: mcp-hub.json)

        Returns:
            Path to saved configuration file
        """
        if data_dir is None:
            data_dir = Path("data/mcp_servers")

        data_dir.mkdir(parents=True, exist_ok=True)
        config_file = data_dir / filename

        config = self.generate_standard_config()

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved MCP config to {config_file}")
        return config_file

    def save_all(self, skip_errors: bool = True) -> Dict[str, Path]:
        """
        Save configurations for all supported clients

        Args:
            skip_errors: Continue if some saves fail (default: True)

        Returns:
            Dict mapping client names to saved config paths
        """
        saved_paths = {}
        
        # List of save operations
        save_operations = [
            ("qwen_cli", self.save_for_qwen_cli),
            ("cursor", self.save_for_cursor),
            ("claude_desktop", self.save_for_claude_desktop),
            ("lm_studio", self.save_for_lm_studio),
            ("data_directory", self.save_for_data_directory),
        ]

        for name, save_func in save_operations:
            try:
                path = save_func()
                saved_paths[name] = path
                logger.info(f"✓ Saved {name} config")
            except Exception as e:
                logger.error(f"✗ Failed to save {name} config: {e}")
                if not skip_errors:
                    raise

        return saved_paths


def main():
    """CLI entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate MCP configurations for various LLM clients"
    )
    parser.add_argument("--user-id", type=int, help="User ID for per-user MCP servers")
    parser.add_argument(
        "--port", type=int, default=8765, help="MCP Hub port (default: 8765)"
    )
    parser.add_argument(
        "--url", type=str, help="Custom MCP Hub URL (for Docker environments)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Save configurations for all supported clients",
    )
    parser.add_argument(
        "--qwen", action="store_true", help="Save configuration for Qwen CLI"
    )
    parser.add_argument(
        "--cursor", action="store_true", help="Save configuration for Cursor"
    )
    parser.add_argument(
        "--claude", action="store_true", help="Save configuration for Claude Desktop"
    )
    parser.add_argument(
        "--lmstudio", action="store_true", help="Save configuration for LM Studio"
    )
    parser.add_argument(
        "--data", action="store_true", help="Save configuration to data directory"
    )
    parser.add_argument(
        "--print", action="store_true", help="Print standard configuration to stdout"
    )

    args = parser.parse_args()

    generator = UniversalMCPConfigGenerator(
        user_id=args.user_id, http_port=args.port, mcp_hub_url=args.url
    )

    if args.print:
        # Print configuration
        config = generator.generate_standard_config()
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return

    # Save configurations
    saved_any = False

    if args.all:
        saved_paths = generator.save_all()
        print(f"\n✓ Saved {len(saved_paths)} configuration(s):")
        for name, path in saved_paths.items():
            print(f"  - {name}: {path}")
        saved_any = True

    if args.qwen:
        path = generator.save_for_qwen_cli()
        print(f"✓ Qwen CLI: {path}")
        saved_any = True

    if args.cursor:
        path = generator.save_for_cursor()
        print(f"✓ Cursor: {path}")
        saved_any = True

    if args.claude:
        path = generator.save_for_claude_desktop()
        print(f"✓ Claude Desktop: {path}")
        saved_any = True

    if args.lmstudio:
        path = generator.save_for_lm_studio()
        print(f"✓ LM Studio: {path}")
        saved_any = True

    if args.data:
        path = generator.save_for_data_directory()
        print(f"✓ Data directory: {path}")
        saved_any = True

    if not saved_any and not args.print:
        print("No action specified. Use --all, --qwen, --cursor, etc., or --print")
        print("Run with --help for usage information")


if __name__ == "__main__":
    main()
