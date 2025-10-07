"""
Agent Task Service
Handles free-form agent tasks in agent mode
Follows Single Responsibility Principle
"""

from pathlib import Path
from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from src.services.interfaces import IAgentTaskService, IUserContextManager
from src.processor.message_aggregator import MessageGroup
from src.processor.content_parser import ContentParser
from src.knowledge_base.repository import RepositoryManager
from src.bot.utils import escape_markdown, split_long_message
from config.agent_prompts import AGENT_MODE_INSTRUCTION


class AgentTaskService(IAgentTaskService):
    """
    Service for executing free-form agent tasks
    
    Responsibilities:
    - Parse task from message
    - Execute task with full agent autonomy
    - Return results to user (answer, modifications, etc.)
    """
    
    def __init__(
        self,
        bot: AsyncTeleBot,
        repo_manager: RepositoryManager,
        user_context_manager: IUserContextManager,
        settings_manager
    ):
        """
        Initialize agent task service
        
        Args:
            bot: Telegram bot instance
            repo_manager: Repository manager
            user_context_manager: User context manager
            settings_manager: Settings manager for user-specific settings
        """
        self.bot = bot
        self.repo_manager = repo_manager
        self.user_context_manager = user_context_manager
        self.settings_manager = settings_manager
        self.content_parser = ContentParser()
        self.logger = logger
    
    async def execute_task(
        self,
        group: MessageGroup,
        processing_msg: Message,
        user_id: int,
        user_kb: dict
    ) -> None:
        """
        Execute a free-form agent task
        
        Args:
            group: Message group containing the task
            processing_msg: Processing status message
            user_id: User ID
            user_kb: User's knowledge base configuration
        """
        try:
            # Get KB path
            kb_path = self.repo_manager.get_kb_path(user_kb['kb_name'])
            if not kb_path:
                await self.bot.edit_message_text(
                    "❌ Локальная копия базы знаний не найдена\n\n"
                    "Попробуйте настроить базу знаний заново: /setkb",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Parse task
            content = await self.content_parser.parse_group_with_files(group, bot=self.bot)
            task_text = content.get('text', '')
            
            if not task_text:
                await self.bot.edit_message_text(
                    "❌ Не могу определить задачу\n\n"
                    "Пожалуйста, отправьте текстовое сообщение с описанием задачи.",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Execute task with agent
            await self.bot.edit_message_text(
                "🤖 Выполняю задачу...",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            
            result = await self._execute_with_agent(kb_path, content, user_id)
            
            # Send result to user
            await self._send_result(processing_msg, result)
            
        except Exception as e:
            self.logger.error(f"Error in agent task execution: {e}", exc_info=True)
            await self._send_error_notification(processing_msg, str(e))
    
    async def _execute_with_agent(
        self,
        kb_path: Path,
        content: dict,
        user_id: int
    ) -> dict:
        """
        Execute task with agent
        
        Args:
            kb_path: Path to knowledge base
            content: Task content
            user_id: User ID
        
        Returns:
            Agent execution result
        """
        # Get user agent
        user_agent = self.user_context_manager.get_or_create_agent(user_id)
        
        # Set working directory to user's KB
        # Use KB_TOPICS_ONLY setting to determine if we should restrict to topics/ folder
        kb_topics_only = self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY")
        
        if kb_topics_only:
            # Restrict to topics folder (protects index.md, README.md, etc.)
            agent_working_dir = kb_path / "topics"
            self.logger.debug(f"KB_TOPICS_ONLY=true, restricting agent to topics folder")
        else:
            # Full access to entire knowledge base
            agent_working_dir = kb_path
            self.logger.debug(f"KB_TOPICS_ONLY=false, agent has full KB access")
        
        if hasattr(user_agent, 'set_working_directory'):
            user_agent.set_working_directory(str(agent_working_dir))
            self.logger.debug(f"Set agent working directory to: {agent_working_dir}")
        
        # Temporarily change agent instruction to agent mode
        original_instruction = None
        if hasattr(user_agent, 'get_instruction') and hasattr(user_agent, 'set_instruction'):
            original_instruction = user_agent.get_instruction()
            user_agent.set_instruction(AGENT_MODE_INSTRUCTION)
            self.logger.debug(f"Temporarily changed agent instruction to agent mode")
        
        # Prepare task content with agent mode instruction
        task_content = {
            'text': content.get('text', ''),
            'urls': content.get('urls', []),
            'prompt': f"{AGENT_MODE_INSTRUCTION}\n\n# Задача от пользователя:\n{content.get('text', '')}"
        }
        
        try:
            # Process task with agent
            response = await user_agent.process(task_content)
            
            # Extract result from response
            # Priority: answer field, then metadata, then summary
            result = {
                'answer': response.get('answer'),
                'summary': response.get('summary', ''),
                'metadata': response.get('metadata', {}),
                'files_created': response.get('metadata', {}).get('files_created', []),
                'files_edited': response.get('metadata', {}).get('files_edited', []),
                'files_deleted': response.get('metadata', {}).get('files_deleted', []),
                'folders_created': response.get('metadata', {}).get('folders_created', []),
            }
            
            return result
            
        except Exception as agent_error:
            self.logger.error(f"Agent task execution failed: {agent_error}", exc_info=True)
            raise RuntimeError(
                f"Ошибка при выполнении задачи: {str(agent_error)}\n\n"
                f"Попробуйте переформулировать задачу или проверьте настройки агента."
            )
        finally:
            # Restore original instruction
            if original_instruction is not None and hasattr(user_agent, 'set_instruction'):
                user_agent.set_instruction(original_instruction)
                self.logger.debug(f"Restored original agent instruction")
    
    async def _send_result(
        self,
        processing_msg: Message,
        result: dict
    ) -> None:
        """
        Send task result to user
        
        Args:
            processing_msg: Processing status message
            result: Task execution result
        """
        # Build result message
        message_parts = []
        
        # If there's an answer (e.g., user asked a question)
        if result.get('answer'):
            message_parts.append("💡 **Ответ:**\n")
            message_parts.append(result['answer'])
            message_parts.append("\n")
        
        # Add summary
        if result.get('summary'):
            message_parts.append(f"📋 **Выполнено:** {result['summary']}\n")
        
        # Add file operations
        files_created = result.get('files_created', [])
        files_edited = result.get('files_edited', [])
        files_deleted = result.get('files_deleted', [])
        folders_created = result.get('folders_created', [])
        
        if files_created or files_edited or files_deleted or folders_created:
            message_parts.append("\n📝 **Изменения:**\n")
            
            if files_created:
                message_parts.append(f"✨ Создано файлов: {len(files_created)}\n")
                for file in files_created[:5]:
                    message_parts.append(f"  • {file}\n")
                if len(files_created) > 5:
                    message_parts.append(f"  • ... и ещё {len(files_created) - 5}\n")
            
            if files_edited:
                message_parts.append(f"✏️ Изменено файлов: {len(files_edited)}\n")
                for file in files_edited[:5]:
                    message_parts.append(f"  • {file}\n")
                if len(files_edited) > 5:
                    message_parts.append(f"  • ... и ещё {len(files_edited) - 5}\n")
            
            if files_deleted:
                message_parts.append(f"🗑️ Удалено файлов: {len(files_deleted)}\n")
                for file in files_deleted[:5]:
                    message_parts.append(f"  • {file}\n")
                if len(files_deleted) > 5:
                    message_parts.append(f"  • ... и ещё {len(files_deleted) - 5}\n")
            
            if folders_created:
                message_parts.append(f"📁 Создано папок: {len(folders_created)}\n")
                for folder in folders_created[:5]:
                    message_parts.append(f"  • {folder}\n")
                if len(folders_created) > 5:
                    message_parts.append(f"  • ... и ещё {len(folders_created) - 5}\n")
        
        # Build final message
        full_message = "".join(message_parts)
        if not full_message.strip():
            full_message = "✅ Задача выполнена!"
        
        # Escape markdown to prevent parsing errors
        escaped_message = escape_markdown(full_message)
        
        # Handle long messages by splitting them
        message_chunks = split_long_message(escaped_message)
        
        try:
            # Edit the processing message with the first chunk
            await self.bot.edit_message_text(
                message_chunks[0],
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                parse_mode='Markdown'
            )
            
            # If there are more chunks, send them as separate messages
            for i, chunk in enumerate(message_chunks[1:], start=2):
                await self.bot.send_message(
                    chat_id=processing_msg.chat.id,
                    text=f"💡 **(часть {i}/{len(message_chunks)}):**\n\n{chunk}",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            # If Markdown parsing fails, send without formatting
            if "can't parse entities" in str(e).lower():
                self.logger.warning(f"Markdown parsing failed, sending without formatting: {e}")
                
                full_message_plain = "".join(message_parts)
                message_chunks_plain = split_long_message(full_message_plain)
                
                await self.bot.edit_message_text(
                    message_chunks_plain[0],
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id,
                    parse_mode=None
                )
                
                for i, chunk in enumerate(message_chunks_plain[1:], start=2):
                    await self.bot.send_message(
                        chat_id=processing_msg.chat.id,
                        text=f"(часть {i}/{len(message_chunks_plain)}):\n\n{chunk}",
                        parse_mode=None
                    )
            else:
                raise
    
    async def _send_error_notification(
        self,
        processing_msg: Message,
        error_message: str
    ) -> None:
        """Send error notification"""
        try:
            await self.bot.edit_message_text(
                f"❌ Ошибка выполнения задачи: {error_message}",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
        except Exception:
            pass
