"""
Agent Task Service
Handles free-form agent tasks in agent mode
Follows Single Responsibility Principle

AICODE-NOTE: This service uses file-first prompt management via PromptService.
Prompts are exported to data/prompts/ on mode switch and read from there.
"""

from pathlib import Path
from typing import Optional

from src.bot.bot_port import BotPort
from src.bot.response_formatter import ResponseFormatter
from src.bot.settings_manager import SettingsManager
from src.core.rate_limiter import RateLimiter
from src.knowledge_base.credentials_manager import CredentialsManager
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.sync_manager import get_sync_manager
from src.processor.message_aggregator import MessageGroup
from src.prompts import PromptService
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
        prompt_provider: Optional[PromptService] = None,
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
            prompt_provider: Prompt provider for getting exported prompts (optional)
        """
        # AICODE-NOTE: Initialize base class with common dependencies
        super().__init__(bot, repo_manager, settings_manager, credentials_manager, rate_limiter)

        # Agent-specific dependencies
        self.user_context_manager = user_context_manager
        self.response_formatter = ResponseFormatter()
        self._prompt_provider = prompt_provider

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

        # Parse task with correct paths based on kb_topics_only setting
        content_parser = self._get_content_parser(user_id)
        content = await content_parser.parse_group_with_files(group, bot=self.bot, kb_path=kb_path)
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

        # Prepare placeholders for multi-part response
        message_break_after = self._get_response_message_breaks(user_id)
        placeholder_count = max(1, len(message_break_after) + 1)
        # AICODE-NOTE: Always ensure at least 3 messages (second for logs, third for errors)
        placeholder_count = max(3, placeholder_count)
        processing_message_ids = await self._prepare_processing_placeholders(
            chat_id=chat_id,
            processing_msg_id=processing_msg_id,
            count=placeholder_count,
            text="Анализирую контент",
        )
        primary_processing_id = processing_message_ids[0]

        # AICODE-NOTE: Start progress monitoring for checkbox tracking
        # Export directory is data/prompts/agent_mode where promptic exports rendered files
        export_dir = Path(__file__).parent.parent.parent / "data" / "prompts" / "agent_mode"
        progress_monitor = await self._start_progress_monitoring(
            export_dir=export_dir,
            chat_id=chat_id,
            message_id=primary_processing_id,
            user_id=user_id,
        )

        try:
            # Execute task with agent
            self.logger.info(
                f"[AGENT_SERVICE] Executing task for user {user_id}: {task_text[:50]}..."
            )

            processed_content = await self._execute_with_agent(
                kb_path, content, user_id, chat_id, primary_processing_id, processing_message_ids
            )

            # Save assistant response to context
            import time

            response_timestamp = int(time.time())
            # Build a simple summary of the response for context
            self.user_context_manager.add_assistant_message_to_context(
                user_id,
                primary_processing_id,
                processed_content.get("markdown"),
                response_timestamp,
            )

            # AICODE-NOTE: Use base class method for auto-commit and push
            task_summary = task_text[:50] + "..." if len(task_text) > 50 else task_text
            commit_message = f"Agent task: {task_summary}"
            await self._auto_commit_and_push(git_ops, user_id, commit_message)

            # Send result to user
            await self._send_result(
                processing_message_ids, chat_id, processed_content, kb_path, user_id
            )

        finally:
            # AICODE-NOTE: Always stop progress monitoring when done
            if progress_monitor:
                await progress_monitor.stop_monitoring()

    async def _execute_with_agent(
        self,
        kb_path: Path,
        content: dict,
        user_id: int,
        chat_id: int,
        processing_msg_id: int,
        processing_message_ids: list,
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
            processing_message_ids: List of all processing message IDs (for log updates)

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

            # AICODE-NOTE: Get agent mode instruction from prompt provider (file-first approach)
            instr = self._get_agent_instruction()

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

        # Create log_callback to update second message with logs (always enabled)
        # AICODE-NOTE: Second message (index 1) is always created for log streaming
        # We ensured placeholder_count >= 2, so processing_message_ids[1] should always exist
        log_message_id = processing_message_ids[1]
        self.logger.info(
            f"[AGENT_SERVICE] Creating log_callback for message_id={log_message_id}, "
            f"total messages={len(processing_message_ids)}"
        )

        # Store last sent text to avoid unnecessary updates
        last_sent_text = [None]

        async def update_log_message(log_snippet: str) -> None:
            """Update the second processing message with log snippet."""
            try:
                # Format log message - escape HTML in log snippet to prevent issues
                from html import escape

                escaped_snippet = escape(log_snippet)
                log_text = f"Анализирую контент\n\n<code>{escaped_snippet}</code>"

                # Skip update if text hasn't changed
                if last_sent_text[0] == log_text:
                    self.logger.debug(
                        f"[AGENT_SERVICE] Log text unchanged, skipping update ({len(log_snippet)} chars)"
                    )
                    return

                self.logger.info(
                    f"[AGENT_SERVICE] Updating log message with {len(log_snippet)} chars"
                )
                success = await self._safe_edit_message(
                    log_text, chat_id=chat_id, message_id=log_message_id, parse_mode="HTML"
                )
                if success:
                    last_sent_text[0] = log_text
                    self.logger.debug(f"[AGENT_SERVICE] Log message updated successfully")
                else:
                    self.logger.warning(
                        f"[AGENT_SERVICE] Failed to update log message (edit returned False)"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to update log message: {e}", exc_info=True)

        log_callback = update_log_message

        # Create error_callback to update third message with errors (if third message exists)
        error_callback = None
        if len(processing_message_ids) > 2:
            error_message_id = processing_message_ids[2]
            self.logger.info(
                f"[AGENT_SERVICE] Creating error_callback for message_id={error_message_id}"
            )

            # Store accumulated errors
            accumulated_errors = [""]

            async def update_error_message(error_msg: str) -> None:
                """Update the third processing message with error message (accumulates errors)."""
                try:
                    # Append new error to accumulated errors
                    if error_msg and error_msg not in accumulated_errors[0]:
                        accumulated_errors[0] += (
                            f"\n{error_msg}" if accumulated_errors[0] else error_msg
                        )
                        # Limit to last 2000 chars to avoid message too long
                        if len(accumulated_errors[0]) > 2000:
                            accumulated_errors[0] = accumulated_errors[0][-2000:]

                    if not accumulated_errors[0]:
                        return

                    from html import escape

                    escaped_error = escape(accumulated_errors[0])
                    error_text = f"⚠️ Ошибки:\n\n<code>{escaped_error}</code>"
                    success = await self._safe_edit_message(
                        error_text, chat_id=chat_id, message_id=error_message_id, parse_mode="HTML"
                    )
                    if success:
                        self.logger.debug(f"[AGENT_SERVICE] Error message updated successfully")
                except Exception as e:
                    self.logger.warning(f"Failed to update error message: {e}", exc_info=True)

            error_callback = update_error_message

        task_content = {
            "text": content.get("text", ""),
            "urls": content.get("urls", []),
            "prompt": task_prompt,
            "log_callback": log_callback,
            "error_callback": error_callback,
            "log_chars": 1000,  # Default: last 1000 characters
            "log_update_interval": 30.0,  # Default: update every 30 seconds
        }

        # Log what we're passing to agent
        self.logger.info(
            f"[AGENT_SERVICE] Passing task_content to agent: "
            f"has_log_callback={log_callback is not None}, "
            f"log_chars={task_content.get('log_chars')}, "
            f"log_update_interval={task_content.get('log_update_interval')}"
        )

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

    def _get_agent_instruction(self) -> str:
        """
        Get agent mode instruction from prompt provider using promptic render.

        AICODE-NOTE: Uses file-first approach with @ref() for shared components.
        response_format is passed via vars parameter, not inline replacement.
        Media instruction is referenced via @ref() in the prompt file.

        Returns:
            Agent mode instruction string with vars substituted
        """
        from src.bot.response_formatter import ResponseFormatter

        response_formatter = ResponseFormatter()
        response_formatter_prompt = response_formatter.generate_prompt_text()

        # Prepare vars for substitution
        vars_dict = {"response_format": response_formatter_prompt}

        # Try to get from prompt provider (file-first approach)
        if self._prompt_provider is not None:
            try:
                # AICODE-NOTE: Use render_mode="file_first" to export files for qwen CLI
                # Direct file path - source_base = config/prompts/ (parent of file)
                return self._prompt_provider.render_prompt(
                    "agent_mode.md",
                    vars=vars_dict,
                    render_mode="file_first",
                )
            except Exception as e:
                self.logger.warning(f"Failed to get agent instruction from provider: {e}")

        # Fallback to direct render (for backward compatibility)
        from promptic import render

        prompts_dir = Path(__file__).parent.parent.parent / "config" / "prompts"
        export_dir = Path(__file__).parent.parent.parent / "data" / "prompts" / "agent_mode"
        return render(
            str(prompts_dir / "agent_mode.md"),
            vars=vars_dict,
            render_mode="file_first",
            export_to=str(export_dir),
            overwrite=True,
        )

    async def _send_error_notification(
        self, processing_msg_id: int, chat_id: int, error_message: str
    ) -> None:
        """Send error notification (override base class to add context)"""
        await super()._send_error_notification(
            processing_msg_id, chat_id, f"Ошибка выполнения задачи: {error_message}"
        )
