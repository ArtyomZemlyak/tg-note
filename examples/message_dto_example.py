"""
Example: Using Message DTOs

This example demonstrates how to work with IncomingMessageDTO
and MessageMapper for platform-independent message processing.
"""

from src.bot.dto import IncomingMessageDTO, OutgoingMessageDTO
from src.bot.message_mapper import MessageMapper


def example_1_creating_dto():
    """Example 1: Creating an IncomingMessageDTO manually"""
    print("=== Example 1: Creating DTO ===")

    # Create a DTO (e.g., for testing or from another platform)
    message = IncomingMessageDTO(
        message_id=12345,
        chat_id=67890,
        user_id=11111,
        text="Hello, world!",
        content_type="text",
        timestamp=1234567890,
    )

    print(f"Message ID: {message.message_id}")
    print(f"Chat ID: {message.chat_id}")
    print(f"User ID: {message.user_id}")
    print(f"Text: {message.text}")
    print(f"Is Forwarded: {message.is_forwarded()}")
    print()


def example_2_forwarded_message():
    """Example 2: Working with forwarded messages"""
    print("=== Example 2: Forwarded Message ===")

    # Create a forwarded message DTO
    forwarded = IncomingMessageDTO(
        message_id=12345,
        chat_id=67890,
        user_id=11111,
        text="Check this out!",
        content_type="text",
        timestamp=1234567890,
        forward_date=1234567800,
        forward_sender_name="John Doe",
    )

    print(f"Message: {forwarded.text}")
    print(f"Is Forwarded: {forwarded.is_forwarded()}")
    print(f"Forwarded from: {forwarded.forward_sender_name}")
    print(f"Forward date: {forwarded.forward_date}")
    print()


def example_3_media_message():
    """Example 3: Message with media attachment"""
    print("=== Example 3: Media Message ===")

    # Create a photo message DTO
    photo_msg = IncomingMessageDTO(
        message_id=12345,
        chat_id=67890,
        user_id=11111,
        text="",
        content_type="photo",
        timestamp=1234567890,
        caption="Beautiful sunset!",
        photo=["photo_file_id_here"],
    )

    print(f"Content Type: {photo_msg.content_type}")
    print(f"Caption: {photo_msg.caption}")
    print(f"Has Photo: {photo_msg.photo is not None}")
    print()


def example_4_converting_to_dict():
    """Example 4: Converting DTO to dictionary"""
    print("=== Example 4: DTO to Dictionary ===")

    # Create a DTO
    message = IncomingMessageDTO(
        message_id=12345,
        chat_id=67890,
        user_id=11111,
        text="Test message",
        content_type="text",
        timestamp=1234567890,
    )

    # Convert to dictionary (for legacy code or serialization)
    message_dict = MessageMapper.to_dict(message)

    print("Dictionary representation:")
    for key, value in message_dict.items():
        print(f"  {key}: {value}")
    print()


def example_5_service_usage():
    """Example 5: How services use DTOs"""
    print("=== Example 5: Service Usage Pattern ===")

    # This shows the pattern services follow

    # 1. Receive DTO from handler layer
    incoming_message = IncomingMessageDTO(
        message_id=12345,
        chat_id=67890,
        user_id=11111,
        text="Process this",
        content_type="text",
        timestamp=1234567890,
    )

    # 2. Extract data from DTO
    user_id = incoming_message.user_id
    text = incoming_message.text
    chat_id = incoming_message.chat_id

    print(f"Processing message from user {user_id}")
    print(f"Message text: {text}")

    # 3. For bot operations, use explicit IDs
    processing_msg_id = 99999  # ID of status message

    print(f"\nBot operations use:")
    print(f"  chat_id: {chat_id}")
    print(f"  message_id: {processing_msg_id}")

    # Example bot operation (pseudocode):
    # await bot.edit_message_text(
    #     "Processing complete!",
    #     chat_id=chat_id,
    #     message_id=processing_msg_id
    # )
    print()


def example_6_testing_with_dto():
    """Example 6: Testing with DTOs"""
    print("=== Example 6: Testing Pattern ===")

    # DTOs make testing easy - no need for complex Telegram mocks

    # Create test message
    test_message = IncomingMessageDTO(
        message_id=1, chat_id=1, user_id=1, text="test", content_type="text", timestamp=0
    )

    # Now you can test your service logic with this simple DTO
    print("Testing with DTO:")
    print(f"  Message: {test_message.text}")
    print(f"  Easy to create: ✓")
    print(f"  No Telegram SDK needed: ✓")
    print(f"  Platform independent: ✓")
    print()


def example_7_outgoing_message():
    """Example 7: Outgoing messages (future use)"""
    print("=== Example 7: Outgoing Message DTO ===")

    # Create outgoing message
    outgoing = OutgoingMessageDTO(
        chat_id=67890,
        text="Hello! This is a response.",
        parse_mode="Markdown",
        reply_to_message_id=12345,
    )

    print(f"Sending to chat: {outgoing.chat_id}")
    print(f"Text: {outgoing.text}")
    print(f"Parse mode: {outgoing.parse_mode}")
    print(f"Replying to: {outgoing.reply_to_message_id}")
    print()


if __name__ == "__main__":
    print("Message DTO Examples\n")
    print("=" * 50)
    print()

    example_1_creating_dto()
    example_2_forwarded_message()
    example_3_media_message()
    example_4_converting_to_dict()
    example_5_service_usage()
    example_6_testing_with_dto()
    example_7_outgoing_message()

    print("=" * 50)
    print("\nKey Takeaways:")
    print("1. Use IncomingMessageDTO for all incoming messages")
    print("2. DTOs are platform-independent")
    print("3. Easy to create for testing")
    print("4. Services never import telebot")
    print("5. Bot operations use explicit IDs (chat_id, message_id)")
    print("\nFor more information, see:")
    print("  - docs_site/architecture/message-dto.md")
    print("  - DECOUPLING_SUMMARY.md")
