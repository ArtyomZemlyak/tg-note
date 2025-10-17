"""
Agent Task Service
Handles free-form agent tasks in agent mode
Follows Single Responsibility Principle
"""

import asyncio
from pathlib import Path

from loguru import logger

from config.agent_prompts import AGENT_MODE_INSTRUCTION
from src.bot.bot_port import BotPort
from src.bot.utils import escape_markdown, split_long_message
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.sync_manager import get_sync_manager
from src.processor.content_parser import ContentParser
from src.processor.message_aggregator import MessageGroup
from src.services.interfaces import IAgentTaskService, IUserContextManager


class AgentTaskService(IAgentTaskService):
    """
    Service for executing free-form agent tasks (agent mode).

    Responsibilities:
    - Parse task from message
    - Execute task with full agent autonomy
    - Handle any KB-related operations (read, write, restructure)
    - Return results to user (answers, file modifications, etc.)
    - Maintain conversation context for complex multi-turn tasks

    This service is activated when user is in 'agent' mode (/agent command).
    Agent has full access to the knowledge base and can perform any task.
    """

    def __init__(
        self,
        bot: BotPort,
        repo_manager: RepositoryManager,
        user_context_manager: IUserContextManager,
        settings_manager,
    ):
        """
        Initialize agent task service

        Args:
            bot: Bot messaging interface (transport abstraction)
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
        self, group: MessageGroup, processing_msg_id: int, chat_id: int, user_id: int, user_kb: dict
    ) -> None:
        """
        Execute a free-form agent task

        Args:
            group: Message group containing the task
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID where task was requested
            user_id: User ID
            user_kb: User's knowledge base configuration
        """
        try:
            # Get KB path
            kb_path = self.repo_manager.get_kb_path(user_kb["kb_name"])
            if not kb_path:
                error_text = (
                    "❌ Локальная копия базы знаний не найдена\n\n"
                    "Попробуйте настроить базу знаний заново: /setkb"
                )
                edit_succeeded = await self._safe_edit_message(
                    error_text, chat_id=chat_id, message_id=processing_msg_id
                )
                if not edit_succeeded:
                    await self.bot.send_message(chat_id=chat_id, text=error_text)
                return

            # AICODE-NOTE: Use sync manager to serialize KB operations and prevent conflicts
            # when multiple users work with the same knowledge base in agent mode
            sync_manager = get_sync_manager()
            
            # Acquire lock for this KB to ensure operations are serialized
            async with sync_manager.with_kb_lock(str(kb_path), f"agent_task_user_{user_id}"):
                await self._execute_task_locked(
                    group, processing_msg_id, chat_id, user_id, user_kb, kb_path
                )

        except Exception as e:
            self.logger.error(f"Error in agent task execution: {e}", exc_info=True)
            await self._send_error_notification(processing_msg_id, chat_id, str(e))

    async def _execute_task_locked(
        self,
        group: MessageGroup,
        processing_msg_id: int,
        chat_id: int,
        user_id: int,
        user_kb: dict,
        kb_path: Path,
    ) -> None:
        """
        Execute task with KB lock already acquired.
        This method performs the actual task execution work.

        Args:
            group: Message group containing the task
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID where task was requested
            user_id: User ID
            user_kb: User's knowledge base configuration
            kb_path: Path to knowledge base
        """
        # Parse task
        content = await self.content_parser.parse_group_with_files(group, bot=self.bot)
        task_text = content.get("text", "")

        if not task_text:
            error_text = (
                "❌ Не могу определить задачу\n\n"
                "Пожалуйста, отправьте текстовое сообщение с описанием задачи."
            )
            edit_succeeded = await self._safe_edit_message(
                error_text, chat_id=chat_id, message_id=processing_msg_id
            )
            if not edit_succeeded:
                await self.bot.send_message(chat_id=chat_id, text=error_text)
            return

        # Save user message to context (get first message from group for ID)
        first_message = group.messages[0] if group.messages else {}
        message_id = first_message.get("message_id", 0)
        timestamp = first_message.get("date", 0)
        self.user_context_manager.add_user_message_to_context(
            user_id, message_id, task_text, timestamp
        )

        # Execute task with agent
        # Try to update status message (but don't fail if it times out)
        self.logger.info(
            f"[AGENT_SERVICE] Executing task for user {user_id}: {task_text[:50]}..."
        )
        await self._safe_edit_message(
            "🤖 Выполняю задачу...", chat_id=chat_id, message_id=processing_msg_id
        )

        result = await self._execute_with_agent(kb_path, content, user_id)

        # Save assistant response to context
        import time

        response_timestamp = int(time.time())
        # Build a simple summary of the response for context
        response_text = result.get("answer") or result.get("summary", "Задача выполнена")
        self.user_context_manager.add_assistant_message_to_context(
            user_id, processing_msg_id, response_text, response_timestamp
        )

        # Send result to user
        await self._send_result(processing_msg_id, chat_id, result)

    async def _execute_with_agent(self, kb_path: Path, content: dict, user_id: int) -> dict:
        """
        Execute task with agent.

        Agent has full access to KB and can:
        - Answer questions
        - Create/edit/delete files
        - Restructure KB
        - Search for additional information online
        - Perform any autonomous task

        Args:
            kb_path: Path to knowledge base
            content: Task content from user
            user_id: User ID

        Returns:
            Agent execution result with answer, file changes, metadata
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

        if hasattr(user_agent, "set_working_directory"):
            user_agent.set_working_directory(str(agent_working_dir))
            self.logger.debug(f"Set agent working directory to: {agent_working_dir}")

        # Temporarily change agent instruction to agent mode
        original_instruction = None
        if hasattr(user_agent, "get_instruction") and hasattr(user_agent, "set_instruction"):
            original_instruction = user_agent.get_instruction()
            user_agent.set_instruction(AGENT_MODE_INSTRUCTION)
            self.logger.debug(f"Temporarily changed agent instruction to agent mode")

        # Get conversation context
        context = self.user_context_manager.get_conversation_context(user_id)

        # Prepare task content with agent mode instruction
        # Include context if available
        if context:
            task_prompt = f"{context}\n\n{AGENT_MODE_INSTRUCTION}\n\n# Задача от пользователя:\n{content.get('text', '')}"
        else:
            task_prompt = (
                f"{AGENT_MODE_INSTRUCTION}\n\n# Задача от пользователя:\n{content.get('text', '')}"
            )

        task_content = {
            "text": content.get("text", ""),
            "urls": content.get("urls", []),
            "prompt": task_prompt,
        }

        try:
            # Process task with agent
            self.logger.debug(f"[AGENT_SERVICE] Processing task with agent for user {user_id}")
            response = await user_agent.process(task_content)

            # Extract result from response
            # Priority: answer field, then metadata, then summary
            result = {
                "answer": response.get("answer"),
                "summary": response.get("summary", ""),
                "metadata": response.get("metadata", {}),
                "files_created": response.get("metadata", {}).get("files_created", []),
                "files_edited": response.get("metadata", {}).get("files_edited", []),
                "files_deleted": response.get("metadata", {}).get("files_deleted", []),
                "folders_created": response.get("metadata", {}).get("folders_created", []),
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
            if original_instruction is not None and hasattr(user_agent, "set_instruction"):
                user_agent.set_instruction(original_instruction)
                self.logger.debug(f"Restored original agent instruction")

    async def _safe_edit_message(
        self, text: str, chat_id: int, message_id: int, parse_mode: str = None
    ) -> bool:
        """
        Safely edit a message with timeout handling

        Args:
            text: Message text
            chat_id: Chat ID
            message_id: Message ID to edit
            parse_mode: Parse mode (e.g., 'Markdown')

        Returns:
            True if edit succeeded, False if we should send a new message instead
        """
        try:
            await self.bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, parse_mode=parse_mode
            )
            return True
        except asyncio.TimeoutError as e:
            # Handle timeout
            self.logger.warning(
                f"Message edit timed out (message may be too old), "
                f"will send new message instead: {e}"
            )
            return False
        except Exception as e:
            # Handle all other errors (including platform-specific API errors)
            error_msg = str(e).lower()

            # Check for common error patterns
            if "timeout" in error_msg or "timed out" in error_msg:
                self.logger.warning(f"Message edit timed out, will send new message: {e}")
                return False
            elif "message is not modified" in error_msg:
                self.logger.debug(f"Message not modified, skipping edit: {e}")
                return True
            elif "message can't be edited" in error_msg or "message to edit not found" in error_msg:
                self.logger.warning(f"Cannot edit message (too old or deleted), will send new: {e}")
                return False
            else:
                # Log unexpected errors but try to continue
                self.logger.error(f"Unexpected error editing message: {e}", exc_info=True)
                return False

    async def _send_result(self, processing_msg_id: int, chat_id: int, result: dict) -> None:
        """
        Send task result to user

        Args:
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID
            result: Task execution result
        """
        # Build result message
        message_parts = []

        # If there's an answer (e.g., user asked a question)
        if result.get("answer"):
            message_parts.append("💡 **Ответ:**\n")
            message_parts.append(result["answer"])
            message_parts.append("\n")

        # Add summary
        if result.get("summary"):
            message_parts.append(f"📋 **Выполнено:** {result['summary']}\n")

        # Add file operations
        files_created = result.get("files_created", [])
        files_edited = result.get("files_edited", [])
        files_deleted = result.get("files_deleted", [])
        folders_created = result.get("folders_created", [])

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
            # Try to edit the processing message with the first chunk
            edit_succeeded = await self._safe_edit_message(
                message_chunks[0],
                chat_id=chat_id,
                message_id=processing_msg_id,
                parse_mode="Markdown",
            )

            # If edit failed (e.g., timeout), send as new message
            if not edit_succeeded:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Результат:**\n\n{message_chunks[0]}",
                    parse_mode="Markdown",
                )

            # If there are more chunks, send them as separate messages
            for i, chunk in enumerate(message_chunks[1:], start=2):
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"💡 **(часть {i}/{len(message_chunks)}):**\n\n{chunk}",
                    parse_mode="Markdown",
                )

        except Exception as e:
            # If Markdown parsing fails, send without formatting
            if "can't parse entities" in str(e).lower():
                self.logger.warning(f"Markdown parsing failed, sending without formatting: {e}")

                full_message_plain = "".join(message_parts)
                message_chunks_plain = split_long_message(full_message_plain)

                # Try to edit, fall back to new message if needed
                edit_succeeded = await self._safe_edit_message(
                    message_chunks_plain[0],
                    chat_id=chat_id,
                    message_id=processing_msg_id,
                    parse_mode=None,
                )

                if not edit_succeeded:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=f"Результат:\n\n{message_chunks_plain[0]}",
                        parse_mode=None,
                    )

                for i, chunk in enumerate(message_chunks_plain[1:], start=2):
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=f"(часть {i}/{len(message_chunks_plain)}):\n\n{chunk}",
                        parse_mode=None,
                    )
            else:
                raise

    async def _send_error_notification(
        self, processing_msg_id: int, chat_id: int, error_message: str
    ) -> None:
        """Send error notification"""
        try:
            error_text = f"❌ Ошибка выполнения задачи: {error_message}"

            # Try to edit the message, fall back to new message if timeout
            edit_succeeded = await self._safe_edit_message(
                error_text, chat_id=chat_id, message_id=processing_msg_id
            )

            # If edit failed due to timeout, send as new message
            if not edit_succeeded:
                await self.bot.send_message(chat_id=chat_id, text=error_text)
        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}", exc_info=True)
