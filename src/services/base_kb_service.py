"""
Base Knowledge Base Service
Contains common functionality for KB-related services (note, agent modes)
Follows DRY (Don't Repeat Yourself) principle
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from src.bot.bot_port import BotPort
from src.bot.response_formatter import ResponseFormatter
from src.bot.settings_manager import SettingsManager
from src.bot.utils import safe_edit_message_text, split_long_message
from src.core.rate_limiter import RateLimiter
from src.knowledge_base.credentials_manager import CredentialsManager
from src.knowledge_base.git_ops import GitOperations
from src.knowledge_base.repository import RepositoryManager
from src.processor.content_parser import ContentParser


class BaseKBService:
    """
    Base class for KB-related services with common functionality.

    AICODE-NOTE: This base class extracts common patterns from NoteCreationService
    and AgentTaskService to minimize code duplication while maintaining clean
    separation of concerns.

    Common responsibilities:
    - Git operations setup and management
    - Agent working directory configuration
    - Rate limiting enforcement
    - Auto-commit and push operations
    - GitHub URL generation for file links
    - File change formatting for user notifications
    - Links/relations filtering and display
    - Safe message editing with timeout handling
    """

    def __init__(
        self,
        bot: BotPort,
        repo_manager: RepositoryManager,
        settings_manager: SettingsManager,
        credentials_manager: Optional[CredentialsManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize base KB service

        Args:
            bot: Bot messaging interface (transport abstraction)
            repo_manager: Repository manager
            settings_manager: Settings manager
            credentials_manager: Credentials manager (optional)
            rate_limiter: Rate limiter for agent calls (optional)
        """
        self.bot = bot
        self.repo_manager = repo_manager
        self.settings_manager = settings_manager
        self.credentials_manager = credentials_manager
        self.rate_limiter = rate_limiter
        self.content_parser = ContentParser()
        self.logger = logger

    def _setup_git_ops(self, kb_path: Path, user_id: int) -> GitOperations:
        """
        Setup Git operations handler with user-specific credentials.

        Args:
            kb_path: Path to knowledge base
            user_id: User ID for settings lookup

        Returns:
            Configured GitOperations instance
        """
        kb_git_enabled = self.settings_manager.get_setting(user_id, "KB_GIT_ENABLED")

        # Get global Git credentials for HTTPS authentication (fallback)
        github_username = self.settings_manager.get_setting(user_id, "GITHUB_USERNAME")
        github_token = self.settings_manager.get_setting(user_id, "GITHUB_TOKEN")
        gitlab_username = self.settings_manager.get_setting(user_id, "GITLAB_USERNAME")
        gitlab_token = self.settings_manager.get_setting(user_id, "GITLAB_TOKEN")

        return GitOperations(
            str(kb_path),
            enabled=kb_git_enabled,
            github_username=github_username,
            github_token=github_token,
            gitlab_username=gitlab_username,
            gitlab_token=gitlab_token,
            user_id=user_id,
            credentials_manager=self.credentials_manager,
        )

    def _get_agent_working_dir(self, kb_path: Path, user_id: int) -> Path:
        """
        Get agent working directory based on KB_TOPICS_ONLY setting.

        Args:
            kb_path: Path to knowledge base root
            user_id: User ID for settings lookup

        Returns:
            Path to agent working directory (kb_path or kb_path/topics)
        """
        kb_topics_only = self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY")

        if kb_topics_only:
            # Restrict to topics folder (protects index.md, README.md, etc.)
            agent_working_dir = kb_path / "topics"
            self.logger.debug("KB_TOPICS_ONLY=true, restricting agent to topics folder")

            # AICODE-NOTE: Ensure topics directory exists (important for GitHub repos)
            # When cloning from GitHub, the repo might not have a topics/ directory,
            # but we need it for agent operations when KB_TOPICS_ONLY=true
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
            self.logger.debug("KB_TOPICS_ONLY=false, agent has full KB access")

        return agent_working_dir

    def _configure_agent_working_dir(self, agent, working_dir: Path) -> None:
        """
        Configure agent's working directory if supported.

        Args:
            agent: Agent instance
            working_dir: Working directory path
        """
        if hasattr(agent, "set_working_directory"):
            agent.set_working_directory(str(working_dir))
            self.logger.debug(f"Set agent working directory to: {working_dir}")

    async def _check_rate_limit(self, user_id: int, chat_id: int, processing_msg_id: int) -> bool:
        """
        Check rate limit before agent API call.

        AICODE-NOTE: Rate limiting prevents abuse and controls API costs.

        Args:
            user_id: User ID
            chat_id: Chat ID for notification
            processing_msg_id: Message ID for status updates

        Returns:
            True if request is allowed, False if rate limited
        """
        if not self.rate_limiter:
            return True

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
            return False

        return True

    async def _auto_commit_and_push(
        self,
        git_ops: GitOperations,
        user_id: int,
        commit_message: str,
        chat_id: Optional[int] = None,
        processing_msg_id: Optional[int] = None,
    ) -> tuple[bool, str]:
        """
        Auto-commit and push changes to remote repository.

        AICODE-NOTE: This ensures that all KB changes are committed and pushed
        before releasing KB lock, maintaining consistency across multiple users.

        Args:
            git_ops: Git operations handler
            user_id: User ID for settings lookup
            commit_message: Commit message
            chat_id: Chat ID for status updates (optional)
            processing_msg_id: Message ID for status updates (optional)

        Returns:
            Tuple of (success, message)
        """
        if not git_ops.enabled:
            return True, "Git not enabled"

        # Update status message if provided
        if chat_id and processing_msg_id:
            await self.bot.edit_message_text(
                "📤 Сохраняю изменения в git...",
                chat_id=chat_id,
                message_id=processing_msg_id,
            )

        # Get git settings
        kb_git_remote = self.settings_manager.get_setting(user_id, "KB_GIT_REMOTE")
        kb_git_branch = self.settings_manager.get_setting(user_id, "KB_GIT_BRANCH")

        # Auto-commit and push
        success, message = git_ops.auto_commit_and_push(
            message=commit_message,
            remote=kb_git_remote,
            branch=kb_git_branch,
        )

        if not success:
            self.logger.warning(f"Auto-commit/push failed: {message}")
        else:
            self.logger.info(f"Auto-commit/push successful: {message}")

        return success, message

    def _get_github_base_url(self, kb_path: Path, user_id: int) -> Optional[str]:
        """
        Generate GitHub base URL for file links.

        Args:
            kb_path: Path to knowledge base
            user_id: User ID for settings lookup

        Returns:
            GitHub base URL or None if not available
        """
        try:
            from git import Repo  # type: ignore

            repo = Repo(kb_path)
            remote_name = self.settings_manager.get_setting(user_id, "KB_GIT_REMOTE") or "origin"
            branch = self.settings_manager.get_setting(user_id, "KB_GIT_BRANCH") or "main"

            try:
                remote = repo.remote(remote_name)
            except Exception:
                return None

            url = next(iter(remote.urls), None)
            if not url:
                return None

            url_str = str(url)
            # Support formats:
            # - https://github.com/user/repo(.git)?
            # - https://user:token@github.com/user/repo(.git)?
            # - git@github.com:user/repo(.git)?
            if url_str.startswith("git@github.com:"):
                repo_path = url_str.split(":", 1)[1]
                if repo_path.endswith(".git"):
                    repo_path = repo_path[:-4]
                return f"https://github.com/{repo_path}/blob/{branch}"

            # HTTP(S) URLs
            from urllib.parse import urlsplit

            parts = urlsplit(url_str)
            # Only allow github.com
            if not parts.netloc.endswith("github.com"):
                return None

            # Clean path without .git and without credentials
            path = parts.path or ""
            if path.endswith(".git"):
                path = path[:-4]
            # Ensure path starts with '/'
            if not path.startswith("/"):
                path = "/" + path

            return f"https://github.com{path}/blob/{branch}"
        except Exception:
            return None

    def _extract_title_from_file(self, file_path: Path) -> Optional[str]:
        """
        Extract title from markdown file (first # heading or frontmatter).

        Args:
            file_path: Path to markdown file

        Returns:
            Extracted title or None
        """
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

    async def _safe_edit_message(
        self, text: str, chat_id: int, message_id: int, parse_mode: Optional[str] = None
    ) -> bool:
        """
        Safely edit a message with timeout handling.

        Args:
            text: Message text
            chat_id: Chat ID
            message_id: Message ID to edit
            parse_mode: Parse mode (e.g., 'Markdown')

        Returns:
            True if edit succeeded, False if we should send a new message instead
        """
        try:
            await safe_edit_message_text(
                self.bot, text, chat_id=chat_id, message_id=message_id, parse_mode=parse_mode
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

    async def _send_error_notification(
        self, processing_msg_id: int, chat_id: int, error_message: str
    ) -> None:
        """
        Send error notification to user.

        Args:
            processing_msg_id: ID of the processing status message
            chat_id: Chat ID
            error_message: Error message to display
        """
        try:
            error_text = f"❌ Ошибка: {error_message}"

            # Try to edit the message, fall back to new message if timeout
            edit_succeeded = await self._safe_edit_message(
                error_text, chat_id=chat_id, message_id=processing_msg_id
            )

            # If edit failed due to timeout, send as new message
            if not edit_succeeded:
                await self.bot.send_message(chat_id=chat_id, text=error_text)
        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}", exc_info=True)

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
        # Use response formatter to format the result
        github_base = self._get_github_base_url(kb_path, user_id)
        kb_topics_only = self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY")
        if kb_topics_only:
            github_base = f"{github_base}/topics"

        # AICODE-NOTE: Get min description length for link filtering
        min_link_desc_length = self.settings_manager.get_setting(
            user_id, "KB_LINKS_MIN_DESCRIPTION_LENGTH"
        )

        response_formatter = ResponseFormatter(github_base, min_link_desc_length)
        full_message = response_formatter.to_html(result.get("parsed_result"))

        # Handle long messages by splitting them. We avoid pre-escaping here to keep links clickable.
        message_chunks = split_long_message(full_message)

        edit_succeeded = await self._safe_edit_message(
            message_chunks[0],
            chat_id=chat_id,
            message_id=processing_msg_id,
            parse_mode="HTML",
        )

        # If edit failed (e.g., timeout), send as new message
        if not edit_succeeded:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Результат:\n\n{message_chunks[0]}",
                parse_mode="HTML",
            )

        # If there are more chunks, send them as separate messages
        for i, chunk in enumerate(message_chunks[1:], start=2):
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"💡 (часть {i}/{len(message_chunks)}):\n\n{chunk}",
                parse_mode="HTML",
            )
