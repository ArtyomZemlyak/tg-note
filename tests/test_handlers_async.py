"""
Tests for async handler functionality (refactored)
Verifies that handlers delegate to services and respond via bot
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from telebot.types import Message, User, Chat

from src.bot.handlers import BotHandlers
from src.tracker.processing_tracker import ProcessingTracker


class TestHandlersAsync:
    """Test that handlers work correctly with async/await"""
    
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
        mock = Mock(spec=ProcessingTracker)
        mock.get_stats = Mock(return_value={
            'total_processed': 0,
            'pending_groups': 0,
            'last_processed': 'Never',
        })
        return mock
    
    @pytest.fixture
    def mock_repo_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_user_settings(self):
        return Mock()
    
    @pytest.fixture
    def mock_settings_manager(self):
        m = Mock()
        m.get_setting = Mock(return_value=False)
        return m
    
    @pytest.fixture
    def mock_user_context(self):
        m = Mock()
        m.get_user_mode = Mock(return_value="note")
        m.set_user_mode = Mock()
        m.invalidate_cache = Mock()
        m.cleanup = Mock()
        return m
    
    @pytest.fixture
    def mock_message_processor(self):
        m = Mock()
        m.process_message = AsyncMock()
        m.process_message_group = AsyncMock()
        return m
    
    @pytest.fixture
    def handlers(
        self,
        mock_bot,
        mock_tracker,
        mock_repo_manager,
        mock_user_settings,
        mock_settings_manager,
        mock_user_context,
        mock_message_processor,
    ):
        """Create handlers instance"""
        return BotHandlers(
            bot=mock_bot,
            tracker=mock_tracker,
            repo_manager=mock_repo_manager,
            user_settings=mock_user_settings,
            settings_manager=mock_settings_manager,
            user_context_manager=mock_user_context,
            message_processor=mock_message_processor,
        )
    
    @pytest.fixture
    def test_message(self):
        """Create a test message"""
        message = Mock(spec=Message)
        message.message_id = 1
        message.text = "Test message"
        message.caption = None
        message.content_type = 'text'
        message.chat = Mock(spec=Chat)
        message.chat.id = 12345
        message.from_user = Mock(spec=User)
        message.from_user.id = 67890
        message.forward_from = None
        message.forward_from_chat = None
        message.forward_from_message_id = None
        message.forward_sender_name = None
        message.forward_date = None
        message.date = 1234567890
        message.photo = None
        message.document = None
        return message
    
    @pytest.mark.asyncio
    async def test_handle_start_async(self, handlers, test_message, mock_bot):
        """Test that /start command works with async"""
        await handlers.handle_start(test_message)
        
        # Verify reply_to was called
        mock_bot.reply_to.assert_called_once()
        call_args = mock_bot.reply_to.call_args
        assert call_args[0][0] == test_message
        assert "Добро пожаловать" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_handle_help_async(self, handlers, test_message, mock_bot):
        """Test that /help command works with async"""
        await handlers.handle_help(test_message)
        
        # Verify reply_to was called
        mock_bot.reply_to.assert_called_once()
        call_args = mock_bot.reply_to.call_args
        assert call_args[0][0] == test_message
        assert "Справка" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_handle_status_async(self, handlers, test_message, mock_bot, mock_tracker):
        """Test that /status command works with async"""
        mock_tracker.get_stats.return_value = {
            'total_processed': 10,
            'pending_groups': 2,
            'last_processed': 'Never'
        }
        
        await handlers.handle_status(test_message)
        
        # Verify reply_to was called
        mock_bot.reply_to.assert_called_once()
        call_args = mock_bot.reply_to.call_args
        assert call_args[0][0] == test_message
        assert "Статистика" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_handle_text_message_calls_processor(self, handlers, test_message):
        """Test that text messages are delegated to message processor"""
        # Act
        await handlers.handle_text_message(test_message)
        # Assert processor was called
        handlers.message_processor.process_message.assert_awaited_once_with(test_message)
    
    @pytest.mark.asyncio
    async def test_handle_timeout_async(self, handlers, mock_bot):
        """Test that timeout handling works with async"""
        from src.processor.message_aggregator import MessageGroup
        
        # Create a test group
        group = MessageGroup(timeout=30)
        group.add_message({
            'message_id': 1,
            'chat_id': 12345,
            'user_id': 67890,
            'text': 'Test',
            'content_type': 'text'
        })
        
        # Mock send_message
        processing_msg = Mock(spec=Message)
        processing_msg.chat = Mock()
        processing_msg.chat.id = 12345
        processing_msg.message_id = 999
        mock_bot.send_message.return_value = processing_msg
        
        # Call timeout handler
        await handlers._handle_timeout(12345, group)
        
        # Verify send_message was called
        assert mock_bot.send_message.called
        handlers.message_processor.process_message_group.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_start_stop_background_tasks(self, handlers):
        """Start/stop background tasks should not raise"""
        handlers.start_background_tasks()
        handlers.stop_background_tasks()
    
    def test_is_forwarded_message(self, handlers, test_message):
        """Test forwarded message detection"""
        # Not forwarded
        assert not handlers._is_forwarded_message(test_message)
        
        # Forwarded from user
        test_message.forward_from = Mock()
        assert handlers._is_forwarded_message(test_message)
        
        # Reset and test forwarded from chat
        test_message.forward_from = None
        test_message.forward_from_chat = Mock()
        assert handlers._is_forwarded_message(test_message)
    
    @pytest.mark.asyncio
    async def test_handle_note_mode_sets_mode(self, handlers, test_message, mock_bot):
        """Test that /note command switches to note mode and replies"""
        await handlers.handle_note_mode(test_message)
        handlers.user_context_manager.set_user_mode.assert_called_once_with(test_message.from_user.id, "note")
        mock_bot.reply_to.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_ask_mode_no_kb(self, handlers, test_message, mock_bot):
        """Test that /ask command requires KB to be configured"""
        await handlers.handle_ask_mode(test_message)
        
        # Should show error when no KB configured
        mock_bot.reply_to.assert_called_once()
        call_args = mock_bot.reply_to.call_args
        assert call_args[0][0] == test_message
        assert "База знаний не настроена" in call_args[0][1]
    
    # No direct mode getter/setter on handlers in refactored version; covered via user_context_manager


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
