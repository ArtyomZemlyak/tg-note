"""
Agent Factory
Factory for creating agent instances based on configuration
Uses registry pattern for extensibility (Open/Closed Principle)
"""

from pathlib import Path
from loguru import logger
from typing import Dict, Optional

from .base_agent import BaseAgent
from .stub_agent import StubAgent
from .autonomous_agent import AutonomousAgent
from .qwen_code_cli_agent import QwenCodeCLIAgent
from .llm_connectors import OpenAIConnector
from .agent_registry import get_registry, register_agent


class AgentFactory:
    """
    Factory for creating agent instances
    
    Uses registry pattern for better extensibility:
    - New agent types can be registered without modifying this class
    - Follows Open/Closed Principle
    """
    
    @classmethod
    def create_agent(
        cls,
        agent_type: str = "stub",
        config: Optional[Dict] = None
    ) -> BaseAgent:
        """
        Create an agent instance
        
        Args:
            agent_type: Type of agent to create
            config: Configuration dictionary
        
        Returns:
            Agent instance
        
        Raises:
            ValueError: If agent_type is not supported
        """
        config = config or {}
        logger.info(f"Creating agent: {agent_type}")
        
        # Get registry
        registry = get_registry()
        
        # Create agent using registry
        return registry.create(agent_type, config)
    
    @classmethod
    def from_settings(cls, settings, user_id: Optional[int] = None) -> BaseAgent:
        """
        Create agent from application settings
        
        Args:
            settings: Settings object
            user_id: Optional user ID for per-user configuration
        
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
            "enable_mcp": settings.AGENT_ENABLE_MCP,
            "enable_mcp_memory": settings.AGENT_ENABLE_MCP_MEMORY,
            "qwen_cli_path": settings.AGENT_QWEN_CLI_PATH,
            "timeout": settings.AGENT_TIMEOUT,
            "kb_path": settings.KB_PATH,
            "kb_topics_only": settings.KB_TOPICS_ONLY,
            "user_id": user_id,
        }
        
        return cls.create_agent(
            agent_type=settings.AGENT_TYPE,
            config=config
        )


# Register default agent types
def _register_default_agents():
    """Register default agent types in the registry"""
    registry = get_registry()
    
    # Register simple agents
    registry.register("stub", agent_class=StubAgent)
    
    # Register agents with custom factories
    registry.register("autonomous", factory=_create_autonomous_agent)
    registry.register("qwen_code_cli", factory=_create_qwen_cli_agent)
    
    # Backward compatibility aliases
    registry.register("qwen_code", factory=_create_autonomous_agent)
    registry.register("openai", factory=_create_autonomous_agent)


def _create_autonomous_agent(config: Dict) -> AutonomousAgent:
    """
    Create Autonomous Agent with LLM connector
    
    Args:
        config: Configuration dictionary
    
    Returns:
        AutonomousAgent instance
    """
    # Determine which LLM connector to use
    llm_connector = None
    
    # Check if we should use OpenAI connector
    api_key = config.get("openai_api_key") or config.get("api_key")
    base_url = config.get("openai_base_url")
    model = config.get("model", "gpt-3.5-turbo")
    
    # If we have API key, create OpenAI connector
    if api_key:
        try:
            llm_connector = OpenAIConnector(
                api_key=api_key,
                base_url=base_url,
                model=model,
                config=config
            )
            logger.info(f"Using OpenAI connector with model: {model}")
        except ImportError as e:
            logger.warning(f"OpenAI connector not available: {e}")
            logger.info("Agent will use rule-based decision making")
    else:
        logger.info("No API key provided, agent will use rule-based decision making")
    
    # Determine kb_root_path based on kb_topics_only setting
    kb_path = Path(config.get("kb_path", "./knowledge_base"))
    kb_topics_only = config.get("kb_topics_only", True)
    
    if kb_topics_only:
        kb_root_path = kb_path / "topics"
        logger.info(f"Restricting agent to topics folder: {kb_root_path}")
    else:
        kb_root_path = kb_path
        logger.info(f"Agent has full access to knowledge base: {kb_root_path}")
    
    # Ensure kb_root_path exists
    try:
        kb_root_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured KB root path exists: {kb_root_path}")
    except Exception as e:
        logger.warning(f"Could not create KB root path {kb_root_path}: {e}")
    
    # Create autonomous agent
    return AutonomousAgent(
        llm_connector=llm_connector,
        config=config,
        instruction=config.get("instruction"),
        max_iterations=config.get("max_iterations", 10),
        enable_web_search=config.get("enable_web_search", True),
        enable_git=config.get("enable_git", True),
        enable_github=config.get("enable_github", True),
        enable_shell=config.get("enable_shell", False),
        enable_file_management=config.get("enable_file_management", True),
        enable_folder_management=config.get("enable_folder_management", True),
        enable_mcp=config.get("enable_mcp", False),
        enable_mcp_memory=config.get("enable_mcp_memory", False),
        kb_root_path=kb_root_path
    )


def _create_qwen_cli_agent(config: Dict) -> QwenCodeCLIAgent:
    """
    Create Qwen Code CLI agent with full configuration
    
    Args:
        config: Configuration dictionary
    
    Returns:
        QwenCodeCLIAgent instance
    """
    # Determine working_directory based on kb_topics_only setting
    working_directory = config.get("working_directory")
    if not working_directory:
        kb_path = Path(config.get("kb_path", "./knowledge_base"))
        kb_topics_only = config.get("kb_topics_only", True)
        
        if kb_topics_only:
            working_directory_path = kb_path / "topics"
            working_directory = str(working_directory_path)
            logger.info(f"Restricting Qwen CLI agent to topics folder: {working_directory}")
        else:
            working_directory_path = kb_path
            working_directory = str(kb_path)
            logger.info(f"Qwen CLI agent has full access to knowledge base: {working_directory}")
        
        # Ensure working directory exists
        try:
            working_directory_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured working directory exists: {working_directory}")
        except Exception as e:
            logger.warning(f"Could not create working directory {working_directory}: {e}")
    
    return QwenCodeCLIAgent(
        config=config,
        instruction=config.get("instruction"),
        qwen_cli_path=config.get("qwen_cli_path", "qwen"),
        working_directory=working_directory,
        enable_web_search=config.get("enable_web_search", True),
        enable_git=config.get("enable_git", True),
        enable_github=config.get("enable_github", True),
        timeout=config.get("timeout", 300)
    )


# Register default agents on module import
_register_default_agents()
