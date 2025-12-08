"""
Base Knowledge Base Service
Contains common functionality for KB-related services (note, agent modes)
Follows DRY (Don't Repeat Yourself) principle
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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
from src.processor.markdown_link_fixer import (
    LinkValidationResult,
    validate_and_fix_links_before_commit,
)


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
        # ContentParser initialization deferred - will be created per-user with kb_topics_only setting
        self.logger = logger

    def _get_content_parser(self, user_id: int) -> ContentParser:
        """
        Get ContentParser instance with correct kb_topics_only setting for user.

        Args:
            user_id: User ID for settings lookup

        Returns:
            ContentParser instance configured for user
        """
        kb_topics_only = self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY")
        return ContentParser(kb_topics_only=kb_topics_only)

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

        IMPORTANT: Validates and fixes markdown links (images and internal pages)
        before committing to prevent broken links in KB.

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

        # AICODE-NOTE: Validate and fix markdown links before commit
        # This prevents broken image/link paths from being committed
        validation_result = await self._validate_and_fix_markdown_links(git_ops.repo_path)

        if validation_result and validation_result.has_changes():
            self.logger.info(
                f"Fixed {validation_result.images_fixed} images and "
                f"{validation_result.links_fixed} links before commit"
            )

        # Update status message if provided
        if chat_id and processing_msg_id:
            status_text = "📤 Сохраняю изменения в git..."
            if validation_result and validation_result.has_broken_links():
                status_text += f"\n⚠️ Некоторые ссылки требуют ручного исправления"
            await self.bot.edit_message_text(
                status_text,
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
        self,
        text: str,
        chat_id: int,
        message_id: int,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: Optional[bool] = None,
    ) -> bool:
        """
        Safely edit a message with timeout handling.

        Args:
            text: Message text
            chat_id: Chat ID
            message_id: Message ID to edit
            parse_mode: Parse mode (e.g., 'Markdown')
            disable_web_page_preview: Disable link previews when editing messages

        Returns:
            True if edit succeeded, False if we should send a new message instead
        """
        try:
            await safe_edit_message_text(
                self.bot,
                text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
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
        processing_msg_id: int | List[int],
        chat_id: int,
        result: dict,
        kb_path: Path,
        user_id: int,
    ) -> None:
        """
        Send task result to user

        Args:
            processing_msg_id: ID (or list of IDs) of the processing status message(s)
            chat_id: Chat ID
            result: Task execution result
        """
        github_base = self._get_github_base_url(kb_path, user_id)
        kb_topics_only = self.settings_manager.get_setting(user_id, "KB_TOPICS_ONLY")
        if kb_topics_only:
            github_base = f"{github_base}/topics"

        message_break_after = self._get_response_message_breaks(user_id)

        response_formatter = ResponseFormatter(
            github_base, message_break_after=message_break_after
        )

        parsed_result = result.get("parsed_result")
        if not parsed_result:
            # Fallback: parse markdown if parsed_result is missing
            parsed_result = response_formatter.parse(result.get("markdown", "") or "")

        messages = response_formatter.to_messages_html(parsed_result)
        if not messages:
            # Fallback to single-block rendering
            fallback_html = response_formatter.to_html(parsed_result or {})
            messages = [fallback_html] if fallback_html else [result.get("markdown", "")]

        # Respect Telegram length limits per message
        message_chunks: List[str] = []
        for msg in messages:
            message_chunks.extend(split_long_message(msg))

        if not message_chunks:
            self.logger.warning("No message content to send")
            return

        message_ids = self._normalize_processing_message_ids(processing_msg_id)
        total_parts = len(message_chunks)

        # Update existing placeholders first
        for idx, chunk in enumerate(message_chunks):
            text = chunk if idx == 0 else f"💡 (часть {idx+1}/{total_parts}):\n\n{chunk}"

            if idx < len(message_ids):
                await self._safe_edit_message(
                    text,
                    chat_id=chat_id,
                    message_id=message_ids[idx],
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            else:
                sent = await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                message_ids.append(sent.message_id)

        # Clear unused placeholders, if any
        if len(message_ids) > total_parts:
            for orphan_id in message_ids[total_parts:]:
                await self._safe_edit_message(
                    "✅ Готово",
                    chat_id=chat_id,
                    message_id=orphan_id,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )

    def _get_response_message_breaks(self, user_id: int) -> List[str]:
        """Return configured field names after which to insert message breaks."""
        raw_value = self.settings_manager.get_setting(user_id, "MESSAGE_RESPONSE_BREAK_AFTER")

        if isinstance(raw_value, list):
            return [str(item).strip() for item in raw_value if str(item).strip()]

        if isinstance(raw_value, str):
            parts = [item.strip() for item in raw_value.split(",")]
            return [p for p in parts if p]

        return []

    async def _prepare_processing_placeholders(
        self,
        chat_id: int,
        processing_msg_id: int,
        count: int,
        text: str = "Анализирую контент...",
    ) -> List[int]:
        """
        Ensure required number of processing placeholders are present.

        Returns list of message IDs (first is the original processing_msg_id).
        """
        count = max(1, count)
        message_ids = [processing_msg_id]

        await self._safe_edit_message(text, chat_id=chat_id, message_id=processing_msg_id)

        for _ in range(count - 1):
            sent = await self.bot.send_message(
                chat_id=chat_id, text=text, disable_web_page_preview=True
            )
            message_ids.append(sent.message_id)

        return message_ids

    def _normalize_processing_message_ids(self, value: int | List[int]) -> List[int]:
        """Normalize processing message IDs to a list."""
        if isinstance(value, list):
            return value
        return [value]


    async def _validate_and_fix_markdown_links(
        self, kb_path: Path
    ) -> Optional[LinkValidationResult]:
        """
        Validate and fix markdown links before commit.

        Checks:
        - Image paths: ![alt](path)
        - Internal markdown links: [text](page.md)

        Auto-fixes:
        - Calculates correct relative paths
        - Finds files by name if path is wrong
        - Adds TODO comments if can't fix

        Args:
            kb_path: Path to knowledge base

        Returns:
            LinkValidationResult or None if validation disabled/failed
        """
        try:
            # Get list of changed markdown files from git status
            # This is more efficient than checking all files
            changed_files = self._get_changed_markdown_files(kb_path)

            if not changed_files:
                self.logger.debug("No markdown files changed, skipping link validation")
                return None

            self.logger.info(
                f"Validating and fixing links in {len(changed_files)} changed markdown files..."
            )

            # Run validation and auto-fix
            result = validate_and_fix_links_before_commit(kb_path, changed_files)

            # Log results
            if result.has_changes():
                self.logger.info(f"✓ Fixed links: {result}")

            if result.has_broken_links():
                self.logger.warning(
                    f"⚠️ Some links could not be fixed automatically. "
                    f"TODO comments added: {result.images_broken} images, "
                    f"{result.links_broken} links"
                )

            return result

        except Exception as e:
            self.logger.error(f"Error during link validation: {e}", exc_info=True)
            return None

    def _get_changed_markdown_files(self, kb_path: Path) -> List[Path]:
        """
        Get list of markdown files that have been modified/added.

        Args:
            kb_path: Path to knowledge base

        Returns:
            List of changed markdown file paths
        """
        try:
            # Try to use GitOperations to get changed files
            git_ops = GitOperations(kb_path)
            if not git_ops.enabled:
                # Git not enabled, check all markdown files
                return list(kb_path.rglob("*.md"))

            # Get status of modified/added files
            changed = []
            for item in git_ops.repo.index.diff(None):  # Modified files
                file_path = kb_path / item.a_path
                if file_path.suffix == ".md" and file_path.exists():
                    changed.append(file_path)

            for item in git_ops.repo.untracked_files:  # Untracked files
                file_path = kb_path / item
                if file_path.suffix == ".md" and file_path.exists():
                    changed.append(file_path)

            return changed

        except Exception as e:
            self.logger.warning(f"Could not get git status, checking all markdown files: {e}")
            # Fallback: check all markdown files
            return list(kb_path.rglob("*.md"))
