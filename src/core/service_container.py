"""
Service Container
Configures and wires up all services with dependency injection
"""

from loguru import logger

from config import settings
from src.core.container import Container
from src.tracker.processing_tracker import ProcessingTracker
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings
from src.bot.settings_manager import SettingsManager, UserSettingsStorage
from src.bot.telegram_bot import TelegramBot
from src.services.user_context_manager import UserContextManager
from src.services.conversation_context import ConversationContextManager
from src.services.note_creation_service import NoteCreationService
from src.services.question_answering_service import QuestionAnsweringService
from src.services.agent_task_service import AgentTaskService
from src.services.message_processor import MessageProcessor
from src.agents.mcp.server_manager import MCPServerManager
from telebot.async_telebot import AsyncTeleBot


def configure_services(container: Container) -> None:
    """
    Configure all services in the container
    
    Args:
        container: Dependency injection container
    """
    logger.info("Configuring services...")
    
    # Register singleton instances
    container.register_instance("settings", settings)
    
    # Register MCP server manager
    container.register(
        "mcp_server_manager",
        lambda c: MCPServerManager(c.get("settings")),
        singleton=True
    )
    
    # Register infrastructure services
    container.register(
        "tracker",
        lambda c: ProcessingTracker(str(c.get("settings").PROCESSED_LOG_PATH)),
        singleton=True
    )
    
    container.register(
        "repo_manager",
        lambda c: RepositoryManager(base_path=str(c.get("settings").KB_PATH)),
        singleton=True
    )
    
    container.register(
        "user_settings",
        lambda c: UserSettings(settings_file="./data/user_settings.json"),
        singleton=True
    )
    
    container.register(
        "user_settings_storage",
        lambda c: UserSettingsStorage(storage_file="./data/user_settings_overrides.json"),
        singleton=True
    )
    
    container.register(
        "settings_manager",
        lambda c: SettingsManager(
            global_settings=c.get("settings"),
            user_storage=c.get("user_settings_storage")
        ),
        singleton=True
    )
    
    # Register conversation context manager
    container.register(
        "conversation_context_manager",
        lambda c: ConversationContextManager(
            storage_file="./data/conversation_contexts.json",
            default_max_tokens=c.get("settings").CONTEXT_MAX_TOKENS
        ),
        singleton=True
    )
    
    # Register bot
    container.register(
        "async_bot",
        lambda c: AsyncTeleBot(c.get("settings").TELEGRAM_BOT_TOKEN),
        singleton=True
    )
    
    # Register business logic services
    container.register(
        "user_context_manager",
        lambda c: UserContextManager(
            settings_manager=c.get("settings_manager"),
            conversation_context_manager=c.get("conversation_context_manager"),
            timeout_callback=None  # Will be set later by message processor
        ),
        singleton=True
    )
    
    container.register(
        "note_creation_service",
        lambda c: NoteCreationService(
            bot=c.get("async_bot"),
            tracker=c.get("tracker"),
            repo_manager=c.get("repo_manager"),
            user_context_manager=c.get("user_context_manager"),
            settings_manager=c.get("settings_manager")
        ),
        singleton=True
    )
    
    container.register(
        "question_answering_service",
        lambda c: QuestionAnsweringService(
            bot=c.get("async_bot"),
            repo_manager=c.get("repo_manager"),
            user_context_manager=c.get("user_context_manager"),
            settings_manager=c.get("settings_manager")
        ),
        singleton=True
    )
    
    container.register(
        "agent_task_service",
        lambda c: AgentTaskService(
            bot=c.get("async_bot"),
            repo_manager=c.get("repo_manager"),
            user_context_manager=c.get("user_context_manager"),
            settings_manager=c.get("settings_manager")
        ),
        singleton=True
    )
    
    container.register(
        "message_processor",
        lambda c: MessageProcessor(
            bot=c.get("async_bot"),
            user_context_manager=c.get("user_context_manager"),
            user_settings=c.get("user_settings"),
            note_creation_service=c.get("note_creation_service"),
            question_answering_service=c.get("question_answering_service"),
            agent_task_service=c.get("agent_task_service")
        ),
        singleton=True
    )
    
    # Register telegram bot (facade)
    container.register(
        "telegram_bot",
        lambda c: TelegramBot(
            bot=c.get("async_bot"),
            tracker=c.get("tracker"),
            repo_manager=c.get("repo_manager"),
            user_settings=c.get("user_settings"),
            settings_manager=c.get("settings_manager"),
            user_context_manager=c.get("user_context_manager"),
            message_processor=c.get("message_processor"),
        ),
        singleton=True
    )
    
    logger.info("Services configured successfully")


def create_service_container() -> Container:
    """
    Create and configure a new service container
    
    Returns:
        Configured container
    """
    container = Container()
    configure_services(container)
    return container
