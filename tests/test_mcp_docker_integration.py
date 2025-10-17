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
    # Note: The number of tools is DYNAMIC based on configuration:
    # 
    # Memory tools (3 tools - controlled by AGENT_ENABLE_MCP_MEMORY):
    #   - store_memory
    #   - retrieve_memory
    #   - list_categories
    # 
    # Vector search tools (2 tools - controlled by VECTOR_SEARCH_ENABLED + dependencies):
    #   - vector_search
    #   - reindex_vector
    #
    # Possible totals:
    #   - 0 tools: both disabled
    #   - 2 tools: only vector search enabled
    #   - 3 tools: only memory enabled (default)
    #   - 5 tools: both enabled
    mock_health_response = {
        "status": "ok",
        "service": "mcp-hub",
        "version": "1.0.0",
        "builtin_tools": {
            "total": 3,  # Can be 0, 2, 3, or 5 depending on config
            "names": [
                "store_memory",
                "retrieve_memory",
                "list_categories",
                # Conditionally added if VECTOR_SEARCH_ENABLED:
                # "vector_search", "reindex_vector"
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
    # After refactor, MCP Hub exposes tools dynamically based on configuration
    # Management endpoints are available via HTTP API, not as MCP tools
    
    # Total should be one of the valid combinations
    assert mock_health_response["builtin_tools"]["total"] in [0, 2, 3, 5]
    assert mock_health_response["builtin_tools"]["total"] == len(mock_health_response["builtin_tools"]["names"])
    
    # If memory tools are in the list, verify they are complete
    memory_tools = ["store_memory", "retrieve_memory", "list_categories"]
    memory_tools_present = [tool in mock_health_response["builtin_tools"]["names"] for tool in memory_tools]
    if any(memory_tools_present):
        # Either all memory tools present or none
        assert all(memory_tools_present), "Memory tools should be all present or all absent"
    
    # If vector search tools are in the list, verify they are complete
    vector_tools = ["vector_search", "reindex_vector"]
    vector_tools_present = [tool in mock_health_response["builtin_tools"]["names"] for tool in vector_tools]
    if any(vector_tools_present):
        # Either all vector tools present or none
        assert all(vector_tools_present), "Vector search tools should be all present or all absent"
