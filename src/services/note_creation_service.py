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
        
        # Agent может ничего не создать - это нормально
        # (например, агент просто проанализировал и решил, что создавать нечего)
        
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
        if git_ops.enabled and (files_created or files_edited):
            kb_git_auto_push = self.settings_manager.get_setting(user_id, "KB_GIT_AUTO_PUSH")
            kb_git_remote = self.settings_manager.get_setting(user_id, "KB_GIT_REMOTE")
            kb_git_branch = self.settings_manager.get_setting(user_id, "KB_GIT_BRANCH")
            
            # Add all created and edited files to git
            all_files = files_created + files_edited
            files_added = False
            
            for file_path in all_files:
                abs_path = Path(file_path)
                if not abs_path.is_absolute():
                    abs_path = kb_path / file_path
                if abs_path.exists():
                    git_ops.add(str(abs_path))
                    files_added = True
            
            # Add index if it was updated
            index_path = kb_path / "index.md"
            if index_path.exists() and files_created:
                git_ops.add(str(index_path))
                files_added = True
            
            # Only commit if we actually added files
            if files_added:
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
            self.tracker.add_processed(
                content_hash=content_hash,
                message_ids=message_ids,
                chat_id=chat_id,
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
        metadata = processed_content.get('metadata', {})
        
        tags = kb_structure.tags if kb_structure else []
        tags_str = ', '.join(tags) if tags else 'нет'
        
        # Формируем сообщение
        message_parts = [
            "✅ Сообщение успешно обработано!\n",
            f"🏷 Теги: {tags_str}"
        ]
        
        # Добавляем информацию о созданных файлах из метаданных агента
        files_created = metadata.get('files_created', [])
        files_edited = metadata.get('files_edited', [])
        folders_created = metadata.get('folders_created', [])
        
        # Убираем дублирование: если файл создан, не показываем его в изменённых
        files_created_set = set(files_created)
        files_edited_unique = [f for f in files_edited if f not in files_created_set]
        
        if files_created or files_edited_unique or folders_created:
            message_parts.append("\n📝 Изменения:")
            
            if files_created:
                message_parts.append(f"  ✨ Создано файлов: {len(files_created)}")
                for file in files_created[:5]:  # Показываем первые 5
                    message_parts.append(f"    • {file}")
                if len(files_created) > 5:
                    message_parts.append(f"    • ... и ещё {len(files_created) - 5}")
            
            if files_edited_unique:
                message_parts.append(f"  ✏️ Изменено файлов: {len(files_edited_unique)}")
                for file in files_edited_unique[:5]:  # Показываем первые 5
                    message_parts.append(f"    • {file}")
                if len(files_edited_unique) > 5:
                    message_parts.append(f"    • ... и ещё {len(files_edited_unique) - 5}")
            
            if folders_created:
                message_parts.append(f"  📁 Создано папок: {len(folders_created)}")
                for folder in folders_created[:5]:  # Показываем первые 5
                    message_parts.append(f"    • {folder}")
                if len(folders_created) > 5:
                    message_parts.append(f"    • ... и ещё {len(folders_created) - 5}")
        
        # Добавляем блок связей
        links = metadata.get('links', []) or metadata.get('relations', [])
        if links:
            message_parts.append("\n🔗 Связи:")
            for link in links[:10]:  # Показываем первые 10
                if isinstance(link, dict):
                    # Если связь это dict с полями 'file' и 'description'
                    file_path = link.get('file', '')
                    description = link.get('description', '')
                    if file_path:
                        if description:
                            message_parts.append(f"  • {file_path} - {description}")
                        else:
                            message_parts.append(f"  • {file_path}")
                else:
                    # Если связь это просто строка
                    message_parts.append(f"  • {link}")
            if len(links) > 10:
                message_parts.append(f"  • ... и ещё {len(links) - 10}")
        
        await self.bot.edit_message_text(
            "\n".join(message_parts),
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )
    
    async def _send_error_notification(
        self,
        processing_msg: Message,
        error_message: str
    ) -> None:
        """Send error notification"""
        try:
            # Don't use parse_mode for error messages to avoid parsing issues
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
