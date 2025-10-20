"""
Agent Task Service
Handles free-form agent tasks in agent mode
Follows Single Responsibility Principle
"""

from pathlib import Path
from typing import Optional

from config.agent_prompts import AGENT_MODE_INSTRUCTION
from src.bot.bot_port import BotPort
from src.bot.settings_manager import SettingsManager
from src.bot.utils import escape_markdown, split_long_message
from src.core.rate_limiter import RateLimiter
from src.knowledge_base.credentials_manager import CredentialsManager
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.sync_manager import get_sync_manager
from src.processor.message_aggregator import MessageGroup
from src.services.base_kb_service import BaseKBService
from src.services.interfaces import IAgentTaskService, IUserContextManager


class AgentTaskService(BaseKBService, IAgentTaskService):
    """
    Service for executing free-form agent tasks (agent mode).

    Responsibilities:
    - Parse task from message
    - Execute task with full agent autonomy
    - Handle any KB-related operations (read, write, restructure)
    - Return results to user (answers, file modifications, etc.)
    - Maintain conversation context for complex multi-turn tasks
    - Enforce rate limits to prevent abuse

    This service is activated when user is in 'agent' mode (/agent command).
    Agent has full access to the knowledge base and can perform any task.
    """

    def __init__(
        self,
        bot: BotPort,
        repo_manager: RepositoryManager,
        user_context_manager: IUserContextManager,
        settings_manager: SettingsManager,
        credentials_manager: Optional[CredentialsManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize agent task service

        Args:
            bot: Bot messaging interface (transport abstraction)
            repo_manager: Repository manager
            user_context_manager: User context manager
            settings_manager: Settings manager for user-specific settings
            credentials_manager: Credentials manager (optional)
            rate_limiter: Rate limiter for agent calls (optional)
        """
        # AICODE-NOTE: Initialize base class with common dependencies
        super().__init__(bot, repo_manager, settings_manager, credentials_manager, rate_limiter)

        # Agent-specific dependencies
        self.user_context_manager = user_context_manager

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
        # AICODE-NOTE: Use base class method to setup Git operations
        git_ops = self._setup_git_ops(kb_path, user_id)

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
        self.logger.info(f"[AGENT_SERVICE] Executing task for user {user_id}: {task_text[:50]}...")
        await self._safe_edit_message(
            "🤖 Выполняю задачу...", chat_id=chat_id, message_id=processing_msg_id
        )

        result = await self._execute_with_agent(
            kb_path, content, user_id, chat_id, processing_msg_id
        )

        # Save assistant response to context
        import time

        response_timestamp = int(time.time())
        # Build a simple summary of the response for context
        response_text = result.get("answer") or result.get("summary", "Задача выполнена")
        self.user_context_manager.add_assistant_message_to_context(
            user_id, processing_msg_id, response_text, response_timestamp
        )

        # AICODE-NOTE: Use base class method for auto-commit and push
        task_summary = task_text[:50] + "..." if len(task_text) > 50 else task_text
        commit_message = f"Agent task: {task_summary}"
        await self._auto_commit_and_push(git_ops, user_id, commit_message)

        # Send result to user
        await self._send_result(processing_msg_id, chat_id, result, kb_path, user_id)

    async def _execute_with_agent(
        self, kb_path: Path, content: dict, user_id: int, chat_id: int, processing_msg_id: int
    ) -> dict:
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
            chat_id: Chat ID for notifications
            processing_msg_id: Message ID for status updates

        Returns:
            Agent execution result with answer, file changes, metadata
        """
        # Get user agent (thread-safe)
        user_agent = await self.user_context_manager.get_or_create_agent(user_id)

        # AICODE-NOTE: Use base class methods to configure agent working directory
        agent_working_dir = self._get_agent_working_dir(kb_path, user_id)
        self._configure_agent_working_dir(user_agent, agent_working_dir)

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

        # AICODE-NOTE: Use base class method for rate limit check
        if not await self._check_rate_limit(user_id, chat_id, processing_msg_id):
            # Return empty result if rate limited
            return {
                "answer": None,
                "summary": "",
                "metadata": {},
                "files_created": [],
                "files_edited": [],
                "files_deleted": [],
                "folders_created": [],
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

    async def _send_result(
        self,
        processing_msg_id: int,
        chat_id: int,
        result: dict,
        kb_path: Path,
        user_id: int,
    ) -> None:
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

        # AICODE-NOTE: Use base class method for GitHub URL generation
        github_base = self._get_github_base_url(kb_path, user_id)
        kb_topics_only = self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY")

        # AICODE-NOTE: Use base class method for file change formatting
        file_change_parts = self._format_file_changes(
            files_created, files_edited, files_deleted, folders_created, github_base, None, kb_topics_only
        )
        # Convert to newline-terminated strings for agent service formatting
        message_parts.extend(
            [part + "\n" if not part.endswith("\n") else part for part in file_change_parts]
        )

        # AICODE-NOTE: Use base class method for links/relations filtering and formatting
        metadata = result.get("metadata", {}) or {}
        links = metadata.get("links", []) or metadata.get("relations", [])
        link_parts = self._filter_and_format_links(links, files_created, kb_path, github_base, kb_topics_only)
        # Convert to newline-terminated strings for agent service formatting
        message_parts.extend(
            [part + "\n" if not part.endswith("\n") else part for part in link_parts]
        )

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
        """Send error notification (override base class to add context)"""
        await super()._send_error_notification(
            processing_msg_id, chat_id, f"Ошибка выполнения задачи: {error_message}"
        )
