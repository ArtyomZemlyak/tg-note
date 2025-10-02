"""
Tests for Agent Factory
"""

import pytest
from unittest.mock import MagicMock
from src.agents.agent_factory import AgentFactory
from src.agents.stub_agent import StubAgent
from src.agents.qwen_code_agent import QwenCodeAgent
from src.agents.base_agent import BaseAgent


class TestAgentFactory:
    """Test AgentFactory class"""
    
    def test_create_stub_agent(self):
        """Test creating stub agent"""
        agent = AgentFactory.create_agent("stub")
        
        assert isinstance(agent, StubAgent)
        assert isinstance(agent, BaseAgent)
    
    def test_create_qwen_agent(self):
        """Test creating Qwen Code agent"""
        config = {
            "model": "qwen-max",
            "enable_web_search": True,
            "enable_git": True,
            "enable_github": True,
            "enable_shell": False
        }
        
        agent = AgentFactory.create_agent("qwen_code", config)
        
        assert isinstance(agent, QwenCodeAgent)
        assert isinstance(agent, BaseAgent)
        assert agent.model == "qwen-max"
    
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
        mock_settings.AGENT_QWEN_CLI_PATH = "qwen"
        mock_settings.AGENT_TIMEOUT = 300
        
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
        mock_settings.AGENT_QWEN_CLI_PATH = "qwen"
        mock_settings.AGENT_TIMEOUT = 300
        
        agent = AgentFactory.from_settings(mock_settings)
        
        assert isinstance(agent, QwenCodeAgent)
        assert agent.api_key == "test-key"
        assert agent.model == "qwen-plus"
        assert agent.instruction == "Custom instruction"
        assert not agent.enable_web_search
        assert agent.enable_git
        assert not agent.enable_github
        assert not agent.enable_shell
    
    def test_agent_types_registered(self):
        """Test that all agent types are registered"""
        assert "stub" in AgentFactory.AGENT_TYPES
        assert "qwen_code" in AgentFactory.AGENT_TYPES
        assert AgentFactory.AGENT_TYPES["stub"] == StubAgent
        assert AgentFactory.AGENT_TYPES["qwen_code"] == QwenCodeAgent
    
    def test_qwen_agent_default_config(self):
        """Test Qwen agent with default configuration"""
        config = {}
        agent = AgentFactory.create_agent("qwen_code", config)
        
        assert agent.model == "qwen-max"  # Default model
        assert agent.enable_web_search  # Default True
        assert agent.enable_git  # Default True
        assert agent.enable_github  # Default True
        assert not agent.enable_shell  # Default False
    
    def test_qwen_agent_partial_config(self):
        """Test Qwen agent with partial configuration"""
        config = {
            "model": "qwen-turbo",
            "enable_shell": True
        }
        agent = AgentFactory.create_agent("qwen_code", config)
        
        assert agent.model == "qwen-turbo"
        assert agent.enable_shell
        # Other settings should use defaults
        assert agent.enable_web_search
