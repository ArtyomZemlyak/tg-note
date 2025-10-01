"""
Tests for async handler functionality
Verifies that handlers work correctly with async/await
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telebot.types import Message, User, Chat

from src.bot.handlers import BotHandlers
from src.tracker.processing_tracker import ProcessingTracker
from src.knowledge_base.manager import KnowledgeBaseManager


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
        mock.is_processed = Mock(return_value=False)
        mock.add_processed = Mock()
        return mock
    
    @pytest.fixture
    def mock_kb_manager(self):
        """Create mock KB manager"""
        return Mock(spec=KnowledgeBaseManager)
    
    @pytest.fixture
    def handlers(self, mock_bot, mock_tracker, mock_kb_manager):
        """Create handlers instance"""
        return BotHandlers(mock_bot, mock_tracker, mock_kb_manager)
    
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
        # Mock stats
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
    async def test_process_message_async(self, handlers, test_message, mock_bot):
        """Test that message processing works with async"""
        # Mock the reply_to to return a processing message
        processing_msg = Mock(spec=Message)
        processing_msg.chat = test_message.chat
        processing_msg.message_id = 999
        mock_bot.reply_to.return_value = processing_msg
        
        await handlers._process_message(test_message)
        
        # Verify that bot methods were called
        assert mock_bot.reply_to.called
        assert mock_bot.edit_message_text.called
    
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
    
    @pytest.mark.asyncio
    async def test_message_aggregator_integration(self, handlers, test_message, mock_bot):
        """Test that message aggregator works with async handlers"""
        # Mock bot methods
        processing_msg = Mock(spec=Message)
        processing_msg.chat = test_message.chat
        processing_msg.message_id = 999
        mock_bot.reply_to.return_value = processing_msg
        
        # Start background tasks
        handlers.start_background_tasks()
        
        try:
            # Process a message
            await handlers._process_message(test_message)
            
            # Wait a bit for async operations
            await asyncio.sleep(0.1)
            
            # Verify bot was called
            assert mock_bot.reply_to.called
            
        finally:
            # Clean up
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
