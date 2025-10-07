"""
MCP Server Manager
Manages lifecycle of MCP servers (start, stop, health checks)
"""

import asyncio
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
        - mem-agent server (if AGENT_ENABLE_MCP_MEMORY is True)
        """
        # Register mem-agent server if MCP memory is enabled
        if self.settings.AGENT_ENABLE_MCP_MEMORY:
            logger.info("[MCPServerManager] MCP memory agent is enabled, registering mem-agent server")
            
            # Use Python module path
            self.register_server(
                name="mem-agent",
                command="python",
                args=["-m", "src.agents.mcp.mem_agent_server"],
                env={},
                cwd=Path.cwd()
            )
    
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