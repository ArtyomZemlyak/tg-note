"""
MCP Server Manager
Manages lifecycle of MCP servers (start, stop, health checks)
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger

from config.settings import Settings


class MCPServerProcess:
    """
    Manages a single MCP server process
    """
    
    def __init__(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path] = None
    ):
        """
        Initialize MCP server process
        
        Args:
            name: Server name
            command: Command to run
            args: Command arguments
            env: Environment variables
            cwd: Working directory
        """
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.cwd = cwd
        self.process: Optional[subprocess.Popen] = None
        self._running = False
    
    def start(self) -> bool:
        """
        Start the MCP server process
        
        Returns:
            True if started successfully
        """
        if self._running and self.process:
            logger.warning(f"[MCPServerManager] Server '{self.name}' is already running")
            return True
        
        try:
            # Prepare environment
            import os
            full_env = os.environ.copy()
            full_env.update(self.env)
            
            # Start process
            logger.info(f"[MCPServerManager] Starting server '{self.name}': {self.command} {' '.join(self.args)}")
            
            self.process = subprocess.Popen(
                [self.command] + self.args,
                env=full_env,
                cwd=self.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self._running = True
            logger.info(f"[MCPServerManager] Server '{self.name}' started (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"[MCPServerManager] Failed to start server '{self.name}': {e}")
            self._running = False
            return False
    
    def stop(self) -> bool:
        """
        Stop the MCP server process
        
        Returns:
            True if stopped successfully
        """
        if not self._running or not self.process:
            logger.debug(f"[MCPServerManager] Server '{self.name}' is not running")
            return True
        
        try:
            logger.info(f"[MCPServerManager] Stopping server '{self.name}'...")
            
            # Try graceful shutdown first
            self.process.terminate()
            
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown failed
                logger.warning(f"[MCPServerManager] Server '{self.name}' did not terminate gracefully, forcing...")
                self.process.kill()
                self.process.wait(timeout=2)
            
            self._running = False
            logger.info(f"[MCPServerManager] Server '{self.name}' stopped")
            return True
            
        except Exception as e:
            logger.error(f"[MCPServerManager] Failed to stop server '{self.name}': {e}")
            return False
    
    def is_running(self) -> bool:
        """
        Check if server is running
        
        Returns:
            True if running
        """
        if not self._running or not self.process:
            return False
        
        # Check if process is still alive
        if self.process.poll() is not None:
            self._running = False
            return False
        
        return True


class MCPServerManager:
    """
    Global MCP Server Manager
    
    Manages all MCP servers for the bot:
    - Auto-starts servers on bot startup based on settings
    - Handles server lifecycle (start, stop)
    - Monitors server health
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize MCP server manager
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.servers: Dict[str, MCPServerProcess] = {}
    
    def register_server(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path] = None
    ) -> None:
        """
        Register an MCP server
        
        Args:
            name: Server name
            command: Command to run
            args: Command arguments
            env: Environment variables
            cwd: Working directory
        """
        server = MCPServerProcess(
            name=name,
            command=command,
            args=args,
            env=env,
            cwd=cwd
        )
        
        self.servers[name] = server
        logger.debug(f"[MCPServerManager] Registered server: {name}")
    
    def start_server(self, name: str) -> bool:
        """
        Start a specific server
        
        Args:
            name: Server name
            
        Returns:
            True if started successfully
        """
        if name not in self.servers:
            logger.error(f"[MCPServerManager] Server '{name}' not registered")
            return False
        
        return self.servers[name].start()
    
    def stop_server(self, name: str) -> bool:
        """
        Stop a specific server
        
        Args:
            name: Server name
            
        Returns:
            True if stopped successfully
        """
        if name not in self.servers:
            logger.error(f"[MCPServerManager] Server '{name}' not registered")
            return False
        
        return self.servers[name].stop()
    
    def start_all(self) -> Dict[str, bool]:
        """
        Start all registered servers
        
        Returns:
            Dict mapping server names to start success status
        """
        results = {}
        
        for name in self.servers:
            results[name] = self.start_server(name)
        
        return results
    
    def stop_all(self) -> Dict[str, bool]:
        """
        Stop all running servers
        
        Returns:
            Dict mapping server names to stop success status
        """
        results = {}
        
        for name in self.servers:
            results[name] = self.stop_server(name)
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all servers
        
        Returns:
            Dict with server status information
        """
        status = {}
        
        for name, server in self.servers.items():
            status[name] = {
                "running": server.is_running(),
                "pid": server.process.pid if server.process else None
            }
        
        return status
    
    def setup_default_servers(self) -> None:
        """
        Setup default MCP servers based on settings
        
        This registers servers that should be auto-started when enabled in settings:
        - mem-agent HTTP server (if AGENT_ENABLE_MCP_MEMORY is True)
        
        Also creates necessary configuration files:
        - data/mcp_servers/mem-agent.json (for Python MCP clients)
        - ~/.qwen/settings.json (for Qwen CLI)
        """
        # Register mem-agent HTTP server if MCP memory is enabled
        if self.settings.AGENT_ENABLE_MCP_MEMORY:
            logger.info("[MCPServerManager] MCP memory agent is enabled, registering mem-agent HTTP server")
            
            # Create data/mcp_servers directory if it doesn't exist
            mcp_servers_dir = Path("data/mcp_servers")
            mcp_servers_dir.mkdir(parents=True, exist_ok=True)
            
            # Create mem-agent.json config file if it doesn't exist
            mem_agent_config_file = mcp_servers_dir / "mem-agent.json"
            if not mem_agent_config_file.exists():
                logger.info(f"[MCPServerManager] Creating MCP server config at {mem_agent_config_file}")
                
                config = {
                    "name": "mem-agent",
                    "description": "Agent's personal note-taking and search system - allows the agent to record and search notes during task execution",
                    "command": "python",
                    "args": ["-m", "src.agents.mcp.mem_agent_server_http", "--host", "127.0.0.1", "--port", "8765"],
                    "env": {},
                    "working_dir": str(Path.cwd()),
                    "enabled": True,
                    "transport": "http"
                }
                
                try:
                    with open(mem_agent_config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    logger.info(f"[MCPServerManager] Created MCP server config: {mem_agent_config_file}")
                except Exception as e:
                    logger.error(f"[MCPServerManager] Failed to create MCP server config: {e}")
            else:
                logger.debug(f"[MCPServerManager] MCP server config already exists: {mem_agent_config_file}")
            
            # Use Python module path for HTTP server
            self.register_server(
                name="mem-agent",
                command="python",
                args=["-m", "src.agents.mcp.mem_agent_server_http", "--host", "127.0.0.1", "--port", "8765"],
                env={},
                cwd=Path.cwd()
            )
        
        # Also create ~/.qwen/settings.json if MCP is enabled for Qwen CLI support
        if self.settings.AGENT_ENABLE_MCP or self.settings.AGENT_ENABLE_MCP_MEMORY:
            self._create_qwen_config()
    
    def _create_qwen_config(self) -> None:
        """
        Create ~/.qwen/settings.json for Qwen CLI MCP support
        
        This allows QwenCodeCLIAgent to use MCP servers via Qwen CLI's native MCP client.
        """
        try:
            from .qwen_config_generator import setup_qwen_mcp_config
            
            logger.info("[MCPServerManager] Creating Qwen CLI MCP configuration at ~/.qwen/settings.json")
            
            # Generate and save configuration (global only, no KB-specific)
            saved_paths = setup_qwen_mcp_config(
                user_id=None,  # No user-specific config
                kb_path=None,  # No KB-specific config
                global_config=True  # Only global ~/.qwen/settings.json
            )
            
            logger.info(f"[MCPServerManager] Qwen CLI MCP configuration saved to: {saved_paths}")
            
        except Exception as e:
            logger.warning(f"[MCPServerManager] Failed to create Qwen CLI config (non-critical): {e}")
            logger.debug(f"[MCPServerManager] Qwen CLI config error details:", exc_info=True)
    
    async def auto_start_servers(self) -> Dict[str, bool]:
        """
        Auto-start servers based on settings
        
        This is called during bot initialization to start required servers.
        
        Returns:
            Dict mapping server names to start success status
        """
        logger.info("[MCPServerManager] Auto-starting MCP servers based on settings...")
        
        # Setup default servers first
        self.setup_default_servers()
        
        # Start all registered servers
        results = self.start_all()
        
        # Log results
        for name, success in results.items():
            if success:
                logger.info(f"[MCPServerManager] ✓ Server '{name}' started successfully")
            else:
                logger.error(f"[MCPServerManager] ✗ Server '{name}' failed to start")
        
        return results
    
    async def cleanup(self) -> None:
        """
        Cleanup: stop all servers
        
        This should be called during bot shutdown.
        """
        logger.info("[MCPServerManager] Stopping all MCP servers...")
        
        results = self.stop_all()
        
        for name, success in results.items():
            if success:
                logger.info(f"[MCPServerManager] ✓ Server '{name}' stopped")
            else:
                logger.warning(f"[MCPServerManager] ✗ Server '{name}' failed to stop cleanly")


# Global server manager instance (will be initialized in service container)
_server_manager: Optional[MCPServerManager] = None


def get_server_manager() -> Optional[MCPServerManager]:
    """
    Get global MCP server manager instance
    
    Returns:
        Server manager or None if not initialized
    """
    return _server_manager


def set_server_manager(manager: MCPServerManager) -> None:
    """
    Set global MCP server manager instance
    
    Args:
        manager: Server manager instance
    """
    global _server_manager
    _server_manager = manager