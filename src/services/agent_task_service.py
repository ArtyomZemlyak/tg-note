"""
Agent Task Service
Handles free-form agent tasks in agent mode
Follows Single Responsibility Principle
"""

from pathlib import Path
from typing import Optional

from config.agent_prompts import get_qwen_code_agent_instruction
from src.bot.bot_port import BotPort
from src.bot.response_formatter import ResponseFormatter
from src.bot.settings_manager import SettingsManager
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
        self.response_formatter = ResponseFormatter()

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
        content = await self.content_parser.parse_group_with_files(
            group, bot=self.bot, kb_path=kb_path
        )
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

        processed_content = await self._execute_with_agent(
            kb_path, content, user_id, chat_id, processing_msg_id
        )

        # Save assistant response to context
        import time

        response_timestamp = int(time.time())
        # Build a simple summary of the response for context
        self.user_context_manager.add_assistant_message_to_context(
            user_id, processing_msg_id, processed_content.get("markdown"), response_timestamp
        )

        # AICODE-NOTE: Use base class method for auto-commit and push
        task_summary = task_text[:50] + "..." if len(task_text) > 50 else task_text
        commit_message = f"Agent task: {task_summary}"
        await self._auto_commit_and_push(git_ops, user_id, commit_message)

        # Send result to user
        await self._send_result(processing_msg_id, chat_id, processed_content, kb_path, user_id)

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
        instr = ""
        if hasattr(user_agent, "get_instruction") and hasattr(user_agent, "set_instruction"):
            original_instruction = user_agent.get_instruction()
            instr = get_qwen_code_agent_instruction("ru")

            # AICODE-NOTE: Add images instruction to prompt
            from config.agent_prompts import get_images_instruction
            from src.bot.response_formatter import ResponseFormatter

            images_instr = get_images_instruction("ru")
            response_formatter = ResponseFormatter()
            response_formatter_prompt = response_formatter.generate_prompt_text()

            # Combine the default instruction with images and ResponseFormatter prompt
            instr = instr.format(
                instruction_images=images_instr, response_format=response_formatter_prompt
            )

            user_agent.set_instruction(instr)
            self.logger.debug(f"Temporarily changed agent instruction to agent mode")

        # Get conversation context
        context = self.user_context_manager.get_conversation_context(user_id)

        # Prepare task content with agent mode instruction
        # Include context if available
        if context:
            task_prompt = (
                f"{context}\n\n{instr}\n\n# Задача от пользователя:\n{content.get('text', '')}"
            )
        else:
            task_prompt = f"{instr}\n\n# Задача от пользователя:\n{content.get('text', '')}"

        task_content = {
            "text": content.get("text", ""),
            "urls": content.get("urls", []),
            "prompt": task_prompt,
        }

        # AICODE-NOTE: Use base class method for rate limit check
        if not await self._check_rate_limit(user_id, chat_id, processing_msg_id):
            # Return empty result if rate limited
            return {}

        try:
            # Process task with agent
            self.logger.debug(f"[AGENT_SERVICE] Processing task with agent for user {user_id}")
            result = await user_agent.process(task_content)
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

    async def _send_error_notification(
        self, processing_msg_id: int, chat_id: int, error_message: str
    ) -> None:
        """Send error notification (override base class to add context)"""
        await super()._send_error_notification(
            processing_msg_id, chat_id, f"Ошибка выполнения задачи: {error_message}"
        )
