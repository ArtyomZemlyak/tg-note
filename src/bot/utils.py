"""
Bot utility functions
"""

import re
from typing import List


def _validate_html_content(text: str, skip_links_and_spoilers: bool = False) -> str:
    """
    Internal function to validate HTML content.

    Args:
        text: HTML text to validate
        skip_links_and_spoilers: If True, skip processing links and spoilers (for nested content)

    Returns:
        Validated HTML text
    """
    if not text:
        return text

    if not skip_links_and_spoilers:
        # First, extract and preserve valid links before processing
        # Pattern to match <a href="...">...</a>
        link_pattern = r'<a\s+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        links_map = {}
        link_counter = 0

        def replace_link(match):
            nonlocal link_counter
            url = match.group(1)
            link_text = match.group(2)
            # Validate the content inside the link (skip links/spoilers to avoid infinite recursion)
            validated_text = _validate_html_content(link_text, skip_links_and_spoilers=True)
            placeholder = f"__TELEGRAM_LINK_PLACEHOLDER_{link_counter}__"
            # Escape URL to prevent XSS
            escaped_url = (
                url.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            links_map[placeholder] = f'<a href="{escaped_url}">{validated_text}</a>'
            link_counter += 1
            return placeholder

        # Replace links with placeholders
        text = re.sub(link_pattern, replace_link, text, flags=re.IGNORECASE | re.DOTALL)

        # Extract and preserve valid spoiler tags
        spoiler_pattern = r'<span\s+class=["\']tg-spoiler["\'][^>]*>(.*?)</span>'
        spoilers_map = {}
        spoiler_counter = 0

        def replace_spoiler(match):
            nonlocal spoiler_counter
            content = match.group(1)
            # Validate the content inside the spoiler (skip links/spoilers to avoid infinite recursion)
            validated_content = _validate_html_content(content, skip_links_and_spoilers=True)
            placeholder = f"__TELEGRAM_SPOILER_PLACEHOLDER_{spoiler_counter}__"
            spoilers_map[placeholder] = f'<span class="tg-spoiler">{validated_content}</span>'
            spoiler_counter += 1
            return placeholder

        # Replace valid spoilers with placeholders
        text = re.sub(spoiler_pattern, replace_spoiler, text, flags=re.IGNORECASE | re.DOTALL)
    else:
        links_map = {}
        spoilers_map = {}

    # Remove all table-related tags (table, tr, td, th, tbody, thead, tfoot, caption, colgroup, col)
    table_tags = [
        "table",
        "tr",
        "td",
        "th",
        "tbody",
        "thead",
        "tfoot",
        "caption",
        "colgroup",
        "col",
    ]
    for tag in table_tags:
        text = re.sub(rf"<{tag}[^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"</{tag}>", "", text, flags=re.IGNORECASE)

    # Convert headings to bold with line breaks
    heading_conversions = {
        r"<h1[^>]*>": "<b>",
        r"</h1>": "</b>\n\n",
        r"<h2[^>]*>": "<b>",
        r"</h2>": "</b>\n\n",
        r"<h3[^>]*>": "<b>",
        r"</h3>": "</b>\n",
        r"<h4[^>]*>": "<b>",
        r"</h4>": "</b>\n",
        r"<h5[^>]*>": "<b>",
        r"</h5>": "</b>\n",
        r"<h6[^>]*>": "<b>",
        r"</h6>": "</b>\n",
    }

    for pattern, replacement in heading_conversions.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Convert supported tags to their canonical forms
    tag_conversions = {
        r"<strong[^>]*>": "<b>",
        r"</strong>": "</b>",
        r"<em[^>]*>": "<i>",
        r"</em>": "</i>",
        r"<ins[^>]*>": "<u>",
        r"</ins>": "</u>",
        r"<strike[^>]*>": "<s>",
        r"</strike>": "</s>",
        r"<del[^>]*>": "<s>",
        r"</del>": "</s>",
    }

    for pattern, replacement in tag_conversions.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Remove div, p, span (without tg-spoiler class) - convert to line breaks
    text = re.sub(r"<div[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)

    # Remove span tags that don't have tg-spoiler class (they were already replaced)
    # This catches any remaining span tags
    text = re.sub(r"<span[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</span>", "", text, flags=re.IGNORECASE)

    # Handle lists - convert to plain text
    text = convert_lists_to_telegram(text)

    # Remove all other unsupported tags but keep content
    # List of unsupported tags to remove
    unsupported_tags = [
        "section",
        "article",
        "nav",
        "header",
        "footer",
        "aside",
        "main",
        "figure",
        "figcaption",
        "details",
        "summary",
        "mark",
        "small",
        "abbr",
        "sub",
        "sup",
        "time",
        "var",
        "kbd",
        "samp",
        "output",
        "progress",
        "meter",
        "canvas",
        "svg",
        "iframe",
        "object",
        "embed",
        "video",
        "audio",
        "source",
        "track",
        "map",
        "area",
        "form",
        "input",
        "button",
        "select",
        "datalist",
        "optgroup",
        "option",
        "textarea",
        "label",
        "fieldset",
        "legend",
        "output",
        "dialog",
    ]

    for tag in unsupported_tags:
        text = re.sub(rf"<{tag}[^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"</{tag}>", "", text, flags=re.IGNORECASE)

    # Remove any remaining HTML tags that are not in the allowed list
    # Allowed tags: b, strong, i, em, u, ins, s, strike, del, a, code, pre, span (with tg-spoiler), blockquote, br
    # We'll be conservative and remove anything that looks like a tag but isn't in our allowed list
    allowed_tags_pattern = (
        r"</?(?:b|strong|i|em|u|ins|s|strike|del|a|code|pre|span|blockquote|br)(?:\s[^>]*)?>"
    )

    # Find all tags
    all_tags = re.findall(r"<[^>]+>", text)
    for tag in all_tags:
        # Check if it's an allowed tag
        if not re.match(allowed_tags_pattern, tag, re.IGNORECASE):
            # Remove the tag but keep content
            text = text.replace(tag, "")

    # Restore placeholders
    for placeholder, original in spoilers_map.items():
        text = text.replace(placeholder, original)

    for placeholder, original in links_map.items():
        text = text.replace(placeholder, original)

    # Clean up multiple consecutive line breaks
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove empty tags
    text = re.sub(r"<b>\s*</b>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<i>\s*</i>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<u>\s*</u>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<s>\s*</s>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<code>\s*</code>", "", text, flags=re.IGNORECASE)

    # Fix nested duplicate tags
    text = re.sub(r"<b><b>", "<b>", text, flags=re.IGNORECASE)
    text = re.sub(r"</b></b>", "</b>", text, flags=re.IGNORECASE)
    text = re.sub(r"<i><i>", "<i>", text, flags=re.IGNORECASE)
    text = re.sub(r"</i></i>", "</i>", text, flags=re.IGNORECASE)

    return text.strip()


def validate_telegram_html(html_text: str) -> str:
    """
    Validate and sanitize HTML for Telegram compatibility.

    Telegram supports only these HTML tags:
    - <b>, <strong> - bold
    - <i>, <em> - italic
    - <u>, <ins> - underline
    - <s>, <strike>, <del> - strikethrough
    - <a href="URL"> - links
    - <code> - inline code
    - <pre> - code block
    - <span class="tg-spoiler"> - spoiler (only with tg-spoiler class!)
    - <blockquote> - blockquote
    - <br> - line break

    All other tags are removed, but their content is preserved.

    Args:
        html_text: HTML text to validate

    Returns:
        str: Validated Telegram-compatible HTML text
    """
    return _validate_html_content(html_text, skip_links_and_spoilers=False)


def convert_html_for_telegram(html_text):
    """
    Convert unsupported HTML tags to Telegram-compatible HTML tags.

    This is a wrapper around validate_telegram_html for backward compatibility.

    Args:
        html_text (str): Original HTML text

    Returns:
        str: Telegram-compatible HTML text
    """
    return validate_telegram_html(html_text)


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
    ul_pattern = r"<ul[^>]*>(.*?)</ul>"
    while re.search(ul_pattern, text, re.IGNORECASE | re.DOTALL):
        text = re.sub(ul_pattern, convert_ul_list, text, flags=re.IGNORECASE | re.DOTALL)

    # Handle ordered lists (ol)
    ol_pattern = r"<ol[^>]*>(.*?)</ol>"
    while re.search(ol_pattern, text, re.IGNORECASE | re.DOTALL):
        text = re.sub(ol_pattern, convert_ol_list, text, flags=re.IGNORECASE | re.DOTALL)

    # Remove any remaining list item tags and convert to simple lines
    text = re.sub(r"<li[^>]*>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)

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
    li_items = re.findall(r"<li[^>]*>(.*?)</li>", list_content, re.IGNORECASE | re.DOTALL)

    converted_list = []
    for item in li_items:
        # Clean up the item content from any remaining HTML tags we don't want
        clean_item = re.sub(r"<[^>]+>", "", item)
        converted_list.append(f"• {clean_item.strip()}")

    return "\n".join(converted_list) + "\n"


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
    li_items = re.findall(r"<li[^>]*>(.*?)</li>", list_content, re.IGNORECASE | re.DOTALL)

    converted_list = []
    for i, item in enumerate(li_items, 1):
        # Clean up the item content from any remaining HTML tags we don't want
        clean_item = re.sub(r"<[^>]+>", "", item)
        converted_list.append(f"{i}. {clean_item.strip()}")

    return "\n".join(converted_list) + "\n"


def escape_html(text: str) -> str:
    """
    Escape special HTML characters in plain text.

    This function is used to escape plain text that will be inserted into HTML,
    preventing XSS attacks. It does NOT validate HTML tags - use validate_telegram_html
    for that purpose.

    Args:
        text: Plain text to escape (should not contain HTML tags)

    Returns:
        str: Escaped text safe for insertion into HTML
    """
    if not text:
        return ""
    # Escape &, <, >, ", '
    html_escape_table = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
    }
    return "".join(html_escape_table.get(c, c) for c in text)


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
    link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"

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
    Safely send a message, falling back to no parse mode if formatting fails.

    Automatically validates HTML tags for Telegram compatibility when parse_mode is "HTML".

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
    # Validate HTML if parse_mode is HTML
    if parse_mode == "HTML" and text:
        text = validate_telegram_html(text)

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
    Safely edit a message, falling back to no parse mode if formatting fails.

    Automatically validates HTML tags for Telegram compatibility when parse_mode is "HTML".

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
    # Validate HTML if parse_mode is HTML
    if parse_mode == "HTML" and text:
        text = validate_telegram_html(text)

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
