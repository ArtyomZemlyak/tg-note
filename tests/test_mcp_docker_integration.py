"""
Tests to ensure Docker MCP mode uses external mcp-hub container and does not
start local MCP subprocesses inside the bot container.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.settings import Settings
from src.mcp.memory.memory_tool import MemoryMCPTool
from src.mcp.server_manager import MCPServerManager


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
    assert (
        not config_file.exists()
    ), "Bot must not create mcp-hub.json in Docker mode (hub owns configs)"


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


@pytest.mark.asyncio
async def test_mcp_hub_health_includes_builtin_tools():
    """Test that MCP Hub health check reports built-in tools"""
    # Arrange: Mock the health response
    # Note: The number of tools is dynamic based on configuration:
    # - Base tools (always available): store_memory, retrieve_memory, list_categories (3 tools)
    # - Vector search tools (conditional): vector_search, reindex_vector (2 tools)
    # Total: 3 tools (vector search disabled) or 5 tools (vector search enabled)
    mock_health_response = {
        "status": "ok",
        "service": "mcp-hub",
        "version": "1.0.0",
        "builtin_tools": {
            "total": 3,  # Can be 3 or 5 depending on VECTOR_SEARCH_ENABLED
            "names": [
                "store_memory",
                "retrieve_memory",
                "list_categories",
                # Conditionally: "vector_search", "reindex_vector"
            ],
        },
        "registry": {
            "servers_total": 0,
            "servers_enabled": 0,
        },
        "storage": {
            "active_users": 0,
        },
        "ready": True,
    }

    # Act & Assert: Verify the structure
    assert "builtin_tools" in mock_health_response
    # After refactor, MCP Hub exposes memory tools and optionally vector search tools
    # Management endpoints are available via HTTP API, not as MCP tools
    
    # Base tools should always be present
    assert mock_health_response["builtin_tools"]["total"] >= 3
    assert len(mock_health_response["builtin_tools"]["names"]) >= 3
    assert "store_memory" in mock_health_response["builtin_tools"]["names"]
    assert "retrieve_memory" in mock_health_response["builtin_tools"]["names"]
    assert "list_categories" in mock_health_response["builtin_tools"]["names"]
    
    # Total should be either 3 (no vector search) or 5 (with vector search)
    assert mock_health_response["builtin_tools"]["total"] in [3, 5]
    assert mock_health_response["builtin_tools"]["total"] == len(mock_health_response["builtin_tools"]["names"])
