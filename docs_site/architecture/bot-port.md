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

The Telegram adapter (`TelegramBotAdapter`) automatically validates HTML content when sending messages with `parse_mode="HTML"`. This ensures:

- Only Telegram-supported HTML tags are used
- Unsupported tags are converted or removed
- Links and spoilers are properly preserved
- XSS vulnerabilities are prevented through URL escaping

The validation is performed transparently before sending messages, ensuring compatibility with Telegram's HTML parsing requirements.

## See also

- [Message DTO Architecture](message-dto.md)
