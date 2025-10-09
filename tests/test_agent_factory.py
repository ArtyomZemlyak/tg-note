"""
Tests for Agent Factory
"""

from unittest.mock import MagicMock

import pytest

from src.agents import AutonomousAgent, QwenCodeAgent  # QwenCodeAgent is now alias
from src.agents.agent_factory import AgentFactory
from src.agents.base_agent import BaseAgent
from src.agents.stub_agent import StubAgent


class TestAgentFactory:
    """Test AgentFactory class"""

    def test_create_stub_agent(self):
        """Test creating stub agent"""
        agent = AgentFactory.create_agent("stub")

        assert isinstance(agent, StubAgent)
        assert isinstance(agent, BaseAgent)

    def test_create_qwen_agent(self):
        """Test creating Qwen Code agent (now AutonomousAgent)"""
        config = {
            "model": "qwen-max",
            "enable_web_search": True,
            "enable_git": True,
            "enable_github": True,
            "enable_shell": False,
        }

        agent = AgentFactory.create_agent("qwen_code", config)

        assert isinstance(agent, AutonomousAgent)
        assert isinstance(agent, QwenCodeAgent)  # QwenCodeAgent is alias
        assert isinstance(agent, BaseAgent)

    def test_create_unknown_agent(self):
        """Test creating unknown agent type"""
        with pytest.raises(ValueError) as exc_info:
            AgentFactory.create_agent("unknown_type")

        assert "Unknown agent type" in str(exc_info.value)

    def test_create_agent_with_config(self):
        """Test creating agent with configuration"""
        config = {"test_key": "test_value"}
        agent = AgentFactory.create_agent("stub", config)

        assert agent.config == config

    def test_create_agent_without_config(self):
        """Test creating agent without configuration"""
        agent = AgentFactory.create_agent("stub")

        assert agent.config == {}

    def test_from_settings_stub(self):
        """Test creating agent from settings (stub)"""
        mock_settings = MagicMock()
        mock_settings.AGENT_TYPE = "stub"
        mock_settings.QWEN_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        mock_settings.OPENAI_BASE_URL = None
        mock_settings.GITHUB_TOKEN = None
        mock_settings.AGENT_MODEL = "qwen-max"
        mock_settings.AGENT_INSTRUCTION = None
        mock_settings.AGENT_ENABLE_WEB_SEARCH = True
        mock_settings.AGENT_ENABLE_GIT = True
        mock_settings.AGENT_ENABLE_GITHUB = True
        mock_settings.AGENT_ENABLE_SHELL = False
        mock_settings.AGENT_ENABLE_FILE_MANAGEMENT = True
        mock_settings.AGENT_ENABLE_FOLDER_MANAGEMENT = True
        mock_settings.AGENT_ENABLE_MCP = False
        mock_settings.AGENT_ENABLE_MCP_MEMORY = False
        mock_settings.AGENT_QWEN_CLI_PATH = "qwen"
        mock_settings.AGENT_TIMEOUT = 300
        mock_settings.KB_PATH = "./knowledge_base"
        mock_settings.KB_TOPICS_ONLY = True

        agent = AgentFactory.from_settings(mock_settings)

        assert isinstance(agent, StubAgent)

    def test_from_settings_qwen(self):
        """Test creating agent from settings (Qwen)"""
        mock_settings = MagicMock()
        mock_settings.AGENT_TYPE = "qwen_code"
        mock_settings.QWEN_API_KEY = "test-key"
        mock_settings.OPENAI_API_KEY = None
        mock_settings.OPENAI_BASE_URL = None
        mock_settings.GITHUB_TOKEN = "github-token"
        mock_settings.AGENT_MODEL = "qwen-plus"
        mock_settings.AGENT_INSTRUCTION = "Custom instruction"
        mock_settings.AGENT_ENABLE_WEB_SEARCH = False
        mock_settings.AGENT_ENABLE_GIT = True
        mock_settings.AGENT_ENABLE_GITHUB = False
        mock_settings.AGENT_ENABLE_SHELL = False
        mock_settings.AGENT_ENABLE_FILE_MANAGEMENT = True
        mock_settings.AGENT_ENABLE_FOLDER_MANAGEMENT = True
        mock_settings.AGENT_ENABLE_MCP = False
        mock_settings.AGENT_ENABLE_MCP_MEMORY = False
        mock_settings.AGENT_QWEN_CLI_PATH = "qwen"
        mock_settings.AGENT_TIMEOUT = 300
        mock_settings.KB_PATH = "./knowledge_base"
        mock_settings.KB_TOPICS_ONLY = True

        agent = AgentFactory.from_settings(mock_settings)

        assert isinstance(agent, AutonomousAgent)
        assert isinstance(agent, QwenCodeAgent)  # QwenCodeAgent is alias
        assert agent.instruction == "Custom instruction"
        assert not agent.enable_web_search
        assert agent.enable_git
        assert not agent.enable_github
        assert not agent.enable_shell

    def test_agent_types_registered(self):
        """Test that all agent types are registered"""
        from src.agents.agent_registry import get_registry

        registry = get_registry()
        available_types = registry.get_available_types()

        assert "stub" in available_types
        assert "qwen_code" in available_types
        assert "autonomous" in available_types

        # Test that we can create agents of these types
        stub_agent = registry.create("stub", {})
        assert isinstance(stub_agent, StubAgent)

        autonomous_agent = registry.create("autonomous", {})
        assert isinstance(autonomous_agent, AutonomousAgent)

    def test_qwen_agent_default_config(self):
        """Test Qwen agent with default configuration"""
        config = {}
        agent = AgentFactory.create_agent("qwen_code", config)

        assert agent.enable_web_search  # Default True
        assert agent.enable_git  # Default True
        assert agent.enable_github  # Default True
        assert not agent.enable_shell  # Default False

    def test_qwen_agent_partial_config(self):
        """Test Qwen agent with partial configuration"""
        config = {"enable_shell": True}
        agent = AgentFactory.create_agent("qwen_code", config)

        assert agent.enable_shell
        # Other settings should use defaults
        assert agent.enable_web_search
