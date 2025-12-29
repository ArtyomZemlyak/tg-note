"""
Scheduled Task Executor
Executes scheduled agent tasks through standard message processing pipeline
"""

import time
from typing import Optional

from loguru import logger

from src.bot.bot_port import BotPort
from src.bot.dto import IncomingMessageDTO
from src.core.enums import UserMode
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.user_settings import UserSettings
from src.prompts import PromptService
from src.services.interfaces import IMessageProcessor, IUserContextManager
from src.services.scheduled_task import ScheduledTask


class ScheduledTaskExecutor:
    """
    Executor for scheduled agent tasks

    AICODE-NOTE: Tasks are executed through the standard message processing pipeline
    (MessageProcessor -> AgentTaskService), ensuring all standard features work:
    - KB locking (handled by AgentTaskService)
    - Progress tracking
    - Log streaming
    - Error handling
    - Telegram notifications

    Responsibilities:
    - Load prompts (from promptic or direct text)
    - Create fake IncomingMessageDTO to simulate user message
    - Ensure user is in agent mode
    - Route task through MessageProcessor
    - Send Telegram notifications about task execution
    """

    def __init__(
        self,
        bot: BotPort,
        message_processor: IMessageProcessor,
        user_context_manager: IUserContextManager,
        repo_manager: RepositoryManager,
        user_settings: UserSettings,
        prompt_service: Optional[PromptService] = None,
    ):
        """
        Initialize scheduled task executor

        Args:
            bot: Bot messaging interface for notifications
            message_processor: Message processor for handling tasks as regular messages
            user_context_manager: User context manager for setting user mode
            repo_manager: Repository manager for KB paths
            user_settings: User settings manager
            prompt_service: Prompt service for loading prompts (optional)
        """
        self.bot = bot
        self.message_processor = message_processor
        self.user_context_manager = user_context_manager
        self.repo_manager = repo_manager
        self.user_settings = user_settings
        self.prompt_service = prompt_service
        self.logger = logger.bind(service="ScheduledTaskExecutor")

    async def execute_task(self, task: ScheduledTask) -> bool:
        """
        Execute a scheduled task

        Args:
            task: Scheduled task to execute

        Returns:
            True if execution was successful, False otherwise
        """
        start_time = time.time()
        self.logger.info(
            f"[SCHEDULED_TASK] Starting execution of task {task.task_id} for user {task.user_id} on KB {task.kb_name}"
        )

        # Verify KB exists
        kb_path = self.repo_manager.get_kb_path(task.kb_name)
        if not kb_path:
            error_msg = f"Knowledge base '{task.kb_name}' not found for task {task.task_id}"
            self.logger.error(error_msg)
            if task.chat_id:
                try:
                    await self.bot.send_message(
                        chat_id=task.chat_id,
                        text=(
                            f"❌ <b>Ошибка запланированной задачи</b>\n\n"
                            f"Задача: {task.task_id}\n"
                            f"База знаний '{task.kb_name}' не найдена"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to send error notification: {e}")
            return False

        # Verify user KB config
        user_kb = self.user_settings.get_user_kb(task.user_id)
        if not user_kb or user_kb.get("kb_name") != task.kb_name:
            # Set KB for user if not configured
            self.logger.warning(
                f"User {task.user_id} KB config not found or different, setting to: {task.kb_name}"
            )
            # AICODE-NOTE: We could set KB here, but for now just log a warning
            # The message processor will handle KB validation

        # Get chat_id for notifications (use task chat_id or user's default)
        chat_id = task.chat_id
        if not chat_id:
            # AICODE-NOTE: chat_id is required for message processing
            # If not set, we can't process the task
            error_msg = f"No chat_id in task {task.task_id}, cannot process task"
            self.logger.error(error_msg)
            return False

        # Send start notification (optional - agent will send its own messages)
        # AICODE-NOTE: We send a simple notification about task start
        # The agent will send its own response through the standard message pipeline
        if task.chat_id:
            try:
                await self.bot.send_message(
                    chat_id=task.chat_id,
                    text=f"⏰ <b>Запуск запланированной задачи</b>\n\nЗадача: {task.task_id}\nБЗ: {task.kb_name}",
                    parse_mode="HTML",
                )
            except Exception as e:
                self.logger.warning(f"Failed to send start notification: {e}")

        try:
            # Load prompt
            prompt_text = await self._load_prompt(task)
            if not prompt_text:
                error_msg = f"Failed to load prompt for task {task.task_id}"
                self.logger.error(error_msg)
                if task.chat_id:
                    try:
                        await self.bot.send_message(
                            chat_id=task.chat_id,
                            text=(
                                f"❌ <b>Ошибка запланированной задачи</b>\n\n"
                                f"Задача: {task.task_id}\n"
                                f"Не удалось загрузить промпт для задачи"
                            ),
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to send error notification: {e}")
                return False

            # AICODE-NOTE: Ensure user is in agent mode for task execution
            # Save current mode to restore later
            original_mode = self.user_context_manager.get_user_mode(task.user_id)
            mode_changed = False
            if original_mode != UserMode.AGENT.value:
                self.logger.info(
                    f"Setting user {task.user_id} to agent mode for scheduled task {task.task_id} "
                    f"(was: {original_mode})"
                )
                self.user_context_manager.set_user_mode(task.user_id, UserMode.AGENT.value)
                mode_changed = True

            # Create a fake incoming message DTO that simulates a message from the user
            # AICODE-NOTE: This allows us to use the standard message processing pipeline
            # The message will go through MessageProcessor -> AgentTaskService
            # All standard features (logging, progress tracking, KB locking, notifications) will work automatically
            # skip_deduplication=True allows scheduled tasks to run even if content was processed before
            fake_message = IncomingMessageDTO(
                message_id=int(time.time() * 1000),  # Generate unique message ID
                chat_id=chat_id,
                user_id=task.user_id,
                text=prompt_text,  # The prompt text becomes the message text
                content_type="text",
                timestamp=int(task.created_at.timestamp()),
                skip_deduplication=True,  # Skip deduplication check for scheduled tasks
            )

            # Process message through standard pipeline (with timeout)
            # AICODE-NOTE: MessageProcessor will handle:
            # - Message aggregation
            # - User mode routing (we set it to AGENT above)
            # - KB validation
            # - AgentTaskService execution with all standard features
            import asyncio

            task_timeout = 7200  # 2 hours default timeout
            self.logger.info(
                f"[SCHEDULED_TASK] Processing task {task.task_id} as regular message with timeout {task_timeout}s"
            )

            try:
                await asyncio.wait_for(
                    self.message_processor.process_message(fake_message),
                    timeout=task_timeout,
                )

                # Task completed successfully
                execution_time = time.time() - start_time
                self.logger.info(
                    f"[SCHEDULED_TASK] Task {task.task_id} completed successfully in {execution_time:.2f}s"
                )

                # Restore original user mode if it was changed
                if mode_changed:
                    self.logger.info(
                        f"Restoring user {task.user_id} mode to {original_mode} after task completion"
                    )
                    self.user_context_manager.set_user_mode(task.user_id, original_mode)

                # AICODE-NOTE: Don't send completion notification - agent already sent its response
                # through the standard message pipeline
                return True

            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                error_msg = f"Task {task.task_id} timed out after {task_timeout}s (executed for {execution_time:.2f}s)"
                self.logger.error(f"[SCHEDULED_TASK] {error_msg}")

                # Restore original user mode if it was changed
                if mode_changed:
                    self.logger.info(
                        f"Restoring user {task.user_id} mode to {original_mode} after task timeout"
                    )
                    self.user_context_manager.set_user_mode(task.user_id, original_mode)

                # Send timeout notification (this is an error case, so we notify)
                if task.chat_id:
                    try:
                        await self.bot.send_message(
                            chat_id=task.chat_id,
                            text=(
                                f"⏱️ <b>Таймаут запланированной задачи</b>\n\n"
                                f"Задача: {task.task_id}\n"
                                f"Превышено время выполнения: {task_timeout}s"
                            ),
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to send timeout notification: {e}")

                return False

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error executing task {task.task_id} after {execution_time:.2f}s: {e}"
            self.logger.error(f"[SCHEDULED_TASK] {error_msg}", exc_info=True)

            # Restore original user mode if it was changed (even on error)
            if mode_changed:
                self.logger.info(
                    f"Restoring user {task.user_id} mode to {original_mode} after task error"
                )
                self.user_context_manager.set_user_mode(task.user_id, original_mode)

            # Send error notification (this is an error case, so we notify)
            if task.chat_id:
                try:
                    await self.bot.send_message(
                        chat_id=task.chat_id,
                        text=(
                            f"❌ <b>Ошибка выполнения запланированной задачи</b>\n\n"
                            f"Задача: {task.task_id}\n"
                            f"Ошибка: {str(e)[:200]}"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to send error notification: {e}")

            return False

    async def _load_prompt(self, task: ScheduledTask) -> Optional[str]:
        """
        Load prompt for a task (from promptic or direct text)

        Args:
            task: Scheduled task

        Returns:
            Prompt text or None if failed
        """
        # If prompt_text is provided, use it directly
        if task.prompt_text:
            self.logger.debug(f"Using direct prompt text for task {task.task_id}")
            return task.prompt_text

        # If prompt_path is provided, load from promptic
        if task.prompt_path:
            self.logger.debug(f"Loading prompt from path: {task.prompt_path}")
            try:
                if self.prompt_service:
                    # Use prompt service to render prompt
                    prompt = self.prompt_service.render_prompt(
                        task.prompt_path, render_mode="file_first"
                    )
                    return prompt
                else:
                    # Fallback to direct promptic render
                    from promptic import render

                    prompts_dir = Path(__file__).parent.parent.parent / "config" / "prompts"
                    prompt_path = prompts_dir / task.prompt_path
                    if prompt_path.exists():
                        prompt = render(str(prompt_path), render_mode="file_first")
                        return prompt
                    else:
                        self.logger.error(f"Prompt file not found: {prompt_path}")
                        return None
            except Exception as e:
                self.logger.error(
                    f"Failed to load prompt from {task.prompt_path}: {e}", exc_info=True
                )
                return None

        self.logger.error(f"No prompt_path or prompt_text provided for task {task.task_id}")
        return None
