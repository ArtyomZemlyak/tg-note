"""
User Context Manager Service
Manages user-specific contexts (aggregators, agents, modes, conversation context)
Follows Single Responsibility Principle
"""

from typing import Any, Dict, Optional
from loguru import logger

from src.services.interfaces import IUserContextManager
from src.processor.message_aggregator import MessageAggregator
from src.agents.agent_factory import AgentFactory
from src.bot.settings_manager import SettingsManager
from src.services.conversation_context import ConversationContextManager
from src.core.background_task_manager import BackgroundTaskManager


class UserContextManager(IUserContextManager):
    """
    Manages user-specific contexts
    
    Responsibilities:
    - Create and cache user-specific message aggregators
    - Create and cache user-specific agents
    - Manage user modes (note/ask)
    - Invalidate user caches when settings change
    - Управление жизненным циклом агрегаторов через BackgroundTaskManager
    """
    
    def __init__(
        self,
        settings_manager: SettingsManager,
        conversation_context_manager: ConversationContextManager,
        background_task_manager: Optional[BackgroundTaskManager] = None,
        timeout_callback=None
    ):
        """
        Initialize user context manager
        
        Args:
            settings_manager: Settings manager for user-specific settings
            conversation_context_manager: Manager for conversation contexts
            background_task_manager: Централизованный менеджер фоновых задач
            timeout_callback: Callback for message aggregator timeouts
        """
        self.settings_manager = settings_manager
        self.conversation_context_manager = conversation_context_manager
        self.background_task_manager = background_task_manager
        self.timeout_callback = timeout_callback
        
        # User-specific caches
        self.user_aggregators: Dict[int, MessageAggregator] = {}
        self.user_agents: Dict[int, Any] = {}
        self.user_modes: Dict[int, str] = {}
        
        self.logger = logger
        self.logger.info("UserContextManager initialized")
    
    def get_or_create_aggregator(self, user_id: int) -> MessageAggregator:
        """
        Get or create message aggregator for a user
        
        Args:
            user_id: User ID
        
        Returns:
            MessageAggregator instance for the user
        """
        if user_id not in self.user_aggregators:
            timeout = self.settings_manager.get_setting(user_id, "MESSAGE_GROUP_TIMEOUT")
            self.logger.info(f"Creating MessageAggregator for user {user_id} with timeout {timeout}s")
            
            # Создать агрегатор с поддержкой BackgroundTaskManager
            aggregator = MessageAggregator(
                timeout=timeout,
                user_id=user_id,
                task_manager=self.background_task_manager
            )
            if self.timeout_callback:
                aggregator.set_timeout_callback(self.timeout_callback)
            
            # Запустить фоновую задачу (будет управляться через BackgroundTaskManager)
            aggregator.start_background_task()
            
            self.user_aggregators[user_id] = aggregator
        
        return self.user_aggregators[user_id]
    
    def get_or_create_agent(self, user_id: int):
        """
        Get or create agent for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Agent instance for the user
        """
        if user_id not in self.user_agents:
            # Get user-specific agent settings
            config = {
                "api_key": self.settings_manager.get_setting(user_id, "QWEN_API_KEY"),
                "openai_api_key": self.settings_manager.get_setting(user_id, "OPENAI_API_KEY"),
                "openai_base_url": self.settings_manager.get_setting(user_id, "OPENAI_BASE_URL"),
                "github_token": self.settings_manager.get_setting(user_id, "GITHUB_TOKEN"),
                "model": self.settings_manager.get_setting(user_id, "AGENT_MODEL"),
                "instruction": self.settings_manager.get_setting(user_id, "AGENT_INSTRUCTION"),
                "enable_web_search": self.settings_manager.get_setting(user_id, "AGENT_ENABLE_WEB_SEARCH"),
                "enable_git": self.settings_manager.get_setting(user_id, "AGENT_ENABLE_GIT"),
                "enable_github": self.settings_manager.get_setting(user_id, "AGENT_ENABLE_GITHUB"),
                "enable_shell": self.settings_manager.get_setting(user_id, "AGENT_ENABLE_SHELL"),
                "enable_mcp": self.settings_manager.get_setting(user_id, "AGENT_ENABLE_MCP"),
                "enable_mcp_memory": self.settings_manager.get_setting(user_id, "AGENT_ENABLE_MCP_MEMORY"),
                "qwen_cli_path": self.settings_manager.get_setting(user_id, "AGENT_QWEN_CLI_PATH"),
                "timeout": self.settings_manager.get_setting(user_id, "AGENT_TIMEOUT"),
                "kb_path": self.settings_manager.get_setting(user_id, "KB_PATH"),
                "kb_topics_only": self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY"),
                "user_id": user_id,  # Pass user_id for per-user MCP server discovery
            }
            
            agent_type = self.settings_manager.get_setting(user_id, "AGENT_TYPE")
            self.logger.info(f"Creating agent for user {user_id}: {agent_type}")
            
            agent = AgentFactory.create_agent(agent_type=agent_type, config=config)
            self.user_agents[user_id] = agent
        
        return self.user_agents[user_id]
    
    def get_user_mode(self, user_id: int) -> str:
        """
        Get current mode for user
        
        Args:
            user_id: User ID
        
        Returns:
            User mode ('note' or 'ask')
        """
        return self.user_modes.get(user_id, "note")
    
    def set_user_mode(self, user_id: int, mode: str) -> None:
        """
        Set mode for user
        
        Args:
            user_id: User ID
            mode: Mode to set ('note' or 'ask')
        """
        self.user_modes[user_id] = mode
        self.logger.info(f"User {user_id} switched to {mode} mode")
    
    def get_conversation_context(self, user_id: int) -> str:
        """
        Get formatted conversation context for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Formatted context string
        """
        context_enabled = self.settings_manager.get_setting(user_id, "CONTEXT_ENABLED")
        return self.conversation_context_manager.get_context_for_prompt(user_id, context_enabled)
    
    def add_user_message_to_context(
        self,
        user_id: int,
        message_id: int,
        content: str,
        timestamp: int
    ) -> None:
        """
        Add user message to conversation context
        
        Args:
            user_id: User ID
            message_id: Message ID
            content: Message content
            timestamp: Message timestamp
        """
        max_tokens = self.settings_manager.get_setting(user_id, "CONTEXT_MAX_TOKENS")
        self.conversation_context_manager.add_user_message(
            user_id, message_id, content, timestamp, max_tokens
        )
    
    def add_assistant_message_to_context(
        self,
        user_id: int,
        message_id: int,
        content: str,
        timestamp: int
    ) -> None:
        """
        Add assistant message to conversation context
        
        Args:
            user_id: User ID
            message_id: Message ID
            content: Message content
            timestamp: Message timestamp
        """
        max_tokens = self.settings_manager.get_setting(user_id, "CONTEXT_MAX_TOKENS")
        self.conversation_context_manager.add_assistant_message(
            user_id, message_id, content, timestamp, max_tokens
        )
    
    def reset_conversation_context(self, user_id: int, from_message_id: int) -> None:
        """
        Reset conversation context from a specific message
        
        Args:
            user_id: User ID
            from_message_id: Start reading context from this message
        """
        self.conversation_context_manager.reset_context(user_id, from_message_id)
    
    def clear_conversation_context(self, user_id: int) -> None:
        """
        Completely clear conversation context for a user
        
        Args:
            user_id: User ID
        """
        self.conversation_context_manager.clear_context(user_id)
    
    async def invalidate_cache(self, user_id: int) -> None:
        """
        Invalidate cached user-specific components
        
        Args:
            user_id: User ID
        """
        self.logger.info(f"Invalidating cache for user {user_id}")
        
        # Stop and remove user's message aggregator
        if user_id in self.user_aggregators:
            await self.user_aggregators[user_id].stop_background_task()
            del self.user_aggregators[user_id]
        
        # Remove user's agent
        if user_id in self.user_agents:
            del self.user_agents[user_id]
    
    async def cleanup(self) -> None:
        """Cleanup all user contexts"""
        self.logger.info("Cleaning up all user contexts")
        
        # Stop all user aggregators
        import asyncio
        await asyncio.gather(
            *[aggregator.stop_background_task() for aggregator in self.user_aggregators.values()],
            return_exceptions=True
        )
        
        self.user_aggregators.clear()
        self.user_agents.clear()
        self.user_modes.clear()
