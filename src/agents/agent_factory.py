"""
Agent Factory
Factory for creating agent instances based on configuration
"""

from loguru import logger
from typing import Dict, Optional

from .base_agent import BaseAgent
from .stub_agent import StubAgent
from .qwen_code_agent import QwenCodeAgent
from .qwen_code_cli_agent import QwenCodeCLIAgent
from .openai_agent import OpenAIAgent




class AgentFactory:
    """Factory for creating agent instances"""
    
    AGENT_TYPES = {
        "stub": StubAgent,
        "qwen_code": QwenCodeAgent,
        "qwen_code_cli": QwenCodeCLIAgent,
        "openai": OpenAIAgent,
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
        elif agent_type == "qwen_code_cli":
            return cls._create_qwen_cli_agent(config)
        elif agent_type == "openai":
            return cls._create_openai_agent(config)
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
        from pathlib import Path
        
        return QwenCodeAgent(
            config=config,
            instruction=config.get("instruction"),
            api_key=config.get("api_key"),
            model=config.get("model", "qwen-max"),
            enable_web_search=config.get("enable_web_search", True),
            enable_git=config.get("enable_git", True),
            enable_github=config.get("enable_github", True),
            enable_shell=config.get("enable_shell", False),
            enable_file_management=config.get("enable_file_management", True),
            enable_folder_management=config.get("enable_folder_management", True),
            kb_root_path=Path(config.get("kb_path", "./knowledge_base")),
            max_iterations=config.get("max_iterations", 10)
        )
    
    @classmethod
    def _create_qwen_cli_agent(cls, config: Dict) -> QwenCodeCLIAgent:
        """
        Create Qwen Code CLI agent with full configuration
        
        Args:
            config: Configuration dictionary
        
        Returns:
            QwenCodeCLIAgent instance
        """
        return QwenCodeCLIAgent(
            config=config,
            instruction=config.get("instruction"),
            qwen_cli_path=config.get("qwen_cli_path", "qwen"),
            working_directory=config.get("working_directory"),
            enable_web_search=config.get("enable_web_search", True),
            enable_git=config.get("enable_git", True),
            enable_github=config.get("enable_github", True),
            timeout=config.get("timeout", 300),
            kb_root_path=config.get("kb_path", "./knowledge_base")
        )
    
    @classmethod
    def _create_openai_agent(cls, config: Dict) -> OpenAIAgent:
        """
        Create OpenAI Agent with full configuration
        
        Args:
            config: Configuration dictionary
        
        Returns:
            OpenAIAgent instance
        """
        from pathlib import Path
        
        return OpenAIAgent(
            config=config,
            instruction=config.get("instruction"),
            api_key=config.get("openai_api_key") or config.get("api_key"),
            base_url=config.get("openai_base_url"),
            model=config.get("model", "qwen-max"),
            max_iterations=config.get("max_iterations", 10),
            kb_root_path=Path(config.get("kb_path", "./knowledge_base"))
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
            "openai_api_key": settings.OPENAI_API_KEY,
            "openai_base_url": settings.OPENAI_BASE_URL,
            "github_token": settings.GITHUB_TOKEN,
            "model": settings.AGENT_MODEL,
            "instruction": settings.AGENT_INSTRUCTION,
            "enable_web_search": settings.AGENT_ENABLE_WEB_SEARCH,
            "enable_git": settings.AGENT_ENABLE_GIT,
            "enable_github": settings.AGENT_ENABLE_GITHUB,
            "enable_shell": settings.AGENT_ENABLE_SHELL,
            "enable_file_management": settings.AGENT_ENABLE_FILE_MANAGEMENT,
            "enable_folder_management": settings.AGENT_ENABLE_FOLDER_MANAGEMENT,
            "qwen_cli_path": settings.AGENT_QWEN_CLI_PATH,
            "timeout": settings.AGENT_TIMEOUT,
            "kb_path": settings.KB_PATH,
        }
        
        return cls.create_agent(
            agent_type=settings.AGENT_TYPE,
            config=config
        )
