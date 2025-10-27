"""
Bot utility functions
"""

import re
from typing import List


def convert_html_for_telegram(html_text):
    """
    Convert unsupported HTML tags to Telegram-compatible HTML tags.
    
    Telegram supports only: 
    <b>, <i>, <u>, <s>, <a>, <code>, <pre>, <span>, <br>, <strong>, <em>
    
    Args:
        html_text (str): Original HTML text
        
    Returns:
        str: Telegram-compatible HTML text
    """
    if not html_text:
        return html_text
    
    # Mapping of unsupported tags to supported alternatives
    tag_conversions = {
        # Headings to bold + newline
        r'<h1[^>]*>': '<b>',
        r'</h1>': '</b>\n\n',
        r'<h2[^>]*>': '<b>',
        r'</h2>': '</b>\n\n',
        r'<h3[^>]*>': '<b>',
        r'</h3>': '</b>\n',
        r'<h4[^>]*>': '<b>',
        r'</h4>': '</b>\n',
        r'<h5[^>]*>': '<b>',
        r'</h5>': '</b>\n',
        r'<h6[^>]*>': '<b>',
        r'</h6>': '</b>\n',
        
        # Div to paragraph (with line breaks)
        r'<div[^>]*>': '<span>',
        r'</div>': '</span>\n',
        
        # Paragraph to span + line breaks
        r'<p[^>]*>': '<span>',
        r'</p>': '</span>\n\n',
        
        # Strong and em are supported, but ensure they're properly closed
        r'<strong>': '<b>',
        r'</strong>': '</b>',
        r'<em>': '<i>',
        r'</em>': '</i>',
        
        # Strike through
        r'<strike>': '<s>',
        r'</strike>': '</s>',
        r'<del>': '<s>',
        r'</del>': '</s>',
        
        # Remove unsupported tags but keep content
        r'</?section[^>]*>': '',
        r'</?article[^>]*>': '',
        r'</?nav[^>]*>': '',
        r'</?header[^>]*>': '',
        r'</?footer[^>]*>': '',
        r'</?aside[^>]*>': '',
    }
    
    converted_text = html_text
    
    # Apply tag conversions
    for pattern, replacement in tag_conversions.items():
        converted_text = re.sub(pattern, replacement, converted_text, flags=re.IGNORECASE)
    
    # Handle lists - convert to plain text with bullet points
    converted_text = convert_lists_to_telegram(converted_text)
    
    # Remove any remaining unsupported tags (keep content)
    unsupported_tags = ['main', 'figure', 'figcaption', 'details', 'summary', 'mark', 'small', 'abbr']
    for tag in unsupported_tags:
        converted_text = re.sub(rf'<(/)?{tag}[^>]*>', '', converted_text, flags=re.IGNORECASE)
    
    # Clean up multiple consecutive line breaks
    converted_text = re.sub(r'\n{3,}', '\n\n', converted_text)
    
    # Remove empty span tags
    converted_text = re.sub(r'<span[^>]*>\s*</span>', '', converted_text)

    converted_text = re.sub(r'<b><b>', '<b>', converted_text)
    converted_text = re.sub(r'</b></b>', '</b>', converted_text)
    converted_text = re.sub(r'</ul>', '</b>', converted_text)
    
    return converted_text.strip()

