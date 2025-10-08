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
from typing import Dict, List, Optional

from loguru import logger


class QwenMCPConfigGenerator:
    """Generator for qwen CLI MCP configuration"""
    
    def __init__(self, user_id: Optional[int] = None, use_http: bool = True, http_port: int = 8765):
        """
        Initialize config generator
        
        Args:
            user_id: Optional user ID for per-user MCP servers
            use_http: Use HTTP/SSE transport instead of stdio (default: True)
            http_port: Port for HTTP server (default: 8765)
        """
        self.user_id = user_id
        self.use_http = use_http
        self.http_port = http_port
        self.project_root = Path(__file__).parent.parent.parent.parent.resolve()
    
    def generate_config(self) -> Dict:
        """
        Generate qwen CLI MCP configuration
        
        Returns:
            Configuration dict with mcpServers
        """
        config = {
            "mcpServers": {}
        }
        
        # Add mem-agent MCP server
        mem_agent_config = self._generate_mem_agent_config()
        if mem_agent_config:
            config["mcpServers"]["mem-agent"] = mem_agent_config
        
        # Add other MCP servers here in the future
        # config["mcpServers"]["filesystem"] = ...
        # config["mcpServers"]["web-search"] = ...
        
        # Add allowMCPServers list
        if config["mcpServers"]:
            config["allowMCPServers"] = list(config["mcpServers"].keys())
        
        return config
    
    def _generate_mem_agent_config(self) -> Optional[Dict]:
        """
        Generate configuration for mem-agent MCP server
        
        Returns:
            Server configuration or None if not available
        """
        # Use HTTP/SSE transport
        if self.use_http:
            return {
                "url": f"http://127.0.0.1:{self.http_port}/sse",
                "timeout": 10000,
                "trust": True,
                "description": "Memory storage and retrieval agent (HTTP/SSE)"
            }
        
        # Use stdio transport (default)
        # Path to memory server script (relative to project root)
        server_script = self.project_root / "src" / "agents" / "mcp" / "memory" / "memory_server.py"
        
        if not server_script.exists():
            logger.warning(f"Mem-agent server script not found: {server_script}")
            return None
        
        # Use python3 command with relative path to script (relative to cwd)
        # This allows the configuration to work on any system where the project is located
        config = {
            "command": "python3",
            "args": [
                str(server_script.relative_to(self.project_root).as_posix())
            ],
            "cwd": str(self.project_root),
            "timeout": 10000,  # 10 seconds
            "trust": True,  # Trust our own server
            "description": "Memory storage and retrieval agent"
        }
        
        # Add user-id argument if specified
        if self.user_id:
            config["args"].extend(["--user-id", str(self.user_id)])
        
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
        
        # Load existing settings if present
        existing_config = {}
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
                logger.info(f"Loaded existing qwen config from {settings_file}")
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
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved qwen MCP config to {settings_file}")
        logger.info(f"Configured MCP servers: {list(config.get('mcpServers', {}).keys())}")
        
        return settings_file
    
    def save_to_kb_dir(self, kb_path: Path) -> Path:
        """
        Save configuration to KB directory (.qwen/settings.json)
        
        This creates a project-specific configuration in the knowledge base directory.
        
        Args:
            kb_path: Path to knowledge base directory
            
        Returns:
            Path to saved configuration file
        """
        qwen_dir = kb_path / ".qwen"
        return self.save_to_qwen_dir(qwen_dir)
    
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
    kb_path: Optional[Path] = None,
    global_config: bool = True,
    use_http: bool = True,
    http_port: int = 8765
) -> List[Path]:
    """
    Setup qwen MCP configuration
    
    This is a convenience function that:
    1. Generates MCP server configuration
    2. Saves to global ~/.qwen/settings.json (if global_config=True)
    3. Saves to KB-specific .qwen/settings.json (if kb_path provided)
    
    Args:
        user_id: Optional user ID for per-user MCP servers
        kb_path: Optional path to knowledge base directory
        global_config: Whether to save to global ~/.qwen/settings.json
        use_http: Use HTTP/SSE transport instead of stdio (default: True)
        http_port: Port for HTTP server (default: 8765)
        
    Returns:
        List of paths where configuration was saved
    """
    generator = QwenMCPConfigGenerator(user_id=user_id, use_http=use_http, http_port=http_port)
    saved_paths = []
    
    # Save to global config
    if global_config:
        path = generator.save_to_qwen_dir()
        saved_paths.append(path)
    
    # Save to KB-specific config
    if kb_path:
        path = generator.save_to_kb_dir(kb_path)
        saved_paths.append(path)
    
    return saved_paths


def main():
    """CLI entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate qwen CLI MCP configuration"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="User ID for per-user MCP servers"
    )
    parser.add_argument(
        "--kb-path",
        type=Path,
        help="Knowledge base path for project-specific config"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: ~/.qwen/settings.json)"
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print configuration to stdout instead of saving"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP/SSE transport instead of stdio"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for HTTP server (default: 8765)"
    )
    
    args = parser.parse_args()
    
    generator = QwenMCPConfigGenerator(
        user_id=args.user_id,
        use_http=args.http,
        http_port=args.port
    )
    
    if args.print:
        # Just print the configuration
        print(generator.get_config_json())
    else:
        # Save configuration
        if args.output:
            qwen_dir = args.output.parent
            generator.save_to_qwen_dir(qwen_dir)
        elif args.kb_path:
            generator.save_to_kb_dir(args.kb_path)
        else:
            generator.save_to_qwen_dir()


if __name__ == "__main__":
    main()