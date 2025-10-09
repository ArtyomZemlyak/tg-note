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
        bot: BotPort or AsyncTeleBot instance (BotPort includes retry/throttling)
        chat_id: Chat ID to send message to
        text: Message text
        parse_mode: Parse mode to try first
        **kwargs: Additional arguments to pass to send_message
    
    Returns:
        Message object if successful
    
    Note: If using BotPort, retry and rate limiting are handled automatically.
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
        bot: BotPort or AsyncTeleBot instance (BotPort includes retry/throttling)
        text: New message text
        chat_id: Chat ID
        message_id: Message ID to edit
        parse_mode: Parse mode to try first
        **kwargs: Additional arguments to pass to edit_message_text
    
    Returns:
        Message object if successful
    
    Note: If using BotPort, retry and rate limiting are handled automatically.
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


def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """
    Split a long message into chunks that fit within Telegram's message length limit
    
    Telegram has a 4096 character limit for messages. This function splits messages
    at line boundaries when possible to maintain readability.
    
    Args:
        text: Text to split
        max_length: Maximum length per chunk (default 4000 to leave buffer)
    
    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by lines to avoid breaking in the middle of a line
    lines = text.split('\n')
    
    for line in lines:
        # If a single line is longer than max_length, we need to split it
        if len(line) > max_length:
            # If current chunk is very small (< 500 chars), try to add part of long line to it
            if current_chunk and len(current_chunk) < 500:
                remaining_space = max_length - len(current_chunk) - 1  # -1 for newline
                current_chunk += '\n' + line[:remaining_space]
                chunks.append(current_chunk)
                # Process the rest of the line
                line = line[remaining_space:]
                current_chunk = ""
            elif current_chunk:
                # Save current chunk if it has content
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Split the long line into smaller parts
            for i in range(0, len(line), max_length):
                chunk_part = line[i:i + max_length]
                if i + max_length >= len(line):
                    # Last part of the long line, keep it for potential merging
                    current_chunk = chunk_part
                else:
                    chunks.append(chunk_part)
        else:
            # Check if adding this line would exceed the limit
            if len(current_chunk) + len(line) + 1 > max_length:
                # Save current chunk and start a new one
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line
            else:
                # Add line to current chunk
                current_chunk += '\n' + line if current_chunk else line
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks