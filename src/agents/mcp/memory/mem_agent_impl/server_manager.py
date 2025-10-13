"""
Server Manager for vLLM and MLX Servers

This module manages the lifecycle of local LLM servers (vLLM on Linux, MLX on macOS).
Servers should be started during MCP memory service initialization, not on first agent creation.
"""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from loguru import logger

from .settings import MEM_AGENT_HOST, MEM_AGENT_MODEL, MEM_AGENT_PORT

# Global process reference to keep track of started servers
_server_process: Optional[subprocess.Popen] = None


def is_server_running(host: str = MEM_AGENT_HOST, port: int = MEM_AGENT_PORT) -> bool:
    """
    Check if a server is already running at the given host and port.
    
    Args:
        host: Host address
        port: Port number
        
    Returns:
        True if server is reachable, False otherwise
    """
    base_url = f"http://{host}:{port}/v1"
    try:
        urlopen(f"{base_url}/models", timeout=1.0)
        return True
    except (URLError, Exception):
        return False


def start_vllm_server(
    host: str = MEM_AGENT_HOST,
    port: int = MEM_AGENT_PORT,
    model: str = MEM_AGENT_MODEL,
    timeout: int = 30,
) -> bool:
    """
    Start vLLM server in the background (Linux).
    
    Args:
        host: Host address to bind to
        port: Port number to bind to
        model: Model name to load
        timeout: Maximum seconds to wait for server to become ready
        
    Returns:
        True if server started successfully, False otherwise
    """
    global _server_process
    
    logger.info("="*80)
    logger.info("🚀 STARTING vLLM SERVER")
    logger.info("="*80)
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Model: {model}")
    logger.info(f"  Timeout: {timeout}s")
    logger.info("="*80)
    
    # Check if already running
    if is_server_running(host, port):
        logger.info(f"✅ vLLM server already running at http://{host}:{port}/v1")
        return True
    
    # Create log directory
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    vllm_log_file = log_dir / "vllm_server.log"
    vllm_error_file = log_dir / "vllm_server_errors.log"
    
    try:
        # Open log files
        log_f = open(vllm_log_file, "a")
        err_f = open(vllm_error_file, "a")
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_f.write(f"\n{'='*80}\n")
        log_f.write(f"vLLM server startup at {timestamp}\n")
        log_f.write(f"Model: {model}\n")
        log_f.write(f"Host: {host}:{port}\n")
        log_f.write(f"{'='*80}\n")
        log_f.flush()
        
        err_f.write(f"\n{'='*80}\n")
        err_f.write(f"vLLM server startup at {timestamp}\n")
        err_f.write(f"{'='*80}\n")
        err_f.flush()
        
        # Start vLLM server
        _server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "vllm.entrypoints.openai.api_server",
                "--host",
                host,
                "--port",
                str(port),
                "--model",
                model,
            ],
            stdout=log_f,
            stderr=err_f,
        )
        
        logger.info(f"📋 vLLM server process started (PID: {_server_process.pid})")
        logger.info(f"📄 Logs: {vllm_log_file}")
        logger.info(f"📄 Errors: {vllm_error_file}")
        logger.info("⏳ Waiting for server to become ready...")
        
        # Wait for server to become ready
        base_url = f"http://{host}:{port}/v1"
        for i in range(timeout * 2):  # Check every 0.5s
            time.sleep(0.5)
            try:
                urlopen(f"{base_url}/models", timeout=1.0)
                logger.info("="*80)
                logger.info(f"✅ vLLM server is ready at {base_url}")
                logger.info("="*80)
                os.environ["MEM_AGENT_BASE_URL"] = base_url
                return True
            except URLError:
                if i % 4 == 0:  # Log every 2 seconds
                    logger.debug(f"  Still waiting... ({i//2 + 1}s)")
                continue
        
        logger.error("="*80)
        logger.error(f"❌ vLLM server did not become ready after {timeout} seconds")
        logger.error(f"   Check logs at {vllm_error_file}")
        logger.error("="*80)
        return False
        
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ Failed to start vLLM server: {e}")
        logger.error("="*80, exc_info=True)
        return False