def convert_lists_to_telegram(html_text):
    """
    Convert HTML lists to Telegram-compatible format.
    
    Args:
        html_text (str): HTML text containing lists
        
    Returns:
        str: Text with lists converted to plain text format
    """
    text = html_text
    
    # Handle unordered lists (ul)
    ul_pattern = r'<ul[^>]*>(.*?)</ul>'
    while re.search(ul_pattern, text, re.IGNORECASE | re.DOTALL):
        text = re.sub(ul_pattern, convert_ul_list, text, flags=re.IGNORECASE | re.DOTALL)
    
    # Handle ordered lists (ol)
    ol_pattern = r'<ol[^>]*>(.*?)</ol>'
    while re.search(ol_pattern, text, re.IGNORECASE | re.DOTALL):
        text = re.sub(ol_pattern, convert_ol_list, text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove any remaining list item tags and convert to simple lines
    text = re.sub(r'<li[^>]*>', '• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    
    return text

def convert_ul_list(match):
    """
    Convert a single unordered list to Telegram format.
    
    Args:
        match: regex match object containing the list content
        
    Returns:
        str: Converted list text
    """
    list_content = match.group(1)
    # Extract list items
    li_items = re.findall(r'<li[^>]*>(.*?)</li>', list_content, re.IGNORECASE | re.DOTALL)
    
    converted_list = []
    for item in li_items:
        # Clean up the item content from any remaining HTML tags we don't want
        clean_item = re.sub(r'<[^>]+>', '', item)
        converted_list.append(f"• {clean_item.strip()}")
    
    return '\n'.join(converted_list) + '\n'

def convert_ol_list(match):
    """
    Convert a single ordered list to Telegram format.
    
    Args:
        match: regex match object containing the list content
        
    Returns:
        str: Converted list text
    """
    list_content = match.group(1)
    # Extract list items
    li_items = re.findall(r'<li[^>]*>(.*?)</li>', list_content, re.IGNORECASE | re.DOTALL)
    
    converted_list = []
    for i, item in enumerate(li_items, 1):
        # Clean up the item content from any remaining HTML tags we don't want
        clean_item = re.sub(r'<[^>]+>', '', item)
        converted_list.append(f"{i}. {clean_item.strip()}")
    
    return '\n'.join(converted_list) + '\n'


def escape_html(text: str) -> str:
       """
       Escape special HTML characters in text.
       
       Args:
           text: Text to escape
           
       Returns:
           str: Escaped text
       """
       if not text:
           return ""
       # Escape &, <, >, ", '
       html_escape_table = {
           "&": "&",
           "<": "<",
           ">": ">",
           '"': "\"",
           "'": "&#x27;",
       }
       text = "".join(html_escape_table.get(c, c) for c in text)

       return convert_html_for_telegram(text)


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
    special_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text)


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram Markdown format
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for Markdown
    """
    if not text:
        return ""
    
    # Characters that need to be escaped in Telegram Markdown (legacy)
    special_chars = r"_*`"
    
    # Pattern to match markdown links [text](url)
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    
    # Find all markdown links and store them with their positions
    links = []
    placeholder_counter = 0
    placeholder_map = {}
    
    def replace_link(match):
        nonlocal placeholder_counter
        placeholder = f"%%LINK_PLACEHOLDER_{placeholder_counter}%%"
        placeholder_counter += 1
        placeholder_map[placeholder] = (match.group(1), match.group(2))
        return placeholder
    
    # Replace links with placeholders
    text_with_placeholders = re.sub(link_pattern, replace_link, text)
    
    # Escape special characters ONLY in non-link parts
    escaped_text = re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text_with_placeholders)
    
    # Restore the original links (without escaping)
    for placeholder, (link_text, link_url) in placeholder_map.items():
        escaped_text = escaped_text.replace(placeholder, f"[{link_text}]({link_url})")
    
    return escaped_text


def escape_markdown_url(url: str) -> str:
    """
    Escape special characters for Telegram Markdown URL format
    Does NOT escape underscores as they are valid in URLs

    Args:
        url: URL to escape

    Returns:
        Escaped URL safe for Markdown links
    """
    # Only escape characters that break URLs, not underscores
    special_chars = r"*`"
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", url)


def sanitize_for_telegram(text: str, parse_mode: str = "Markdown") -> str:
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

    if parse_mode == "MarkdownV2":
        return escape_markdown_v2(text)
    elif parse_mode == "Markdown":
        return escape_markdown(text)
    elif parse_mode == "HTML":
        # For HTML mode, escape HTML special characters
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    else:
        # No parse mode, return as is
        return text


async def safe_send_message(bot, chat_id: int, text: str, parse_mode: str = "HTML", **kwargs):
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


async def safe_edit_message_text(
    bot, text: str, chat_id: int, message_id: int, parse_mode: str = "HTML", **kwargs
):
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
        return await bot.edit_message_text(
            text, chat_id, message_id, parse_mode=parse_mode, **kwargs
        )
    except Exception as e:
        # If it's a parsing error, retry without parse mode
        if "can't parse entities" in str(e).lower():
            try:
                return await bot.edit_message_text(
                    text, chat_id, message_id, parse_mode=None, **kwargs
                )
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
    status_emoji = {"processing": "⏳", "completed": "✅", "error": "❌"}

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
    lines = text.split("\n")

    for line in lines:
        # If a single line is longer than max_length, we need to split it
        if len(line) > max_length:
            # If current chunk is very small (< 500 chars), try to add part of long line to it
            if current_chunk and len(current_chunk) < 500:
                remaining_space = max_length - len(current_chunk) - 1  # -1 for newline
                current_chunk += "\n" + line[:remaining_space]
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
                chunk_part = line[i : i + max_length]
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
                current_chunk += "\n" + line if current_chunk else line

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks
