# Message DTO Quick Reference

## Quick Start

### Creating a DTO (for testing)

```python
from src.bot.dto import IncomingMessageDTO

message = IncomingMessageDTO(
    message_id=123,
    chat_id=456,
    user_id=789,
    text="Hello",
    content_type="text",
    timestamp=1234567890
)
```

### Converting Telegram Message to DTO (in handlers)

```python
from src.bot.message_mapper import MessageMapper
from telebot.types import Message

# Telegram message received
telegram_msg: Message = ...

# Convert to DTO
message_dto = MessageMapper.from_telegram_message(telegram_msg)

# Pass to services
await service.process_message(message_dto)
```

### Writing a Service Method

**❌ OLD WAY (Don't do this):**

```python
from telebot.types import Message

async def my_service_method(
    self,
    message: Message,  # ❌ Telegram dependency!
    processing_msg: Message  # ❌ Telegram dependency!
) -> None:
    await self.bot.edit_message_text(
        "Done",
        chat_id=processing_msg.chat.id,
        message_id=processing_msg.message_id
    )
```

**✅ NEW WAY (Do this):**

```python
from src.bot.dto import IncomingMessageDTO

async def my_service_method(
    self,
    message: IncomingMessageDTO,  # ✅ Platform independent!
    processing_msg_id: int,       # ✅ Just the ID
    chat_id: int                  # ✅ Just the ID
) -> None:
    await self.bot.edit_message_text(
        "Done",
        chat_id=chat_id,
        message_id=processing_msg_id
    )
```

## Common Patterns

### Pattern 1: Handler → Service

```python
# In handlers.py
async def handle_message(self, message: Message) -> None:
    # Convert to DTO
    message_dto = MessageMapper.from_telegram_message(message)

    # Pass to service
    await self.message_processor.process_message(message_dto)
```

### Pattern 2: Service → Service

```python
# Service A calls Service B
async def service_a_method(
    self,
    group: MessageGroup,
    processing_msg_id: int,
    chat_id: int,
    user_id: int
) -> None:
    # Call another service with same signature
    await self.service_b.process(
        group,
        processing_msg_id,
        chat_id,
        user_id
    )
```

### Pattern 3: Bot Operations

```python
# All bot operations use explicit IDs
await self.bot.send_message(
    chat_id=chat_id,
    text="Hello"
)

await self.bot.edit_message_text(
    "Updated!",
    chat_id=chat_id,
    message_id=processing_msg_id
)

await self.bot.reply_to(
    message_id=original_msg_id,
    text="Reply"
)
```

## DTO Fields Reference

### Core Fields (Required)

- `message_id: int` - Unique message identifier
- `chat_id: int` - Chat identifier
- `user_id: int` - User identifier
- `text: str` - Message text (empty string if none)
- `content_type: str` - Type: "text", "photo", "document", etc.
- `timestamp: int` - Unix timestamp

### Optional Fields

- `caption: str` - Media caption
- `forward_from: Any` - Forwarded from user
- `forward_from_chat: Any` - Forwarded from chat
- `forward_from_message_id: int` - Original message ID
- `forward_sender_name: str` - Sender name (hidden accounts)
- `forward_date: int` - Forward timestamp

### Media Fields (Optional)

- `photo: Any` - Photo data
- `document: Any` - Document data
- `video: Any` - Video data
- `audio: Any` - Audio data
- `voice: Any` - Voice message data
- `video_note: Any` - Video note data
- `animation: Any` - Animation/GIF data
- `sticker: Any` - Sticker data

### Methods

- `is_forwarded() -> bool` - Check if message is forwarded

## Testing Examples

### Test with Mock DTO

```python
def test_my_service():
    # Create mock message
    message = IncomingMessageDTO(
        message_id=1,
        chat_id=1,
        user_id=1,
        text="test message",
        content_type="text",
        timestamp=0
    )

    # Test your service
    result = await my_service.process(message, 999, 1)

    # Assert results
    assert result == expected
```

### Test Forwarded Message

```python
def test_forwarded_message():
    forwarded = IncomingMessageDTO(
        message_id=1,
        chat_id=1,
        user_id=1,
        text="forwarded",
        content_type="text",
        timestamp=0,
        forward_date=123,
        forward_sender_name="John"
    )

    assert forwarded.is_forwarded() is True
```

## Checklist for New Services

- [ ] Accept `IncomingMessageDTO` instead of `Message`
- [ ] Use `processing_msg_id: int, chat_id: int` instead of `processing_msg: Message`
- [ ] Don't import from `telebot` in service files
- [ ] Use `message.user_id`, `message.text`, etc. from DTO
- [ ] Pass explicit IDs to bot operations
- [ ] Write tests using mock DTOs

## Migration Checklist

When updating existing service:

1. [ ] Remove `from telebot.types import Message`
2. [ ] Add `from src.bot.dto import IncomingMessageDTO`
3. [ ] Replace `message: Message` with `message: IncomingMessageDTO`
4. [ ] Replace `processing_msg: Message` with `processing_msg_id: int, chat_id: int`
5. [ ] Update method calls: `message.chat.id` → `chat_id`
6. [ ] Update method calls: `message.message_id` → `message_id`
7. [ ] Update interface definition
8. [ ] Update all method calls to this service
9. [ ] Run tests

## Common Mistakes

### ❌ Mistake 1: Importing telebot in services

```python
from telebot.types import Message  # ❌ NO!
```

### ❌ Mistake 2: Passing Message object

```python
await service.process(message, processing_msg)  # ❌ NO!
```

### ❌ Mistake 3: Not converting in handlers

```python
await self.service.process_message(message)  # ❌ NO! (if message is Telegram Message)
```

### ✅ Correct Usage

```python
# In services - use DTO
from src.bot.dto import IncomingMessageDTO

# In handlers - convert first
message_dto = MessageMapper.from_telegram_message(message)
await self.service.process_message(message_dto)
```

## Related Files

- **Implementation**: `src/bot/dto.py`, `src/bot/message_mapper.py`
- **Interfaces**: `src/services/interfaces.py`
- **Tests**: `tests/test_message_dto.py`
- **Example**: `examples/message_dto_example.py`
- **Documentation**: `docs_site/architecture/message-dto.md`
- **Summary**: `DECOUPLING_SUMMARY.md`

## Getting Help

If you're unsure about how to use DTOs:

1. Check `examples/message_dto_example.py` for patterns
2. Look at existing services: `note_creation_service.py`, `question_answering_service.py`
3. Read the full documentation: `docs_site/architecture/message-dto.md`
4. Review the summary: `DECOUPLING_SUMMARY.md`
