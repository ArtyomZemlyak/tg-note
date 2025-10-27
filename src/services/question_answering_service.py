"""
Question Answering Service
Handles question answering based on knowledge base
Follows Single Responsibility Principle
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from config.agent_prompts import get_ask_mode_instruction, get_kb_query_template
from src.agents.base_agent import BaseAgent
from src.bot.bot_port import BotPort
from src.bot.response_formatter import ResponseFormatter
from src.bot.settings_manager import SettingsManager
from src.bot.utils import escape_markdown, split_long_message
from src.core.rate_limiter import RateLimiter
from src.knowledge_base.repository import RepositoryManager
from src.processor.content_parser import ContentParser
from src.processor.message_aggregator import MessageGroup
from src.services.base_kb_service import BaseKBService
from src.services.interfaces import IQuestionAnsweringService, IUserContextManager


class QuestionAnsweringService(BaseKBService, IQuestionAnsweringService):
    """
    Service for answering questions based on knowledge base (ask mode).

    Responsibilities:
    - Parse question from message
    - Search knowledge base using agent with KB reading tools
    - Format and return answer to user
    - Maintain conversation context for follow-up questions
    - Enforce rate limits to prevent abuse

    This service is activated when user is in 'ask' mode (/ask command).
    """

    def __init__(
        self,
        bot: BotPort,
        repo_manager: RepositoryManager,
        user_context_manager: IUserContextManager,
        settings_manager: SettingsManager,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize question answering service

        Args:
            bot: Bot messaging interface (transport abstraction)
            repo_manager: Repository manager
            user_context_manager: User context manager
            settings_manager: Settings manager for user-specific settings
            rate_limiter: Rate limiter for agent calls (optional)
        """
        self.bot = bot
        self.repo_manager = repo_manager
        self.user_context_manager = user_context_manager
        self.settings_manager = settings_manager
        self.rate_limiter = rate_limiter
        self.content_parser = ContentParser()
        self.logger = logger
        self.response_formatter = ResponseFormatter()

    async def answer_question(
        self, group: MessageGroup, processing_msg_id: int, chat_id: int, user_id: int, user_kb: dict
    ) -> None:
        """
        Answer a question based on knowledge base

        Args:
            group: Message group containing the question
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID where question was asked
            user_id: User ID
            user_kb: User's knowledge base configuration
        """
        try:
            # Get KB path
            kb_path = self.repo_manager.get_kb_path(user_kb["kb_name"])
            if not kb_path:
                await self.bot.edit_message_text(
                    "❌ Локальная копия базы знаний не найдена\n\n"
                    "Попробуйте настроить базу знаний заново: /setkb",
                    chat_id=chat_id,
                    message_id=processing_msg_id,
                )
                return

            # Parse question
            content = await self.content_parser.parse_group_with_files(group, bot=self.bot)
            question_text = content.get("text", "")

            if not question_text:
                await self.bot.edit_message_text(
                    "❌ Не могу определить вопрос\n\n"
                    "Пожалуйста, отправьте текстовое сообщение с вопросом.",
                    chat_id=chat_id,
                    message_id=processing_msg_id,
                )
                return

            # Save user message to context (get first message from group for ID)
            first_message = group.messages[0] if group.messages else {}
            message_id = first_message.get("message_id", 0)
            timestamp = first_message.get("date", 0)
            self.user_context_manager.add_user_message_to_context(
                user_id, message_id, question_text, timestamp
            )

            # Query knowledge base
            await self.bot.edit_message_text(
                "🔍 Ищу информацию в базе знаний...", chat_id=chat_id, message_id=processing_msg_id
            )

            self.logger.info(
                f"[ASK_SERVICE] Querying KB for user {user_id}, question: {question_text[:50]}..."
            )
            processed_content = await self._query_kb(kb_path, question_text, user_id)

            # Save assistant response to context
            import time

            response_timestamp = int(time.time())
            self.user_context_manager.add_assistant_message_to_context(
                user_id, processing_msg_id, processed_content.get("markdown"), response_timestamp
            )

            # Send success notification
            await self._send_result(
                processing_msg_id, chat_id, processed_content, kb_path, user_id
            )

        except Exception as e:
            self.logger.error(f"Error in question processing: {e}", exc_info=True)
            # AICODE-FIX: Более информативное сообщение об ошибке
            error_message = str(e)
            if "summary" in error_message and "JSON" in str(type(e).__name__):
                error_message = (
                    "Ошибка обработки ответа агента. Попробуйте переформулировать вопрос."
                )
            await self._send_error_notification(processing_msg_id, chat_id, error_message)

    async def _query_kb(self, kb_path: Path, question: str, user_id: int) -> str:
        """
        Query knowledge base with a question.

        Uses agent with KB reading tools (grep, read, ls, etc.) to find
        relevant information and formulate an answer.

        Args:
            kb_path: Path to knowledge base
            question: Question text from user
            user_id: User ID

        Returns:
            Answer text formatted for user
        """
        # Get user agent (thread-safe)
        user_agent: BaseAgent = await self.user_context_manager.get_or_create_agent(user_id)

        # Set working directory to user's KB for qwen-code-cli agent
        # Use KB_TOPICS_ONLY setting to determine if we should restrict to topics/ folder
        kb_topics_only = self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY")

        if kb_topics_only:
            # Restrict to topics folder (protects index.md, README.md, etc.)
            agent_working_dir = kb_path / "topics"
            self.logger.debug(f"KB_TOPICS_ONLY=true, restricting agent to topics folder")

            # AICODE-NOTE: Ensure topics directory exists (important for GitHub repos)
            # When cloning from GitHub, the repo might not have a topics/ directory
            try:
                agent_working_dir.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Ensured agent working directory exists: {agent_working_dir}")
            except Exception as e:
                self.logger.warning(
                    f"Could not create agent working directory {agent_working_dir}: {e}"
                )
        else:
            # Full access to entire knowledge base
            agent_working_dir = kb_path
            self.logger.debug(f"KB_TOPICS_ONLY=false, agent has full KB access")

        if hasattr(user_agent, "set_working_directory"):
            user_agent.set_working_directory(str(agent_working_dir))
            self.logger.debug(f"Set agent working directory to: {agent_working_dir}")

        # Temporarily change agent instruction to ask mode
        # This prevents the agent from using note creation instructions
        original_instruction = None
        if hasattr(user_agent, "get_instruction") and hasattr(user_agent, "set_instruction"):
            original_instruction = user_agent.get_instruction()
            ask_instr = get_ask_mode_instruction("ru")

            from src.bot.response_formatter import ResponseFormatter
            response_formatter = ResponseFormatter()
            response_formatter_prompt = response_formatter.generate_prompt_text()

            # Combine the default instruction with the ResponseFormatter prompt
            ask_instr = ask_instr.format(response_format=response_formatter_prompt)

            user_agent.set_instruction(ask_instr)
            self.logger.debug(f"Temporarily changed agent instruction to ask mode")

        # Get conversation context
        context = self.user_context_manager.get_conversation_context(user_id)

        # Prepare query prompt with appropriate path (based on KB_TOPICS_ONLY setting)
        # Include context if available
        if context:
            query_prompt = f"{context}\n\n{get_kb_query_template('ru').format(kb_path=str(agent_working_dir), question=question)}"
        else:
            query_prompt = get_kb_query_template("ru").format(
                kb_path=str(agent_working_dir), question=question
            )

        # Create query content
        query_content = {"text": query_prompt, "urls": [], "prompt": query_prompt}

        # AICODE-NOTE: Rate limit check before expensive agent API call
        if self.rate_limiter:
            if not await self.rate_limiter.acquire(user_id):
                # Rate limited - calculate reset time
                reset_time = await self.rate_limiter.get_reset_time(user_id)
                wait_seconds = int((reset_time - datetime.now()).total_seconds())
                remaining = await self.rate_limiter.get_remaining(user_id)

                await self.bot.edit_message_text(
                    f"⏱️ Превышен лимит запросов к агенту\n\n"
                    f"Подождите ~{wait_seconds} секунд перед следующим запросом.\n"
                    f"Доступно запросов: {remaining}",
                    chat_id=chat_id,
                    message_id=processing_msg_id,
                )
                return

        try:
            # Process query with agent
            self.logger.debug(f"[ASK_SERVICE] Processing query with agent for user {user_id}")
            response = await user_agent.process(query_content)

            return response

        except Exception as agent_error:
            self.logger.error(f"Agent query processing failed: {agent_error}", exc_info=True)
            raise RuntimeError(
                f"Ошибка при поиске информации: {str(agent_error)}\n\n"
                f"Попробуйте переформулировать вопрос или проверьте, "
                f"что база знаний содержит релевантную информацию."
            )
        finally:
            # Restore original instruction
            if original_instruction is not None and hasattr(user_agent, "set_instruction"):
                user_agent.set_instruction(original_instruction)
                self.logger.debug(f"Restored original agent instruction")

    async def _send_error_notification(
        self, processing_msg_id: int, chat_id: int, error_message: str
    ) -> None:
        """Send error notification"""
        try:
            await self.bot.edit_message_text(
                f"❌ Ошибка обработки вопроса: {error_message}",
                chat_id=chat_id,
                message_id=processing_msg_id,
            )
        except Exception:
            pass