def start_mlx_server(
    host: str = MEM_AGENT_HOST,
    port: int = MEM_AGENT_PORT,
    model: str = MEM_AGENT_MODEL,
    timeout: int = 30,
) -> bool:
    """
    Start MLX server in the background (macOS).
    
    Args:
        host: Host address to bind to
        port: Port number to bind to
        model: Model name to load
        timeout: Maximum seconds to wait for server to become ready
        
    Returns:
        True if server started successfully, False otherwise
    """
    global _server_process
    
    logger.info("="*80)
    logger.info("🚀 STARTING MLX SERVER")
    logger.info("="*80)
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Model: {model}")
    logger.info(f"  Timeout: {timeout}s")
    logger.info("="*80)
    
    # Check if already running
    if is_server_running(host, port):
        logger.info(f"✅ MLX server already running at http://{host}:{port}/v1")
        return True
    
    # Check MLX compatibility first
    try:
        import mlx.core as mx
        logger.info("✅ MLX library is compatible")
    except ImportError as mlx_error:
        logger.error("="*80)
        logger.error("❌ MLX COMPATIBILITY ERROR")
        logger.error(f"  Error: {mlx_error}")
        logger.error("  ")
        logger.error("  Possible causes:")
        logger.error("  1. macOS version too old (MLX requires macOS 13.5+)")
        logger.error("  2. MLX not installed correctly")
        logger.error("  ")
        logger.error("  Solutions:")
        logger.error("  - Upgrade to macOS 13.5 or later, OR")
        logger.error("  - Set MEM_AGENT_OPENAI_API_KEY to use OpenRouter/OpenAI, OR")
        logger.error("  - Install compatible MLX version: pip install --upgrade mlx mlx-lm")
        logger.error("  ")
        logger.error("  Falling back to OpenRouter/OpenAI endpoint")
        logger.error("="*80)
        return False
    
    # Create log directory
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    mlx_log_file = log_dir / "mlx_server.log"
    mlx_error_file = log_dir / "mlx_server_errors.log"
    
    try:
        # Open log files
        log_f = open(mlx_log_file, "a")
        err_f = open(mlx_error_file, "a")
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_f.write(f"\n{'='*80}\n")
        log_f.write(f"MLX server startup at {timestamp}\n")
        log_f.write(f"Model: {model}\n")
        log_f.write(f"Host: {host}:{port}\n")
        log_f.write(f"{'='*80}\n")
        log_f.flush()
        
        err_f.write(f"\n{'='*80}\n")
        err_f.write(f"MLX server startup at {timestamp}\n")
        err_f.write(f"{'='*80}\n")
        err_f.flush()
        
        # Start MLX server
        _server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "mlx_lm.server",
                "--model",
                model,
                "--host",
                host,
                "--port",
                str(port),
            ],
            stdout=log_f,
            stderr=err_f,
        )
        
        logger.info(f"📋 MLX server process started (PID: {_server_process.pid})")
        logger.info(f"📄 Logs: {mlx_log_file}")
        logger.info(f"📄 Errors: {mlx_error_file}")
        logger.info("⏳ Waiting for server to become ready...")
        
        # Wait for server to become ready
        base_url = f"http://{host}:{port}/v1"
        for i in range(timeout * 2):  # Check every 0.5s
            time.sleep(0.5)
            try:
                urlopen(f"{base_url}/models", timeout=1.0)
                logger.info("="*80)
                logger.info(f"✅ MLX server is ready at {base_url}")
                logger.info("="*80)
                os.environ["MEM_AGENT_BASE_URL"] = base_url
                return True
            except URLError:
                if i % 4 == 0:  # Log every 2 seconds
                    logger.debug(f"  Still waiting... ({i//2 + 1}s)")
                continue
        
        logger.error("="*80)
        logger.error(f"❌ MLX server did not become ready after {timeout} seconds")
        logger.error(f"   Check logs at {mlx_error_file}")
        logger.error("="*80)
        return False
        
    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ Failed to start MLX server: {e}")
        logger.error("="*80, exc_info=True)
        return False


def ensure_server_started(
    host: str = MEM_AGENT_HOST,
    port: int = MEM_AGENT_PORT,
    model: str = MEM_AGENT_MODEL,
    timeout: int = 30,
) -> bool:
    """
    Ensure a local LLM server is started based on the platform.
    
    - Linux: Start vLLM server
    - macOS: Start MLX server
    - Others: Return False (no local server support)
    
    This should be called during MCP memory service initialization,
    not on first agent creation.
    
    Args:
        host: Host address to bind to
        port: Port number to bind to
        model: Model name to load
        timeout: Maximum seconds to wait for server to become ready
        
    Returns:
        True if server is running (either already running or successfully started),
        False otherwise
    """
    from .settings import MEM_AGENT_BASE_URL, MEM_AGENT_OPENAI_API_KEY
    
    # If explicit endpoint or API key is configured, don't start local server
    if MEM_AGENT_BASE_URL or MEM_AGENT_OPENAI_API_KEY:
        logger.info("⏩ Skipping local server startup (endpoint/API key already configured)")
        if MEM_AGENT_BASE_URL:
            logger.info(f"  Using endpoint: {MEM_AGENT_BASE_URL}")
        else:
            logger.info("  Using OpenRouter/OpenAI with API key")
        return True
    
    # Determine platform and start appropriate server
    system = platform.system().lower()
    
    if system == "linux":
        logger.info("🐧 Linux detected - starting vLLM server")
        return start_vllm_server(host=host, port=port, model=model, timeout=timeout)
    
    elif system == "darwin":
        logger.info("🍎 macOS detected - starting MLX server")
        return start_mlx_server(host=host, port=port, model=model, timeout=timeout)
    
    else:
        logger.warning(f"⚠️ Platform '{system}' not supported for local server")
        logger.warning("  Please configure MEM_AGENT_OPENAI_API_KEY to use OpenRouter/OpenAI")
        return False


def stop_server() -> None:
    """
    Stop the server process if it's running.
    
    This should be called during shutdown (if needed).
    """
    global _server_process
    
    if _server_process is not None:
        logger.info(f"🛑 Stopping server (PID: {_server_process.pid})")
        try:
            _server_process.terminate()
            _server_process.wait(timeout=5)
            logger.info("✅ Server stopped successfully")
        except Exception as e:
            logger.error(f"❌ Error stopping server: {e}")
            try:
                _server_process.kill()
                logger.warning("⚠️ Server forcefully killed")
            except Exception as e2:
                logger.error(f"❌ Error killing server: {e2}")
        finally:
            _server_process = None
