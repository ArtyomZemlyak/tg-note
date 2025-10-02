"""
Agent Factory
Factory for creating agent instances based on configuration
"""

import logging
from typing import Dict, Optional

from .base_agent import BaseAgent
from .stub_agent import StubAgent
from .qwen_code_agent import QwenCodeAgent


logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating agent instances"""
    
    AGENT_TYPES = {
        "stub": StubAgent,
        "qwen_code": QwenCodeAgent,
    }
    
    @classmethod
    def create_agent(
        cls,
        agent_type: str = "stub",
        config: Optional[Dict] = None
    ) -> BaseAgent:
        """
        Create an agent instance
        
        Args:
            agent_type: Type of agent to create (stub, qwen_code)
            config: Configuration dictionary
        
        Returns:
            Agent instance
        
        Raises:
            ValueError: If agent_type is not supported
        """
        if agent_type not in cls.AGENT_TYPES:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Supported types: {list(cls.AGENT_TYPES.keys())}"
            )
        
        agent_class = cls.AGENT_TYPES[agent_type]
        config = config or {}
        
        logger.info(f"Creating agent: {agent_type}")
        
        # Create agent with appropriate parameters
        if agent_type == "qwen_code":
            return cls._create_qwen_agent(config)
        else:
            return agent_class(config=config)
    
    @classmethod
    def _create_qwen_agent(cls, config: Dict) -> QwenCodeAgent:
        """
        Create Qwen Code agent with full configuration
        
        Args:
            config: Configuration dictionary
        
        Returns:
            QwenCodeAgent instance
        """
        return QwenCodeAgent(
            config=config,
            instruction=config.get("instruction"),
            api_key=config.get("api_key"),
            model=config.get("model", "qwen-max"),
            enable_web_search=config.get("enable_web_search", True),
            enable_git=config.get("enable_git", True),
            enable_github=config.get("enable_github", True),
            enable_shell=config.get("enable_shell", False)
        )
    
    @classmethod
    def from_settings(cls, settings) -> BaseAgent:
        """
        Create agent from application settings
        
        Args:
            settings: Settings object
        
        Returns:
            Agent instance
        """
        config = {
            "api_key": settings.QWEN_API_KEY,
            "github_token": settings.GITHUB_TOKEN,
            "model": settings.AGENT_MODEL,
            "instruction": settings.AGENT_INSTRUCTION,
            "enable_web_search": settings.AGENT_ENABLE_WEB_SEARCH,
            "enable_git": settings.AGENT_ENABLE_GIT,
            "enable_github": settings.AGENT_ENABLE_GITHUB,
            "enable_shell": settings.AGENT_ENABLE_SHELL,
        }
        
        return cls.create_agent(
            agent_type=settings.AGENT_TYPE,
            config=config
        )
