"""
Bot utility functions
"""

import re
from typing import List


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2 format
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text safe for MarkdownV2
    """
    # Characters that need to be escaped in MarkdownV2
    # Reference: https://core.telegram.org/bots/api#markdownv2-style
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram Markdown format
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text safe for Markdown
    """
    # Characters that need to be escaped in standard Markdown
    special_chars = r'_*[`'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)


def sanitize_for_telegram(text: str, parse_mode: str = 'Markdown') -> str:
    """
    Sanitize text for safe sending via Telegram
    
    Args:
        text: Text to sanitize
        parse_mode: Parse mode ('Markdown', 'MarkdownV2', 'HTML', or None)
    
    Returns:
        Sanitized text safe for the specified parse mode
    """
    if not text:
        return ""
    
    if parse_mode == 'MarkdownV2':
        return escape_markdown_v2(text)
    elif parse_mode == 'Markdown':
        return escape_markdown(text)
    elif parse_mode == 'HTML':
        # For HTML mode, escape HTML special characters
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    else:
        # No parse mode, return as is
        return text


async def safe_send_message(bot, chat_id: int, text: str, parse_mode: str = 'Markdown', **kwargs):
    """
    Safely send a message, falling back to no parse mode if formatting fails
    
    Args:
        bot: AsyncTeleBot instance
        chat_id: Chat ID to send message to
        text: Message text
        parse_mode: Parse mode to try first
        **kwargs: Additional arguments to pass to send_message
    
    Returns:
        Message object if successful
    """
    try:
        return await bot.send_message(chat_id, text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        # If it's a parsing error, retry without parse mode
        if "can't parse entities" in str(e).lower():
            try:
                return await bot.send_message(chat_id, text, parse_mode=None, **kwargs)
            except Exception:
                raise
        raise


async def safe_edit_message_text(bot, text: str, chat_id: int, message_id: int, parse_mode: str = 'Markdown', **kwargs):
    """
    Safely edit a message, falling back to no parse mode if formatting fails
    
    Args:
        bot: AsyncTeleBot instance
        text: New message text
        chat_id: Chat ID
        message_id: Message ID to edit
        parse_mode: Parse mode to try first
        **kwargs: Additional arguments to pass to edit_message_text
    
    Returns:
        Message object if successful
    """
    try:
        return await bot.edit_message_text(text, chat_id, message_id, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        # If it's a parsing error, retry without parse mode
        if "can't parse entities" in str(e).lower():
            try:
                return await bot.edit_message_text(text, chat_id, message_id, parse_mode=None, **kwargs)
            except Exception:
                raise
        raise


def is_user_allowed(user_id: int, allowed_ids: List[int]) -> bool:
    """
    Check if user is allowed to use the bot
    
    Args:
        user_id: Telegram user ID
        allowed_ids: List of allowed user IDs
    
    Returns:
        True if user is allowed, False otherwise
    """
    return user_id in allowed_ids


def format_status_message(status: str, details: str = "") -> str:
    """
    Format status message for user
    
    Args:
        status: Status type (processing, completed, error)
        details: Additional details
    
    Returns:
        Formatted status message
    """
    status_emoji = {
        "processing": "⏳",
        "completed": "✅",
        "error": "❌"
    }
    
    emoji = status_emoji.get(status, "ℹ️")
    message = f"{emoji} {status.capitalize()}"
    
    if details:
        message += f"\n{details}"
    
    return message