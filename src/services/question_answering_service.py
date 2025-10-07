"""
Question Answering Service
Handles question answering based on knowledge base
Follows Single Responsibility Principle
"""

from pathlib import Path
from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from src.services.interfaces import IQuestionAnsweringService, IUserContextManager
from src.processor.message_aggregator import MessageGroup
from src.processor.content_parser import ContentParser
from src.knowledge_base.repository import RepositoryManager
from src.bot.utils import escape_markdown, split_long_message
from config.agent_prompts import KB_QUERY_PROMPT_TEMPLATE


class QuestionAnsweringService(IQuestionAnsweringService):
    """
    Service for answering questions based on knowledge base
    
    Responsibilities:
    - Parse question from message
    - Query knowledge base using agent
    - Return answer to user
    """
    
    def __init__(
        self,
        bot: AsyncTeleBot,
        repo_manager: RepositoryManager,
        user_context_manager: IUserContextManager
    ):
        """
        Initialize question answering service
        
        Args:
            bot: Telegram bot instance
            repo_manager: Repository manager
            user_context_manager: User context manager
        """
        self.bot = bot
        self.repo_manager = repo_manager
        self.user_context_manager = user_context_manager
        self.content_parser = ContentParser()
        self.logger = logger
    
    async def answer_question(
        self,
        group: MessageGroup,
        processing_msg: Message,
        user_id: int,
        user_kb: dict
    ) -> None:
        """
        Answer a question based on knowledge base
        
        Args:
            group: Message group containing the question
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
            
            # Parse question
            content = await self.content_parser.parse_group_with_files(group, bot=self.bot)
            question_text = content.get('text', '')
            
            if not question_text:
                await self.bot.edit_message_text(
                    "❌ Не могу определить вопрос\n\n"
                    "Пожалуйста, отправьте текстовое сообщение с вопросом.",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Query knowledge base
            await self.bot.edit_message_text(
                "🔍 Ищу информацию в базе знаний...",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            
            answer = await self._query_kb(kb_path, question_text, user_id)
            
            # Send answer - escape the answer text to prevent Markdown parsing errors
            escaped_answer = escape_markdown(answer)
            
            # Handle long messages by splitting them
            full_message = f"💡 **Ответ:**\n\n{escaped_answer}"
            message_chunks = split_long_message(full_message)
            
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
                        text=f"💡 **Ответ (часть {i}/{len(message_chunks)}):**\n\n{chunk}",
                        parse_mode='Markdown'
                    )
                    
            except Exception as e:
                # If Markdown parsing still fails, send without formatting
                if "can't parse entities" in str(e).lower():
                    self.logger.warning(f"Markdown parsing failed, sending without formatting: {e}")
                    
                    # Try again without markdown formatting
                    full_message_plain = f"💡 Ответ:\n\n{answer}"
                    message_chunks_plain = split_long_message(full_message_plain)
                    
                    await self.bot.edit_message_text(
                        message_chunks_plain[0],
                        chat_id=processing_msg.chat.id,
                        message_id=processing_msg.message_id,
                        parse_mode=None
                    )
                    
                    # Send remaining chunks without markdown
                    for i, chunk in enumerate(message_chunks_plain[1:], start=2):
                        await self.bot.send_message(
                            chat_id=processing_msg.chat.id,
                            text=f"💡 Ответ (часть {i}/{len(message_chunks_plain)}):\n\n{chunk}",
                            parse_mode=None
                        )
                elif "MESSAGE_TOO_LONG" in str(e):
                    # This shouldn't happen after splitting, but handle it just in case
                    self.logger.error(f"Message still too long after splitting: {e}")
                    await self.bot.edit_message_text(
                        "❌ Ответ слишком длинный даже после разделения. Пожалуйста, попробуйте задать более конкретный вопрос.",
                        chat_id=processing_msg.chat.id,
                        message_id=processing_msg.message_id
                    )
                else:
                    raise
            
        except Exception as e:
            self.logger.error(f"Error in question processing: {e}", exc_info=True)
            await self._send_error_notification(processing_msg, str(e))
    
    async def _query_kb(
        self,
        kb_path: Path,
        question: str,
        user_id: int
    ) -> str:
        """
        Query knowledge base with a question
        
        Args:
            kb_path: Path to knowledge base
            question: Question text
            user_id: User ID
        
        Returns:
            Answer text
        """
        # Get user agent
        user_agent = self.user_context_manager.get_or_create_agent(user_id)
        
        # Prepare query prompt
        query_prompt = KB_QUERY_PROMPT_TEMPLATE.format(
            kb_path=str(kb_path),
            question=question
        )
        
        # Create query content
        query_content = {
            'text': query_prompt,
            'urls': [],
            'prompt': query_prompt
        }
        
        try:
            # Process query with agent
            response = await user_agent.process(query_content)
            
            # Extract answer from response (priority: answer field, then markdown, then text)
            # The 'answer' field contains the final formatted answer from agent-result block
            answer = response.get('answer')
            
            # Fallback to markdown or text if answer is not present
            if not answer:
                self.logger.warning("Agent did not return 'answer' field, using markdown/text as fallback")
                answer = response.get('markdown') or response.get('text', '')
            
            if not answer:
                raise ValueError("Agent did not return an answer")
            
            return answer
            
        except Exception as agent_error:
            self.logger.error(f"Agent query processing failed: {agent_error}", exc_info=True)
            raise RuntimeError(
                f"Ошибка при поиске информации: {str(agent_error)}\n\n"
                f"Попробуйте переформулировать вопрос или проверьте, "
                f"что база знаний содержит релевантную информацию."
            )
    
    async def _send_error_notification(
        self,
        processing_msg: Message,
        error_message: str
    ) -> None:
        """Send error notification"""
        try:
            await self.bot.edit_message_text(
                f"❌ Ошибка обработки вопроса: {error_message}",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
        except Exception:
            pass
