"""
Note Creation Service
Handles the creation of notes in the knowledge base
Follows Single Responsibility Principle
"""

from pathlib import Path
from typing import Optional
from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from src.services.interfaces import INoteCreationService, IUserContextManager
from src.processor.message_aggregator import MessageGroup
from src.processor.content_parser import ContentParser
from src.knowledge_base.manager import KnowledgeBaseManager
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.git_ops import GitOperations
from src.tracker.processing_tracker import ProcessingTracker
from src.bot.settings_manager import SettingsManager


class NoteCreationService(INoteCreationService):
    """
    Service for creating notes in the knowledge base
    
    Responsibilities:
    - Parse message content
    - Process content with agent
    - Save to knowledge base
    - Handle git operations
    - Track processed messages
    """
    
    def __init__(
        self,
        bot: AsyncTeleBot,
        tracker: ProcessingTracker,
        repo_manager: RepositoryManager,
        user_context_manager: IUserContextManager,
        settings_manager: SettingsManager
    ):
        """
        Initialize note creation service
        
        Args:
            bot: Telegram bot instance
            tracker: Processing tracker
            repo_manager: Repository manager
            user_context_manager: User context manager
            settings_manager: Settings manager
        """
        self.bot = bot
        self.tracker = tracker
        self.repo_manager = repo_manager
        self.user_context_manager = user_context_manager
        self.settings_manager = settings_manager
        self.content_parser = ContentParser()
        self.logger = logger
    
    async def create_note(
        self,
        group: MessageGroup,
        processing_msg: Message,
        user_id: int,
        user_kb: dict
    ) -> None:
        """
        Create a note from message group
        
        Args:
            group: Message group to process
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
            
            # Create KB manager and Git operations
            kb_manager = KnowledgeBaseManager(str(kb_path))
            kb_git_enabled = self.settings_manager.get_setting(user_id, "KB_GIT_ENABLED")
            git_ops = GitOperations(str(kb_path), enabled=kb_git_enabled)
            
            # Parse content
            content = await self.content_parser.parse_group_with_files(group, bot=self.bot)
            content_hash = self.content_parser.generate_hash(content)
            
            # Check if already processed
            if self.tracker.is_processed(content_hash):
                await self.bot.edit_message_text(
                    "✅ Это сообщение уже было обработано ранее",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Process with agent
            await self.bot.edit_message_text(
                "🤖 Анализирую контент...",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            
            user_agent = self.user_context_manager.get_or_create_agent(user_id)
            
            # Set working directory to user's KB path for qwen-code-cli agent
            # This ensures files created by the CLI are in the correct location
            if hasattr(user_agent, 'set_working_directory'):
                user_agent.set_working_directory(str(kb_path))
                self.logger.debug(f"Set agent working directory to: {kb_path}")
            
            try:
                processed_content = await user_agent.process(content)
            except Exception as agent_error:
                self.logger.error(f"Agent processing failed: {agent_error}", exc_info=True)
                await self.bot.edit_message_text(
                    f"❌ Ошибка обработки контента агентом:\n{str(agent_error)}\n\n"
                    f"Проверьте, что агент правильно настроен.",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
                return
            
            # Save to knowledge base
            await self._save_to_kb(
                kb_manager,
                git_ops,
                kb_path,
                processed_content,
                user_id,
                processing_msg
            )
            
            # Track processed message
            self._track_processed(group, content_hash, kb_path, processed_content)
            
            # Send success notification
            await self._send_success_notification(
                processing_msg,
                kb_path,
                processed_content
            )
            
        except Exception as e:
            self.logger.error(f"Error in note creation: {e}", exc_info=True)
            await self._send_error_notification(processing_msg, str(e))
    
    async def _save_to_kb(
        self,
        kb_manager: KnowledgeBaseManager,
        git_ops: GitOperations,
        kb_path: Path,
        processed_content: dict,
        user_id: int,
        processing_msg: Message
    ) -> None:
        """Save content to knowledge base"""
        await self.bot.edit_message_text(
            "💾 Сохраняю в базу знаний...",
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )
        
        # Extract metadata from processed content
        metadata = processed_content.get('metadata', {})
        kb_structure = processed_content.get('kb_structure')
        title = processed_content.get('title', 'Untitled Note')
        
        # Get files created/edited by agent
        files_created = metadata.get('files_created', [])
        files_edited = metadata.get('files_edited', [])
        folders_created = metadata.get('folders_created', [])
        
        # Validate that agent created at least some files
        if not files_created and not files_edited:
            raise ValueError("Agent did not create or edit any files")
        
        # Store first created file as primary kb_file for tracking
        # (for backward compatibility with tracking system)
        if files_created:
            processed_content['kb_file'] = files_created[0]
        elif files_edited:
            processed_content['kb_file'] = files_edited[0]
        else:
            processed_content['kb_file'] = 'unknown'
        
        # Update index for all created files
        if files_created and kb_structure:
            for file_path in files_created:
                # Convert to absolute path if relative
                abs_path = Path(file_path)
                if not abs_path.is_absolute():
                    abs_path = kb_path / file_path
                
                # Only add to index if it's a markdown file
                if abs_path.suffix == '.md' and abs_path.exists():
                    # Extract title from file if possible, otherwise use main title
                    file_title = self._extract_title_from_file(abs_path) or title
                    kb_manager.update_index(abs_path, file_title, kb_structure)
        
        # Git operations
        if git_ops.enabled:
            kb_git_auto_push = self.settings_manager.get_setting(user_id, "KB_GIT_AUTO_PUSH")
            kb_git_remote = self.settings_manager.get_setting(user_id, "KB_GIT_REMOTE")
            kb_git_branch = self.settings_manager.get_setting(user_id, "KB_GIT_BRANCH")
            
            # Add all created and edited files to git
            all_files = files_created + files_edited
            for file_path in all_files:
                abs_path = Path(file_path)
                if not abs_path.is_absolute():
                    abs_path = kb_path / file_path
                if abs_path.exists():
                    git_ops.add(str(abs_path))
            
            # Add index if it was updated
            index_path = kb_path / "index.md"
            if index_path.exists():
                git_ops.add(str(index_path))
            
            # Create commit message
            if len(files_created) == 1:
                commit_msg = f"Add: {title}"
            elif files_created:
                commit_msg = f"Add {len(files_created)} files: {title}"
            else:
                commit_msg = f"Update {len(files_edited)} files: {title}"
            
            git_ops.commit(commit_msg)
            
            if kb_git_auto_push:
                git_ops.push(kb_git_remote, kb_git_branch)
    
    def _track_processed(
        self,
        group: MessageGroup,
        content_hash: str,
        kb_path: Path,
        processed_content: dict
    ) -> None:
        """Track processed message"""
        if not group.messages:
            self.logger.warning("Skipping tracker entry for empty message group")
            return
        
        first_message = group.messages[0]
        message_ids = [msg.get('message_id') for msg in group.messages if msg.get('message_id')]
        chat_id = first_message.get('chat_id')
        
        if message_ids and chat_id:
            kb_file = processed_content.get('kb_file', 'unknown')
            self.tracker.add_processed(
                content_hash=content_hash,
                message_ids=message_ids,
                chat_id=chat_id,
                kb_file=str(kb_file),
                status="completed"
            )
    
    async def _send_success_notification(
        self,
        processing_msg: Message,
        kb_path: Path,
        processed_content: dict
    ) -> None:
        """Send success notification"""
        kb_structure = processed_content.get('kb_structure')
        title = processed_content.get('title', 'Untitled')
        kb_file = processed_content.get('kb_file')
        metadata = processed_content.get('metadata', {})
        
        category_str = kb_structure.category if kb_structure else "unknown"
        if kb_structure and kb_structure.subcategory:
            category_str += f"/{kb_structure.subcategory}"
        
        tags = kb_structure.tags if kb_structure else []
        
        # Формируем сообщение
        message_parts = [
            "✅ Сообщение успешно обработано и сохранено!\n",
            f"📁 Файл: `{Path(kb_file).name if kb_file else 'unknown'}`",
            f"📂 Категория: `{category_str}`",
            f"🏷 Теги: {', '.join(tags) if tags else 'нет'}"
        ]
        
        # Добавляем информацию о созданных файлах из метаданных агента
        files_created = metadata.get('files_created', [])
        files_edited = metadata.get('files_edited', [])
        folders_created = metadata.get('folders_created', [])
        
        if files_created or files_edited or folders_created:
            message_parts.append("\n📝 **Изменения:**")
            
            if files_created:
                message_parts.append(f"  ✨ Создано файлов: {len(files_created)}")
                for file in files_created[:5]:  # Показываем первые 5
                    message_parts.append(f"    • `{file}`")
                if len(files_created) > 5:
                    message_parts.append(f"    • ... и ещё {len(files_created) - 5}")
            
            if files_edited:
                message_parts.append(f"  ✏️ Изменено файлов: {len(files_edited)}")
                for file in files_edited[:5]:  # Показываем первые 5
                    message_parts.append(f"    • `{file}`")
                if len(files_edited) > 5:
                    message_parts.append(f"    • ... и ещё {len(files_edited) - 5}")
            
            if folders_created:
                message_parts.append(f"  📁 Создано папок: {len(folders_created)}")
                for folder in folders_created[:5]:  # Показываем первые 5
                    message_parts.append(f"    • `{folder}`")
                if len(folders_created) > 5:
                    message_parts.append(f"    • ... и ещё {len(folders_created) - 5}")
        
        await self.bot.edit_message_text(
            "\n".join(message_parts),
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id,
            parse_mode='Markdown'
        )
    
    async def _send_error_notification(
        self,
        processing_msg: Message,
        error_message: str
    ) -> None:
        """Send error notification"""
        try:
            await self.bot.edit_message_text(
                f"❌ Ошибка обработки сообщения: {error_message}",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
        except Exception:
            pass
    
    def _extract_title_from_file(self, file_path: Path) -> Optional[str]:
        """Extract title from markdown file (first # heading)"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
            
            # Try to extract from frontmatter
            if content.startswith('---'):
                import yaml
                try:
                    # Extract YAML frontmatter
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        if isinstance(frontmatter, dict) and 'title' in frontmatter:
                            return frontmatter['title']
                except:
                    pass
            
            return None
        except Exception as e:
            self.logger.debug(f"Failed to extract title from {file_path}: {e}")
            return None
