"""
Test for handlers forwarded message exclusion during settings input
Verifies that forwarded, photo, and document messages are ignored when user is waiting for settings input
"""

import pytest
from unittest.mock import Mock, AsyncMock
from telebot.types import Message, User, Chat

from src.bot.handlers import BotHandlers
from src.bot.settings_handlers import SettingsHandlers


class TestHandlersForwardedMessageFix:
    """Test that handlers correctly ignore non-text messages during settings input"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock async bot"""
        mock = Mock()
        mock.reply_to = AsyncMock()
        mock.send_message = AsyncMock()
        mock.edit_message_text = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_tracker(self):
        """Create mock tracker"""
        return Mock()
    
    @pytest.fixture
    def mock_repo_manager(self):
        """Create mock repo manager"""
        return Mock()
    
    @pytest.fixture
    def mock_user_settings(self):
        """Create mock user settings"""
        return Mock()
    
    @pytest.fixture
    def settings_handlers(self, mock_bot):
        """Create settings handlers instance"""
        return SettingsHandlers(mock_bot, handlers=None)
    
    @pytest.fixture
    def handlers(self, mock_bot, mock_tracker, mock_repo_manager, mock_user_settings, settings_handlers):
        """Create handlers instance with settings_handlers"""
        h = BotHandlers(mock_bot, mock_tracker, mock_repo_manager, mock_user_settings, None)
        h.settings_handlers = settings_handlers
        return h
    
    @pytest.fixture
    def test_message(self):
        """Create a test message"""
        message = Mock(spec=Message)
        message.message_id = 1
        message.chat = Mock(spec=Chat)
        message.chat.id = 123
        message.from_user = Mock(spec=User)
        message.from_user.id = 456
        message.text = "test"
        message.caption = None
        message.content_type = 'text'
        # Not forwarded by default
        message.forward_from = None
        message.forward_from_chat = None
        message.forward_from_message_id = None
        message.forward_sender_name = None
        message.forward_date = None
        message.photo = None
        message.document = None
        return message
    
    def test_is_forwarded_message_detection(self, handlers, test_message):
        """Test forwarded message detection"""
        assert not handlers._is_forwarded_message(test_message)
        
        test_message.forward_from = Mock()
        assert handlers._is_forwarded_message(test_message)
    
    @pytest.mark.asyncio
    async def test_forwarded_message_ignored_during_settings_input(self, handlers, test_message, mock_bot):
        """Test that forwarded messages are ignored when user is waiting for settings input"""
        # Set user as waiting for settings input
        handlers.settings_handlers.waiting_for_input[456] = ("KB_PATH", "knowledge_base")
        
        # Make message forwarded
        test_message.forward_from = Mock()
        
        # Call handler
        await handlers.handle_forwarded_message(test_message)
        
        # Verify that reply was sent explaining the message is ignored
        mock_bot.reply_to.assert_called_once()
        call_args = mock_bot.reply_to.call_args[0]
        assert call_args[0] == test_message
        assert "настроек" in call_args[1].lower()
        assert "игнорируются" in call_args[1].lower()
    
    @pytest.mark.asyncio
    async def test_forwarded_message_processed_when_not_waiting(self, handlers, test_message, mock_bot):
        """Test that forwarded messages are processed normally when not waiting for input"""
        # Make sure user is NOT waiting for input
        assert 456 not in handlers.settings_handlers.waiting_for_input
        
        # Make message forwarded
        test_message.forward_from = Mock()
        
        # Mock reply_to to return processing message
        processing_msg = Mock(spec=Message)
        processing_msg.chat = test_message.chat
        processing_msg.message_id = 999
        mock_bot.reply_to.return_value = processing_msg
        
        # Call handler
        await handlers.handle_forwarded_message(test_message)
        
        # Verify that processing started (reply_to called for "Processing..." message)
        assert mock_bot.reply_to.called
        # First call should be the processing notification
        first_call_args = mock_bot.reply_to.call_args_list[0][0]
        assert "Обрабатываю" in first_call_args[1]
    
    @pytest.mark.asyncio
    async def test_photo_message_ignored_during_settings_input(self, handlers, test_message, mock_bot):
        """Test that photo messages are ignored when user is waiting for settings input"""
        # Set user as waiting for settings input
        handlers.settings_handlers.waiting_for_input[456] = ("KB_PATH", "knowledge_base")
        
        # Make message a photo
        test_message.content_type = 'photo'
        test_message.photo = [Mock()]
        
        # Call handler
        await handlers.handle_photo_message(test_message)
        
        # Verify that reply was sent explaining the message is ignored
        mock_bot.reply_to.assert_called_once()
        call_args = mock_bot.reply_to.call_args[0]
        assert call_args[0] == test_message
        assert "настроек" in call_args[1].lower()
    
    @pytest.mark.asyncio
    async def test_document_message_ignored_during_settings_input(self, handlers, test_message, mock_bot):
        """Test that document messages are ignored when user is waiting for settings input"""
        # Set user as waiting for settings input
        handlers.settings_handlers.waiting_for_input[456] = ("KB_PATH", "knowledge_base")
        
        # Make message a document
        test_message.content_type = 'document'
        test_message.document = Mock()
        
        # Call handler
        await handlers.handle_document_message(test_message)
        
        # Verify that reply was sent explaining the message is ignored
        mock_bot.reply_to.assert_called_once()
        call_args = mock_bot.reply_to.call_args[0]
        assert call_args[0] == test_message
        assert "настроек" in call_args[1].lower()
    
    @pytest.mark.asyncio
    async def test_text_message_ignored_during_settings_input(self, handlers, test_message, mock_bot):
        """Test that text messages are skipped (not processed) when user is waiting for settings input"""
        # Set user as waiting for settings input
        handlers.settings_handlers.waiting_for_input[456] = ("KB_PATH", "knowledge_base")
        
        # Call handler
        await handlers.handle_text_message(test_message)
        
        # Verify that no processing happened (no reply_to for processing message)
        # The text should be handled by settings_handlers instead
        assert not mock_bot.reply_to.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
