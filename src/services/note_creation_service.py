"""
Note Creation Service
Handles the creation of notes in the knowledge base
Follows Single Responsibility Principle
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from src.bot.bot_port import BotPort
from src.bot.settings_manager import SettingsManager
from src.core.rate_limiter import RateLimiter
from src.knowledge_base.git_ops import GitOperations
from src.knowledge_base.manager import KnowledgeBaseManager
from src.knowledge_base.repository import RepositoryManager
from src.knowledge_base.sync_manager import get_sync_manager
from src.processor.content_parser import ContentParser
from src.processor.message_aggregator import MessageGroup
from src.services.interfaces import INoteCreationService, IUserContextManager
from src.tracker.processing_tracker import ProcessingTracker


class NoteCreationService(INoteCreationService):
    """
    Service for creating notes in the knowledge base (note mode).

    Responsibilities:
    - Parse message content (text, media, forwarded messages)
    - Process content with agent (extract key information)
    - Save structured notes to knowledge base
    - Handle git operations (commit, push)
    - Track processed messages to avoid duplicates
    - Enforce rate limits to prevent abuse

    This service is activated when user is in 'note' mode (/note command).
    """

    def __init__(
        self,
        bot: BotPort,
        tracker: ProcessingTracker,
        repo_manager: RepositoryManager,
        user_context_manager: IUserContextManager,
        settings_manager: SettingsManager,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize note creation service

        Args:
            bot: Bot messaging interface (transport abstraction)
            tracker: Processing tracker
            repo_manager: Repository manager
            user_context_manager: User context manager
            settings_manager: Settings manager
            rate_limiter: Rate limiter for agent calls (optional)
        """
        self.bot = bot
        self.tracker = tracker
        self.repo_manager = repo_manager
        self.user_context_manager = user_context_manager
        self.settings_manager = settings_manager
        self.rate_limiter = rate_limiter
        self.content_parser = ContentParser()
        self.logger = logger

    async def create_note(
        self, group: MessageGroup, processing_msg_id: int, chat_id: int, user_id: int, user_kb: dict
    ) -> None:
        """
        Create a note from message group

        Args:
            group: Message group to process
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID where message group was sent
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

            # AICODE-NOTE: Use sync manager to serialize KB operations and prevent conflicts
            # when multiple users work with the same knowledge base
            sync_manager = get_sync_manager()

            # Acquire lock for this KB to ensure operations are serialized
            async with sync_manager.with_kb_lock(str(kb_path), f"create_note_user_{user_id}"):
                await self._create_note_locked(
                    group, processing_msg_id, chat_id, user_id, user_kb, kb_path
                )

        except Exception as e:
            self.logger.error(f"Error in note creation: {e}", exc_info=True)
            await self._send_error_notification(processing_msg_id, chat_id, str(e))

    async def _create_note_locked(
        self,
        group: MessageGroup,
        processing_msg_id: int,
        chat_id: int,
        user_id: int,
        user_kb: dict,
        kb_path: Path,
    ) -> None:
        """
        Create note with KB lock already acquired.
        This method performs the actual note creation work.

        Args:
            group: Message group to process
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID where message group was sent
            user_id: User ID
            user_kb: User's knowledge base configuration
            kb_path: Path to knowledge base
        """
        # Create KB manager and Git operations
        kb_manager = KnowledgeBaseManager(str(kb_path))
        kb_git_enabled = self.settings_manager.get_setting(user_id, "KB_GIT_ENABLED")

        # Get GitHub credentials for HTTPS authentication
        github_username = self.settings_manager.get_setting(user_id, "GITHUB_USERNAME")
        github_token = self.settings_manager.get_setting(user_id, "GITHUB_TOKEN")

        git_ops = GitOperations(
            str(kb_path),
            enabled=kb_git_enabled,
            github_username=github_username,
            github_token=github_token,
        )

        # AICODE-NOTE: Pull latest changes from remote before working with KB
        # This prevents conflicts when multiple users work with the same KB
        if git_ops.enabled and user_kb.get("kb_type") == "github":
            await self.bot.edit_message_text(
                "🔄 Синхронизация с GitHub...", chat_id=chat_id, message_id=processing_msg_id
            )

            kb_git_remote = self.settings_manager.get_setting(user_id, "KB_GIT_REMOTE")
            kb_git_branch = self.settings_manager.get_setting(user_id, "KB_GIT_BRANCH")

            success, message = git_ops.pull(kb_git_remote, kb_git_branch)
            if not success:
                # If pull failed due to conflicts or other issues, notify user
                await self.bot.edit_message_text(
                    f"❌ Ошибка при синхронизации с GitHub:\n{message}\n\n"
                    f"Возможно, есть конфликты. Проверьте репозиторий вручную.",
                    chat_id=chat_id,
                    message_id=processing_msg_id,
                )
                return

            # Parse content
            content = await self.content_parser.parse_group_with_files(group, bot=self.bot)
            content_hash = self.content_parser.generate_hash(content)

            # Check if already processed
            if self.tracker.is_processed(content_hash):
                await self.bot.edit_message_text(
                    "✅ Это сообщение уже было обработано ранее",
                    chat_id=chat_id,
                    message_id=processing_msg_id,
                )
                return

            # Process with agent
            await self.bot.edit_message_text(
                "🤖 Анализирую контент...", chat_id=chat_id, message_id=processing_msg_id
            )

            self.logger.debug(f"[NOTE_SERVICE] Getting agent for user {user_id}")
            user_agent = await self.user_context_manager.get_or_create_agent(user_id)

            # Set working directory to user's KB for qwen-code-cli agent
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
                self.logger.info(f"[NOTE_SERVICE] Processing content with agent for user {user_id}")
                processed_content = await user_agent.process(content)
            except Exception as agent_error:
                self.logger.error(f"Agent processing failed: {agent_error}", exc_info=True)
                await self.bot.edit_message_text(
                    f"❌ Ошибка обработки контента агентом:\n{str(agent_error)}\n\n"
                    f"Проверьте, что агент правильно настроен.",
                    chat_id=chat_id,
                    message_id=processing_msg_id,
                )
                return

            # Save to knowledge base
            await self._save_to_kb(
                kb_manager,
                git_ops,
                kb_path,
                agent_working_dir,
                processed_content,
                user_id,
                processing_msg_id,
                chat_id,
            )

            # Track processed message
            self._track_processed(group, content_hash, kb_path, processed_content)

            # AICODE-NOTE: Auto-commit and push changes before releasing KB lock
            # This ensures that all KB changes are committed and pushed to remote (if configured)
            # before another user can start working with the same KB
            if git_ops.enabled:
                await self.bot.edit_message_text(
                    "📤 Сохраняю изменения в git...", chat_id=chat_id, message_id=processing_msg_id
                )

                # Get git settings
                kb_git_remote = self.settings_manager.get_setting(user_id, "KB_GIT_REMOTE")
                kb_git_branch = self.settings_manager.get_setting(user_id, "KB_GIT_BRANCH")

                # Create commit message
                commit_message = f"Add: {processed_content.get('title', 'Untitled Note')}"

                # Auto-commit and push
                success, message = git_ops.auto_commit_and_push(
                    message=commit_message,
                    remote=kb_git_remote,
                    branch=kb_git_branch,
                )

                if not success:
                    logger.warning(f"Auto-commit/push failed: {message}")
                else:
                    logger.info(f"Auto-commit/push successful: {message}")

            # Send success notification
            await self._send_success_notification(
                processing_msg_id, chat_id, kb_path, processed_content
            )

    async def _save_to_kb(
        self,
        kb_manager: KnowledgeBaseManager,
        git_ops: GitOperations,
        kb_path: Path,
        agent_working_dir: Path,
        processed_content: dict,
        user_id: int,
        processing_msg_id: int,
        chat_id: int,
    ) -> None:
        """
        Save content to knowledge base.

        Handles:
        - Extracting metadata from processed content
        - Updating index for created files
        - Git operations (add, commit, push)

        Args:
            kb_manager: Knowledge base manager
            git_ops: Git operations handler
            kb_path: Path to knowledge base root
            agent_working_dir: Working directory used by agent (may be kb_path or kb_path/topics)
            processed_content: Processed content from agent
            user_id: User ID
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID
        """
        await self.bot.edit_message_text(
            "💾 Сохраняю в базу знаний...", chat_id=chat_id, message_id=processing_msg_id
        )

        # Extract metadata from processed content
        metadata = processed_content.get("metadata", {})
        kb_structure = processed_content.get("kb_structure")
        title = processed_content.get("title", "Untitled Note")

        # Get files created/edited by agent
        files_created = metadata.get("files_created", [])
        files_edited = metadata.get("files_edited", [])
        folders_created = metadata.get("folders_created", [])

        # Agent может ничего не создать - это нормально
        # (например, агент просто проанализировал и решил, что создавать нечего)

        # Update index for all created files
        if files_created and kb_structure:
            for file_path in files_created:
                # Convert to absolute path if relative
                # Agent returns paths relative to its working directory
                abs_path = Path(file_path)
                if not abs_path.is_absolute():
                    # Use agent_working_dir as base for relative paths
                    abs_path = agent_working_dir / file_path

                # Only add to index if it's a markdown file
                if abs_path.suffix == ".md" and abs_path.exists():
                    # Extract title from file if possible, otherwise use main title
                    file_title = self._extract_title_from_file(abs_path) or title
                    kb_manager.update_index(abs_path, file_title, kb_structure)

        # AICODE-NOTE: Git operations (add/commit/push) are now handled automatically
        # by auto_commit_and_push() after _save_to_kb completes, before releasing KB lock.
        # This ensures proper transaction-like behavior with locking.

    def _track_processed(
        self, group: MessageGroup, content_hash: str, kb_path: Path, processed_content: dict
    ) -> None:
        """Track processed message"""
        if not group.messages:
            self.logger.warning("Skipping tracker entry for empty message group")
            return

        first_message = group.messages[0]
        message_ids = [msg.get("message_id") for msg in group.messages if msg.get("message_id")]
        chat_id = first_message.get("chat_id")

        if message_ids and chat_id:
            self.tracker.add_processed(
                content_hash=content_hash,
                message_ids=message_ids,
                chat_id=chat_id,
                status="completed",
            )

    async def _send_success_notification(
        self, processing_msg_id: int, chat_id: int, kb_path: Path, processed_content: dict
    ) -> None:
        """Send success notification"""
        kb_structure = processed_content.get("kb_structure")
        metadata = processed_content.get("metadata", {})

        tags = kb_structure.tags if kb_structure else []
        tags_str = ", ".join(tags) if tags else "нет"

        # Формируем сообщение
        message_parts = ["✅ Сообщение успешно обработано!\n", f"🏷 Теги: {tags_str}"]

        # Добавляем информацию о созданных файлах из метаданных агента
        files_created = metadata.get("files_created", [])
        files_edited = metadata.get("files_edited", [])
        folders_created = metadata.get("folders_created", [])

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
        links = metadata.get("links", []) or metadata.get("relations", [])
        if links:
            message_parts.append("\n🔗 Связи:")
            for link in links[:10]:  # Показываем первые 10
                if isinstance(link, dict):
                    # Если связь это dict с полями 'file' и 'description'
                    file_path = link.get("file", "")
                    description = link.get("description", "")
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
            "\n".join(message_parts), chat_id=chat_id, message_id=processing_msg_id
        )

    async def _send_error_notification(
        self, processing_msg_id: int, chat_id: int, error_message: str
    ) -> None:
        """Send error notification"""
        try:
            # Don't use parse_mode for error messages to avoid parsing issues
            await self.bot.edit_message_text(
                f"❌ Ошибка обработки сообщения: {error_message}",
                chat_id=chat_id,
                message_id=processing_msg_id,
            )
        except Exception:
            pass

    def _extract_title_from_file(self, file_path: Path) -> Optional[str]:
        """Extract title from markdown file (first # heading)"""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            for line in lines:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()

            # Try to extract from frontmatter
            if content.startswith("---"):
                import yaml

                try:
                    # Extract YAML frontmatter
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        if isinstance(frontmatter, dict) and "title" in frontmatter:
                            return frontmatter["title"]
                except:
                    pass

            return None
        except Exception as e:
            self.logger.debug(f"Failed to extract title from {file_path}: {e}")
            return None
