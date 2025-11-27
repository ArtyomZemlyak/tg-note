"""
Tests for MCP tools description functionality

Verifies that agents can discover and describe available MCP tools.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from promptic import load_prompt

from src.agents.autonomous_agent import AutonomousAgent
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent
from src.mcp.tools_description import format_mcp_tools_for_prompt, get_mcp_tools_description


class TestMCPToolsDescription:
    """Test MCP tools description generation"""

    @pytest.mark.asyncio
    async def test_get_mcp_tools_description_no_servers(self):
        """Test description generation when no MCP servers are available"""
        # Mock registry client to return no servers
        with patch("src.mcp.tools_description.MCPRegistryClient") as mock_registry:
            mock_instance = Mock()
            mock_instance.initialize = Mock()
            mock_instance.connect_all_enabled = AsyncMock(return_value={})
            mock_registry.return_value = mock_instance

            description = await get_mcp_tools_description()

            # Should return empty string when no servers
            assert description == ""

    @pytest.mark.asyncio
    async def test_get_mcp_tools_description_with_servers(self):
        """Test description generation with mock MCP servers"""
        # Mock a server with tools
        mock_client = Mock()
        mock_client.list_tools = AsyncMock(
            return_value=[
                {
                    "name": "test_tool",
                    "description": "A test tool",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "param1": {"type": "string", "description": "First parameter"}
                        },
                        "required": ["param1"],
                    },
                }
            ]
        )

        with patch("src.mcp.tools_description.MCPRegistryClient") as mock_registry:
            mock_instance = Mock()
            mock_instance.initialize = Mock()
            mock_instance.connect_all_enabled = AsyncMock(return_value={"test_server": mock_client})
            mock_registry.return_value = mock_instance

            description = await get_mcp_tools_description()

            # Should contain server name and tool info
            assert "test_server" in description
            assert "test_tool" in description
            assert "mcp_test_server_test_tool" in description
            assert "A test tool" in description
            assert "param1" in description

    def test_format_mcp_tools_for_prompt_system(self):
        """Test formatting MCP tools for system prompt"""
        tools_desc = "# Test Tools\n\nSome tools available"

        formatted = format_mcp_tools_for_prompt(tools_desc, include_in_system=True)

        assert "MCP Tools Available" in formatted
        assert tools_desc in formatted

    def test_format_mcp_tools_for_prompt_user(self):
        """Test formatting MCP tools for user prompt"""
        tools_desc = "# Test Tools\n\nSome tools available"

        formatted = format_mcp_tools_for_prompt(tools_desc, include_in_system=False)

        assert tools_desc in formatted
        assert "---" in formatted

    def test_format_mcp_tools_for_prompt_empty(self):
        """Test formatting empty tools description"""
        formatted = format_mcp_tools_for_prompt("", include_in_system=True)

        assert formatted == ""

    def test_prompt_registry_lookup(self, tmp_path):
        """Promptic should locate highest version file using _vX naming convention"""
        # Create temporary prompt files with correct naming convention (_vX.md)
        base = tmp_path / "demo"
        base.mkdir(parents=True)
        (base / "greeting_v1.md").write_text("hello v1", encoding="utf-8")
        (base / "greeting_v2.md").write_text("hello v2", encoding="utf-8")

        latest = load_prompt(str(base), version="latest")
        assert latest == "hello v2"


class TestAutonomousAgentMCPIntegration:
    """Test AutonomousAgent MCP integration"""

    @pytest.mark.asyncio
    async def test_autonomous_agent_get_mcp_tools_disabled(self):
        """Test that MCP tools description is empty when MCP is disabled"""
        config = {"enable_mcp": False}
        agent = AutonomousAgent(config=config, enable_mcp=False)

        description = await agent.get_mcp_tools_description()

        assert description == ""
        assert agent._mcp_tools_description == ""

    @pytest.mark.asyncio
    async def test_autonomous_agent_get_mcp_tools_enabled(self):
        """Test that MCP tools description is generated when enabled"""
        config = {"enable_mcp": True, "user_id": 12345}

        # Mock discover_and_create_mcp_tools to prevent actual MCP discovery during agent init
        with patch(
            "src.agents.tools.registry.discover_and_create_mcp_tools", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = []

            agent = AutonomousAgent(config=config, enable_mcp=True)

            # Mock the MCP description function - patch where it's imported FROM
            with patch("src.mcp.get_mcp_tools_description", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = "# Test MCP Tools"

                with patch("src.mcp.format_mcp_tools_for_prompt") as mock_format:
                    mock_format.return_value = "## MCP Tools Available\n\n# Test MCP Tools"

                    description = await agent.get_mcp_tools_description()

                    # Should call the functions with correct parameters
                    mock_get.assert_called_once_with(user_id=12345)
                    mock_format.assert_called_once_with("# Test MCP Tools", include_in_system=True)

                    # Should cache the result
                    assert (
                        agent._mcp_tools_description == "## MCP Tools Available\n\n# Test MCP Tools"
                    )

    @pytest.mark.asyncio
    async def test_autonomous_agent_caches_mcp_description(self):
        """Test that MCP tools description is cached"""
        config = {"enable_mcp": True}

        # Mock discover_and_create_mcp_tools to prevent actual MCP discovery during agent init
        with patch(
            "src.agents.tools.registry.discover_and_create_mcp_tools", new_callable=AsyncMock
        ) as mock_discover:
            mock_discover.return_value = []

            agent = AutonomousAgent(config=config, enable_mcp=True)

            with patch("src.mcp.get_mcp_tools_description", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = "# Test MCP Tools"

                with patch("src.mcp.format_mcp_tools_for_prompt") as mock_format:
                    mock_format.return_value = "Formatted tools"

                    # First call
                    description1 = await agent.get_mcp_tools_description()

                    # Second call
                    description2 = await agent.get_mcp_tools_description()

                    # Should only call once (cached)
                    assert mock_get.call_count == 1
                    assert description1 == description2


class TestQwenCodeCLIAgentMCPIntegration:
    """Test QwenCodeCLIAgent MCP integration"""

    @pytest.mark.asyncio
    async def test_qwen_agent_mcp_disabled(self):
        """Test that MCP is disabled when enable_mcp is False"""
        config = {"enable_mcp": False}

        # Mock CLI check to avoid requiring qwen binary
        with patch.object(QwenCodeCLIAgent, "_check_cli_available"):
            agent = QwenCodeCLIAgent(config=config)

            # QwenCodeCLIAgent uses built-in qwen CLI MCP client, not Python MCP tools
            assert agent.enable_mcp is False
            assert not hasattr(agent, "get_mcp_tools_description")

    @pytest.mark.asyncio
    async def test_qwen_agent_mcp_enabled(self):
        """Test that MCP is enabled when enable_mcp is True"""
        config = {"enable_mcp": True, "user_id": 12345}

        with patch.object(QwenCodeCLIAgent, "_check_cli_available"):
            agent = QwenCodeCLIAgent(config=config)

            # QwenCodeCLIAgent uses built-in qwen CLI MCP client, not Python MCP tools
            assert agent.enable_mcp is True
            assert agent.user_id == 12345
            assert not hasattr(agent, "get_mcp_tools_description")

    @pytest.mark.asyncio
    async def test_qwen_agent_uses_qwen_native_mcp(self):
        """Test that QwenCodeCLIAgent uses qwen native MCP, not Python MCP tools"""
        config = {"enable_mcp": True, "user_id": 12345}

        with patch.object(QwenCodeCLIAgent, "_check_cli_available"):
            agent = QwenCodeCLIAgent(config=config)

            # QwenCodeCLIAgent uses qwen CLI's built-in MCP client
            # It doesn't use Python MCP tools, so there's no get_mcp_tools_description method
            assert agent.enable_mcp is True
            assert not hasattr(agent, "get_mcp_tools_description")

            # The agent should have MCP configuration setup
            assert hasattr(agent, "_setup_qwen_mcp_config")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
