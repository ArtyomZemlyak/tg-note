# Message DTO Architecture

## Overview

The messaging layer has been decoupled from the Telegram SDK using the Data Transfer Object (DTO) pattern. This architectural decision improves maintainability, testability, and allows for easier migration to different messaging platforms.

## Architecture Components

### 1. IncomingMessageDTO (`src/bot/dto.py`)

The `IncomingMessageDTO` is a platform-independent representation of an incoming message. It contains all the necessary data from a message without depending on Telegram-specific types.

**Key fields:**
- `message_id`: Unique message identifier
- `chat_id`: Chat where message was sent
- `user_id`: User who sent the message
- `text`: Message text content
- `content_type`: Type of content (text, photo, document, etc.)
- `timestamp`: When the message was sent
- Optional fields for forwarded messages and media attachments

**Benefits:**
- Platform-independent: Services don't depend on Telegram SDK
- Testable: Easy to create mock messages for testing
- Serializable: Can be easily converted to/from JSON for storage or queuing

### 2. MessageMapper (`src/bot/message_mapper.py`)

The `MessageMapper` class handles conversion between Telegram messages and DTOs. It isolates the Telegram SDK dependency to the bot layer.

**Key methods:**
- `from_telegram_message(message: Message) -> IncomingMessageDTO`: Converts Telegram message to DTO
- `to_dict(dto: IncomingMessageDTO) -> Dict`: Converts DTO to dictionary (for legacy code)

### 3. Service Interfaces (`src/services/interfaces.py`)

Service interfaces have been updated to use DTOs instead of Telegram types:

**Before:**
```python
from telebot.types import Message

async def process_message(self, message: Message) -> None:
    pass
```

**After:**
```python
from src.bot.dto import IncomingMessageDTO

async def process_message(self, message: IncomingMessageDTO) -> None:
    pass
```

## Data Flow

```
┌─────────────────┐
│ Telegram Bot    │
│ (handlers.py)   │
└────────┬────────┘
         │ Telegram Message
         ▼
┌─────────────────┐
│ MessageMapper   │
│ (mapper)        │
└────────┬────────┘
         │ IncomingMessageDTO
         ▼
┌─────────────────┐
│ MessageProcessor│
│ (service)       │
└────────┬────────┘
         │ MessageGroup
         ▼
┌─────────────────┐
│ Domain Services │
│ (note, ask,     │
│  agent)         │
└─────────────────┘
```

## Changes to Processing Messages

### In Handlers Layer (`src/bot/handlers.py`)

Handlers now convert incoming Telegram messages to DTOs before passing them to services:

```python
async def handle_message(self, message: Message) -> None:
    # Convert Telegram message to DTO
    message_dto = MessageMapper.from_telegram_message(message)
    
    # Pass DTO to service
    await self.message_processor.process_message(message_dto)
```

### In Service Layer

Services now work with DTOs and only need message IDs and chat IDs for bot operations:

**Before:**
```python
async def create_note(
    self,
    group: MessageGroup,
    processing_msg: Message,  # Telegram type!
    user_id: int,
    user_kb: dict
) -> None:
    await self.bot.edit_message_text(
        "Processing...",
        chat_id=processing_msg.chat.id,
        message_id=processing_msg.message_id
    )
```

**After:**
```python
async def create_note(
    self,
    group: MessageGroup,
    processing_msg_id: int,  # Just the ID
    chat_id: int,            # Just the ID
    user_id: int,
    user_kb: dict
) -> None:
    await self.bot.edit_message_text(
        "Processing...",
        chat_id=chat_id,
        message_id=processing_msg_id
    )
```

## Benefits

### 1. Platform Independence
Services are no longer tied to Telegram. Switching to a different messaging platform (Discord, Slack, etc.) only requires:
- Implementing a new adapter for that platform
- Creating a mapper from that platform's message type to `IncomingMessageDTO`
- No changes to service layer

### 2. Testability
Creating test messages is now trivial:

```python
# Before (Telegram-specific)
from telebot.types import Message, User, Chat
message = Message(...)  # Complex Telegram object creation

# After (simple DTO)
from src.bot.dto import IncomingMessageDTO
message_dto = IncomingMessageDTO(
    message_id=1,
    chat_id=123,
    user_id=456,
    text="Test message",
    content_type="text",
    timestamp=1234567890
)
```

### 3. Clear Boundaries
The architecture now has clear boundaries:
- **Bot Layer** (`src/bot/`): Handles Telegram-specific logic, imports `telebot`
- **Service Layer** (`src/services/`): Platform-independent business logic, NO `telebot` imports
- **Domain Layer**: Pure business logic

### 4. Easier Evolution
Changes to the Telegram SDK or bot framework don't ripple through the entire codebase. The impact is isolated to:
- `TelegramBotAdapter`
- `MessageMapper`
- `BotHandlers`

## Migration Guide

### For New Services

When creating new services that process messages:

1. **Accept DTOs in interface:**
   ```python
   from src.bot.dto import IncomingMessageDTO
   
   async def process(self, message: IncomingMessageDTO) -> None:
       pass
   ```

2. **Use message data from DTO:**
   ```python
   user_id = message.user_id
   text = message.text
   chat_id = message.chat_id
   ```

3. **Pass IDs for bot operations:**
   ```python
   async def my_service_method(
       self,
       message_id: int,
       chat_id: int,
       ...
   ) -> None:
       await self.bot.edit_message_text(
           "Done!",
           chat_id=chat_id,
           message_id=message_id
       )
   ```

### For Existing Code

If you encounter code that still uses `telebot.types.Message`:

1. **Check the layer:**
   - If in `src/bot/`: OK to use Telegram types
   - If in `src/services/`: Should use DTOs

2. **Convert to DTO pattern:**
   - Replace `Message` parameters with `IncomingMessageDTO`
   - Replace `processing_msg: Message` with `processing_msg_id: int, chat_id: int`
   - Update all references to use the new parameters

## Best Practices

1. **Never import `telebot` in services:** Services should be platform-independent
2. **Use DTOs for message data:** Always convert at the boundary (handlers)
3. **Pass only IDs for operations:** Services only need IDs to interact with the bot
4. **Keep mapper simple:** Complex transformations belong in services, not the mapper
5. **Document DTO changes:** If you add fields to `IncomingMessageDTO`, update this documentation

## Future Enhancements

Potential improvements to the DTO architecture:

1. **Typed Media DTOs:** Create specific DTOs for different media types (PhotoDTO, DocumentDTO, etc.)
2. **Event-based Processing:** Use DTOs as events in an event-driven architecture
3. **Message Serialization:** Add methods to serialize/deserialize DTOs for message queues
4. **Validation:** Add validation logic to DTOs to ensure data integrity
5. **Immutability:** Consider making DTOs immutable (frozen dataclasses) for better safety

## Related Documentation

- [Architecture Overview](overview.md)
- [Data Flow](data-flow.md)
- [Bot Port Interface](bot-port.md)
