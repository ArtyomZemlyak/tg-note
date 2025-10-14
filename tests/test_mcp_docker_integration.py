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

    # Assert: client-style config created pointing to mcp-hub URL
    config_file = Path("data/mcp_servers/mcp-hub.json")
    assert config_file.exists(), "mcp-hub client config should be created"

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "mcpServers" in data and "mcp-hub" in data["mcpServers"], "Config must contain mcp-hub entry"
    assert data["mcpServers"]["mcp-hub"]["url"] == hub_url, "Config URL must point to MCP hub"


def test_memory_mcp_tool_loads_sse_config_from_file(tmp_path, monkeypatch):
    # Arrange: prepare a client-style config file created by server manager
    monkeypatch.chdir(tmp_path)
    config_dir = Path("data/mcp_servers")
    config_dir.mkdir(parents=True, exist_ok=True)
    hub_url = "http://mcp-hub:8765/sse"
    config = {"mcpServers": {"mcp-hub": {"url": hub_url, "transport": "sse", "timeout": 10000}}}
    (config_dir / "mcp-hub.json").write_text(json.dumps(config), encoding="utf-8")

    # Act
    tool = MemoryMCPTool()
    cfg = tool.mcp_server_config

    # Assert: MemoryMCPTool should pick SSE transport and provided URL
    assert cfg.transport == "sse"
    assert cfg.url == hub_url
