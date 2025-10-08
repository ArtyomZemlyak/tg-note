"""
Tests for Message DTO and Mapper
"""

import pytest
from unittest.mock import Mock
from src.bot.dto import IncomingMessageDTO
from src.bot.message_mapper import MessageMapper


class TestIncomingMessageDTO:
    """Test IncomingMessageDTO functionality"""
    
    def test_create_basic_dto(self):
        """Test creating a basic DTO"""
        dto = IncomingMessageDTO(
            message_id=123,
            chat_id=456,
            user_id=789,
            text="Hello, world!",
            content_type="text",
            timestamp=1234567890
        )
        
        assert dto.message_id == 123
        assert dto.chat_id == 456
        assert dto.user_id == 789
        assert dto.text == "Hello, world!"
        assert dto.content_type == "text"
        assert dto.timestamp == 1234567890
    
    def test_is_forwarded_with_forward_date(self):
        """Test is_forwarded with forward_date set"""
        dto = IncomingMessageDTO(
            message_id=123,
            chat_id=456,
            user_id=789,
            text="",
            content_type="text",
            timestamp=1234567890,
            forward_date=1234567800
        )
        
        assert dto.is_forwarded() is True
    
    def test_is_forwarded_with_forward_from(self):
        """Test is_forwarded with forward_from set"""
        forward_from = Mock()
        dto = IncomingMessageDTO(
            message_id=123,
            chat_id=456,
            user_id=789,
            text="",
            content_type="text",
            timestamp=1234567890,
            forward_from=forward_from
        )
        
        assert dto.is_forwarded() is True
    
    def test_is_forwarded_with_forward_sender_name(self):
        """Test is_forwarded with forward_sender_name set"""
        dto = IncomingMessageDTO(
            message_id=123,
            chat_id=456,
            user_id=789,
            text="",
            content_type="text",
            timestamp=1234567890,
            forward_sender_name="John Doe"
        )
        
        assert dto.is_forwarded() is True
    
    def test_is_not_forwarded(self):
        """Test is_forwarded returns False for regular messages"""
        dto = IncomingMessageDTO(
            message_id=123,
            chat_id=456,
            user_id=789,
            text="",
            content_type="text",
            timestamp=1234567890
        )
        
        assert dto.is_forwarded() is False


