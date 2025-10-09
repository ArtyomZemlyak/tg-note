"""
Conversation Context Manager
Manages conversation history with token limits for context-aware agents
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from filelock import FileLock
from loguru import logger


class ConversationMessage:
    """A single message in conversation history"""

    def __init__(
        self, message_id: int, role: str, content: str, timestamp: int  # "user" or "assistant"
    ):
        self.message_id = message_id
        self.role = role
        self.content = content
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationMessage":
        """Create from dictionary"""
        return cls(
            message_id=data["message_id"],
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
        )

    def estimate_tokens(self) -> int:
        """
        Estimate token count for the message
        Simple estimation: ~4 characters per token
        """
        return len(self.content) // 4 + 10  # +10 for role and formatting


class ConversationContext:
    """Manages conversation context for a single user"""

    def __init__(self, user_id: int, max_tokens: int):
        self.user_id = user_id
        self.max_tokens = max_tokens
        self.messages: List[ConversationMessage] = []
        self.reset_from_message_id: Optional[int] = None

    def add_message(self, message_id: int, role: str, content: str, timestamp: int) -> None:
        """
        Add a message to context

        Args:
            message_id: Telegram message ID
            role: "user" or "assistant"
            content: Message content
            timestamp: Message timestamp
        """
        message = ConversationMessage(message_id, role, content, timestamp)
        self.messages.append(message)

        # Trim context to fit within token limit
        self._trim_to_token_limit()

    def get_context_messages(self) -> List[ConversationMessage]:
        """
        Get messages for context, respecting reset point

        Returns:
            List of messages to include in context
        """
        if self.reset_from_message_id is None:
            return self.messages

        # Filter messages after reset point
        filtered = []
        for msg in self.messages:
            if msg.message_id >= self.reset_from_message_id:
                filtered.append(msg)

        return filtered

    def reset_context(self, from_message_id: int) -> None:
        """
        Reset context from a specific message ID

        Args:
            from_message_id: Start reading context from this message ID
        """
        self.reset_from_message_id = from_message_id
        logger.info(f"User {self.user_id}: context reset from message {from_message_id}")

    def clear_reset(self) -> None:
        """Clear the reset marker"""
        self.reset_from_message_id = None

    def format_for_prompt(self) -> str:
        """
        Format context messages for inclusion in prompts

        Returns:
            Formatted context string
        """
        context_messages = self.get_context_messages()

        if not context_messages:
            return ""

        lines = ["# Предыдущий контекст разговора:"]
        for msg in context_messages:
            role_name = "Пользователь" if msg.role == "user" else "Ассистент"
            lines.append(f"\n**{role_name}:** {msg.content}")

        lines.append("\n---\n")
        return "\n".join(lines)

    def _trim_to_token_limit(self) -> None:
        """Trim messages to fit within token limit"""
        if not self.messages:
            return

        # Calculate total tokens
        total_tokens = sum(msg.estimate_tokens() for msg in self.messages)

        # Remove oldest messages until we fit in limit
        while total_tokens > self.max_tokens and len(self.messages) > 1:
            removed = self.messages.pop(0)
            total_tokens -= removed.estimate_tokens()
            logger.debug(
                f"User {self.user_id}: removed message {removed.message_id} "
                f"from context (tokens: {total_tokens}/{self.max_tokens})"
            )

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "user_id": self.user_id,
            "max_tokens": self.max_tokens,
            "messages": [msg.to_dict() for msg in self.messages],
            "reset_from_message_id": self.reset_from_message_id,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationContext":
        """Create from dictionary"""
        context = cls(user_id=data["user_id"], max_tokens=data["max_tokens"])
        context.messages = [
            ConversationMessage.from_dict(msg_data) for msg_data in data.get("messages", [])
        ]
        context.reset_from_message_id = data.get("reset_from_message_id")
        return context


class ConversationContextManager:
    """
    Manages conversation contexts for all users

    Responsibilities:
    - Store and retrieve conversation history
    - Manage per-user context with token limits
    - Handle context reset functionality
    - Persist context to disk
    """

    def __init__(
        self,
        storage_file: str = "./data/conversation_contexts.json",
        default_max_tokens: int = 2000,
    ):
        """
        Initialize conversation context manager

        Args:
            storage_file: Path to storage file
            default_max_tokens: Default max tokens per user context
        """
        self.storage_file = Path(storage_file)
        self.lock_file = Path(str(storage_file) + ".lock")
        self.default_max_tokens = default_max_tokens

        # In-memory cache
        self.contexts: Dict[int, ConversationContext] = {}

        # Ensure parent directory exists
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing contexts
        self._load_contexts()

        logger.info("ConversationContextManager initialized")

    def get_or_create_context(
        self, user_id: int, max_tokens: Optional[int] = None
    ) -> ConversationContext:
        """
        Get or create context for a user

        Args:
            user_id: User ID
            max_tokens: Max tokens for this context (uses default if None)

        Returns:
            ConversationContext for the user
        """
        if user_id not in self.contexts:
            tokens = max_tokens or self.default_max_tokens
            self.contexts[user_id] = ConversationContext(user_id, tokens)
            logger.debug(f"Created new context for user {user_id} (max_tokens: {tokens})")

        return self.contexts[user_id]

    def add_user_message(
        self,
        user_id: int,
        message_id: int,
        content: str,
        timestamp: int,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Add a user message to context

        Args:
            user_id: User ID
            message_id: Message ID
            content: Message content
            timestamp: Message timestamp
            max_tokens: Max tokens for context
        """
        context = self.get_or_create_context(user_id, max_tokens)
        context.add_message(message_id, "user", content, timestamp)
        self._save_contexts()

    def add_assistant_message(
        self,
        user_id: int,
        message_id: int,
        content: str,
        timestamp: int,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Add an assistant message to context

        Args:
            user_id: User ID
            message_id: Message ID (of bot's response)
            content: Message content
            timestamp: Message timestamp
            max_tokens: Max tokens for context
        """
        context = self.get_or_create_context(user_id, max_tokens)
        context.add_message(message_id, "assistant", content, timestamp)
        self._save_contexts()

    def get_context_for_prompt(self, user_id: int, enabled: bool = True) -> str:
        """
        Get formatted context for including in prompts

        Args:
            user_id: User ID
            enabled: Whether context is enabled for this user

        Returns:
            Formatted context string (empty if disabled)
        """
        if not enabled:
            return ""

        if user_id not in self.contexts:
            return ""

        return self.contexts[user_id].format_for_prompt()

    def reset_context(self, user_id: int, from_message_id: int) -> None:
        """
        Reset context for a user from a specific message

        Args:
            user_id: User ID
            from_message_id: Start reading context from this message
        """
        context = self.get_or_create_context(user_id)
        context.reset_context(from_message_id)
        self._save_contexts()

    def clear_context(self, user_id: int) -> None:
        """
        Completely clear context for a user

        Args:
            user_id: User ID
        """
        if user_id in self.contexts:
            del self.contexts[user_id]
            self._save_contexts()
            logger.info(f"Cleared context for user {user_id}")

    def update_max_tokens(self, user_id: int, max_tokens: int) -> None:
        """
        Update max tokens for a user's context

        Args:
            user_id: User ID
            max_tokens: New max tokens value
        """
        if user_id in self.contexts:
            self.contexts[user_id].max_tokens = max_tokens
            self.contexts[user_id]._trim_to_token_limit()
            self._save_contexts()
            logger.info(f"Updated max tokens for user {user_id} to {max_tokens}")

    def _load_contexts(self) -> None:
        """Load contexts from disk"""
        with FileLock(self.lock_file):
            try:
                if self.storage_file.exists():
                    with open(self.storage_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                        for user_id_str, context_data in data.items():
                            user_id = int(user_id_str)
                            self.contexts[user_id] = ConversationContext.from_dict(context_data)

                        logger.info(f"Loaded {len(self.contexts)} conversation contexts")
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in contexts file, starting fresh")
            except Exception as e:
                logger.error(f"Error loading contexts: {e}", exc_info=True)

    def _save_contexts(self) -> None:
        """Save contexts to disk"""
        with FileLock(self.lock_file):
            try:
                data = {
                    str(user_id): context.to_dict() for user_id, context in self.contexts.items()
                }

                with open(self.storage_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                logger.debug(f"Saved {len(self.contexts)} conversation contexts")
            except Exception as e:
                logger.error(f"Error saving contexts: {e}", exc_info=True)
                raise
