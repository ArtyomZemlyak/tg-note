"""
Tests for MCP tools description functionality

Verifies that agents can discover and describe available MCP tools.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.autonomous_agent import AutonomousAgent
from src.agents.mcp.tools_description import format_mcp_tools_for_prompt, get_mcp_tools_description
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent


class TestMCPToolsDescription:
    """Test MCP tools description generation"""

    @pytest.mark.asyncio
    async def test_get_mcp_tools_description_no_servers(self):
        """Test description generation when no MCP servers are available"""
        # Mock registry client to return no servers
        with patch("src.agents.mcp.tools_description.MCPRegistryClient") as mock_registry:
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

        with patch("src.agents.mcp.tools_description.MCPRegistryClient") as mock_registry:
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
        agent = AutonomousAgent(config=config, enable_mcp=True)

        # Mock the MCP description function
        with patch("src.agents.autonomous_agent.get_mcp_tools_description") as mock_get:
            mock_get.return_value = "# Test MCP Tools"

            with patch("src.agents.autonomous_agent.format_mcp_tools_for_prompt") as mock_format:
                mock_format.return_value = "## MCP Tools Available\n\n# Test MCP Tools"

                description = await agent.get_mcp_tools_description()

                # Should call the functions with correct parameters
                mock_get.assert_called_once_with(user_id=12345)
                mock_format.assert_called_once_with("# Test MCP Tools", include_in_system=True)

                # Should cache the result
                assert agent._mcp_tools_description == "## MCP Tools Available\n\n# Test MCP Tools"

    @pytest.mark.asyncio
    async def test_autonomous_agent_caches_mcp_description(self):
        """Test that MCP tools description is cached"""
        config = {"enable_mcp": True}
        agent = AutonomousAgent(config=config, enable_mcp=True)

        with patch("src.agents.autonomous_agent.get_mcp_tools_description") as mock_get:
            mock_get.return_value = "# Test MCP Tools"

            with patch("src.agents.autonomous_agent.format_mcp_tools_for_prompt") as mock_format:
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
    async def test_qwen_agent_get_mcp_tools_disabled(self):
        """Test that MCP tools description is empty when MCP is disabled"""
        config = {"enable_mcp": False}

        # Mock CLI check to avoid requiring qwen binary
        with patch.object(QwenCodeCLIAgent, "_check_cli_available"):
            agent = QwenCodeCLIAgent(config=config)

            description = await agent.get_mcp_tools_description()

            assert description == ""
            assert agent._mcp_tools_description == ""

    @pytest.mark.asyncio
    async def test_qwen_agent_get_mcp_tools_enabled(self):
        """Test that MCP tools description is generated when enabled"""
        config = {"enable_mcp": True, "user_id": 12345}

        with patch.object(QwenCodeCLIAgent, "_check_cli_available"):
            agent = QwenCodeCLIAgent(config=config)

            # Mock the MCP description function
            with patch("src.agents.qwen_code_cli_agent.get_mcp_tools_description") as mock_get:
                mock_get.return_value = "# Test MCP Tools"

                with patch(
                    "src.agents.qwen_code_cli_agent.format_mcp_tools_for_prompt"
                ) as mock_format:
                    mock_format.return_value = "\n---\n\n# Test MCP Tools"

                    description = await agent.get_mcp_tools_description()

                    # Should call the functions with correct parameters
                    mock_get.assert_called_once_with(user_id=12345)
                    mock_format.assert_called_once_with("# Test MCP Tools", include_in_system=False)

                    # Should cache the result
                    assert agent._mcp_tools_description == "\n---\n\n# Test MCP Tools"

    @pytest.mark.asyncio
    async def test_qwen_agent_includes_mcp_in_prompt(self):
        """Test that MCP tools are included in prompt"""
        config = {"enable_mcp": True, "user_id": 12345}

        with patch.object(QwenCodeCLIAgent, "_check_cli_available"):
            agent = QwenCodeCLIAgent(config=config)

            # Mock MCP description
            with patch.object(agent, "get_mcp_tools_description") as mock_get_mcp:
                mock_get_mcp.return_value = "\n\n## MCP Tools\n\ntest_tool available"

                content = {"text": "Test content"}

                prompt = await agent._prepare_prompt_async(content)

                # Should include MCP description
                assert "MCP Tools" in prompt
                assert "test_tool available" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
