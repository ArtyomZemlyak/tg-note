# Bot Port Interface

The Bot Port defines a stable interface between the bot layer and services, enabling platform-agnostic business logic.

## Purpose

- Decouple Telegram-specific APIs from services
- Allow replacing the transport (Telegram/Discord/Slack) without changing services

## Interface Responsibilities

- Accept DTO-based inputs (message IDs, chat IDs, user IDs)
- Expose minimal methods required by services
- Avoid SDK-specific types in method signatures

## Example Responsibilities

- Edit message text by `chat_id` and `message_id`
- Send messages and documents
- Answer callback queries
- Automatic HTML validation for Telegram compatibility

## HTML Validation

The Telegram adapter (`TelegramBotAdapter`) automatically validates and corrects HTML content when sending messages with `parse_mode="HTML"`. This ensures robust handling of various HTML formatting issues.

### Features

The HTML validator (`validate_telegram_html` in `src/bot/utils.py`) provides:

1. **HTML Entity Decoding**
   - Automatically decodes HTML entities like `&lt;b&gt;` to `<b>`
   - Ensures escaped HTML is properly rendered

2. **Automatic Tag Correction**
   - Closes unclosed tags (e.g., `<b>text` → `<b>text</b>`)
   - Fixes improperly nested tags (e.g., `<b>text <i>more</b> end</i>` → `<b>text <i>more</i></b> end`)
   - Removes empty tags (e.g., `<b></b>` is removed)

3. **Tag Conversion**
   - Converts unsupported tags to Telegram-compatible equivalents:
     - `<strong>` → `<b>`
     - `<em>` → `<i>`
     - `<ins>` → `<u>`
     - `<strike>`, `<del>` → `<s>`
   - Converts lists (`<ul>`, `<ol>`, `<li>`) to plain text with bullets

4. **Security**
   - Prevents XSS vulnerabilities through URL escaping in links
   - Only allows Telegram-supported tags

### Supported Tags

Telegram supports only these HTML tags:
- `<b>`, `<strong>` - bold
- `<i>`, `<em>` - italic
- `<u>`, `<ins>` - underline
- `<s>`, `<strike>`, `<del>` - strikethrough
- `<a href="URL">` - links
- `<code>` - inline code
- `<pre>` - code block
- `<span class="tg-spoiler">` - spoiler (only with tg-spoiler class!)
- `<blockquote>` - blockquote

Use the newline character (`\n`) for line breaks.

All other tags are removed, but their content is preserved.

### Processing Pipeline

The validation is performed transparently in this order:

1. Decode HTML entities (e.g., `&lt;b&gt;` → `<b>`)
2. Fix HTML structure (close unclosed tags, fix nesting)
3. Convert lists to plain text with bullets
4. Convert unsupported tags to Telegram equivalents
5. Remove remaining unsupported tags (keep content)
6. Clean up empty and duplicate tags

This multi-stage approach ensures maximum compatibility with Telegram's HTML parser while preserving the original content and intent.

## See also

- [Message DTO Architecture](message-dto.md)
