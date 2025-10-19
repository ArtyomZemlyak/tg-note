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

## See also

- [Message DTO Architecture](message-dto.md)