class TestMessageMapper:
    """Test MessageMapper functionality"""
    
    def test_from_telegram_message_basic(self):
        """Test mapping basic Telegram message to DTO"""
        # Create mock Telegram message
        telegram_msg = Mock()
        telegram_msg.message_id = 123
        telegram_msg.chat.id = 456
        telegram_msg.from_user.id = 789
        telegram_msg.text = "Hello"
        telegram_msg.caption = None
        telegram_msg.content_type = "text"
        telegram_msg.date = 1234567890
        telegram_msg.forward_from = None
        telegram_msg.forward_from_chat = None
        telegram_msg.forward_from_message_id = None
        telegram_msg.forward_sender_name = None
        telegram_msg.forward_date = None
        
        # Map to DTO
        dto = MessageMapper.from_telegram_message(telegram_msg)
        
        # Verify mapping
        assert dto.message_id == 123
        assert dto.chat_id == 456
        assert dto.user_id == 789
        assert dto.text == "Hello"
        assert dto.content_type == "text"
        assert dto.timestamp == 1234567890
        assert dto.caption == ""
    
    def test_from_telegram_message_with_caption(self):
        """Test mapping message with caption"""
        telegram_msg = Mock()
        telegram_msg.message_id = 123
        telegram_msg.chat.id = 456
        telegram_msg.from_user.id = 789
        telegram_msg.text = None
        telegram_msg.caption = "Photo caption"
        telegram_msg.content_type = "photo"
        telegram_msg.date = 1234567890
        telegram_msg.forward_from = None
        telegram_msg.forward_from_chat = None
        telegram_msg.forward_from_message_id = None
        telegram_msg.forward_sender_name = None
        telegram_msg.forward_date = None
        telegram_msg.photo = ["photo_data"]
        
        dto = MessageMapper.from_telegram_message(telegram_msg)
        
        assert dto.text == ""
        assert dto.caption == "Photo caption"
        assert dto.content_type == "photo"
        assert dto.photo == ["photo_data"]
    
    def test_from_telegram_message_forwarded(self):
        """Test mapping forwarded message"""
        forward_from = Mock()
        telegram_msg = Mock()
        telegram_msg.message_id = 123
        telegram_msg.chat.id = 456
        telegram_msg.from_user.id = 789
        telegram_msg.text = "Forwarded"
        telegram_msg.caption = None
        telegram_msg.content_type = "text"
        telegram_msg.date = 1234567890
        telegram_msg.forward_from = forward_from
        telegram_msg.forward_from_chat = None
        telegram_msg.forward_from_message_id = 999
        telegram_msg.forward_sender_name = None
        telegram_msg.forward_date = 1234567800
        
        dto = MessageMapper.from_telegram_message(telegram_msg)
        
        assert dto.forward_from == forward_from
        assert dto.forward_from_message_id == 999
        assert dto.forward_date == 1234567800
        assert dto.is_forwarded() is True
    
    def test_to_dict_basic(self):
        """Test converting DTO to dictionary"""
        dto = IncomingMessageDTO(
            message_id=123,
            chat_id=456,
            user_id=789,
            text="Hello",
            content_type="text",
            timestamp=1234567890,
            caption="Caption"
        )
        
        result = MessageMapper.to_dict(dto)
        
        assert result['message_id'] == 123
        assert result['chat_id'] == 456
        assert result['user_id'] == 789
        assert result['text'] == "Hello"
        assert result['content_type'] == "text"
        assert result['date'] == 1234567890
        assert result['caption'] == "Caption"
    
    def test_to_dict_with_media(self):
        """Test converting DTO with media to dictionary"""
        dto = IncomingMessageDTO(
            message_id=123,
            chat_id=456,
            user_id=789,
            text="",
            content_type="photo",
            timestamp=1234567890,
            photo=["photo_data"],
            document=None,
            video=None
        )
        
        result = MessageMapper.to_dict(dto)
        
        assert 'photo' in result
        assert result['photo'] == ["photo_data"]
        assert 'document' not in result
        assert 'video' not in result
    
    def test_to_dict_forwarded(self):
        """Test converting forwarded DTO to dictionary"""
        forward_from = Mock()
        dto = IncomingMessageDTO(
            message_id=123,
            chat_id=456,
            user_id=789,
            text="Forwarded",
            content_type="text",
            timestamp=1234567890,
            forward_from=forward_from,
            forward_date=1234567800
        )
        
        result = MessageMapper.to_dict(dto)
        
        assert result['forward_from'] == forward_from
        assert result['forward_date'] == 1234567800


class TestMessageDTOIntegration:
    """Integration tests for DTO and Mapper"""
    
    def test_round_trip_conversion(self):
        """Test converting Telegram message to DTO and back to dict"""
        # Create mock Telegram message
        telegram_msg = Mock()
        telegram_msg.message_id = 123
        telegram_msg.chat.id = 456
        telegram_msg.from_user.id = 789
        telegram_msg.text = "Test message"
        telegram_msg.caption = None
        telegram_msg.content_type = "text"
        telegram_msg.date = 1234567890
        telegram_msg.forward_from = None
        telegram_msg.forward_from_chat = None
        telegram_msg.forward_from_message_id = None
        telegram_msg.forward_sender_name = None
        telegram_msg.forward_date = None
        
        # Convert to DTO
        dto = MessageMapper.from_telegram_message(telegram_msg)
        
        # Convert to dict
        result = MessageMapper.to_dict(dto)
        
        # Verify all fields preserved
        assert result['message_id'] == 123
        assert result['chat_id'] == 456
        assert result['user_id'] == 789
        assert result['text'] == "Test message"
        assert result['content_type'] == "text"
        assert result['date'] == 1234567890
