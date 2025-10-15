"""
Tests to ensure Docker MCP mode uses external mcp-hub container and does not
start local MCP subprocesses inside the bot container.
"""

import json
from pathlib import Path

import pytest

from config.settings import Settings
from src.mcp.server_manager import MCPServerManager
from src.mcp.memory.memory_tool import MemoryMCPTool


def test_mcp_docker_mode_uses_hub_and_no_subprocess(tmp_path, monkeypatch):
    # Arrange: isolate working directory and environment
    monkeypatch.chdir(tmp_path)
    hub_url = "http://mcp-hub:8765/sse"
    monkeypatch.setenv("MCP_HUB_URL", hub_url)

    # Ensure settings read MCP enablement from env with highest priority
    monkeypatch.setenv("AGENT_ENABLE_MCP", "false")
    monkeypatch.setenv("AGENT_ENABLE_MCP_MEMORY", "true")

    # Enable only MCP memory; dynamic MCP is irrelevant here (constructor args are lower priority)
    settings = Settings(AGENT_ENABLE_MCP=False, AGENT_ENABLE_MCP_MEMORY=True)
    manager = MCPServerManager(settings)

    # Act
    manager.setup_default_servers()

    # Assert: no subprocess servers registered
    assert manager.servers == {}, "No MCP subprocesses should be registered in Docker mode"

    # Assert: bot container does NOT create local client-style configs in Docker mode
    config_file = Path("data/mcp_servers/mcp-hub.json")
    assert not config_file.exists(), "Bot must not create mcp-hub.json in Docker mode (hub owns configs)"


def test_memory_mcp_tool_uses_env_url_in_docker(tmp_path, monkeypatch):
    # Arrange: prefer MCP_HUB_URL environment when set
    monkeypatch.chdir(tmp_path)
    hub_url = "http://mcp-hub:8765/sse"
    monkeypatch.setenv("MCP_HUB_URL", hub_url)

    # Act
    tool = MemoryMCPTool()
    cfg = tool.mcp_server_config

    # Assert: MemoryMCPTool should pick SSE transport and provided URL from env
    assert cfg.transport == "sse"
    assert cfg.url == hub_url
