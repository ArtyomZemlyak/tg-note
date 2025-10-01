"""
Tests for handler threading safety with asyncio
Verifies that handlers can safely call async code from synchronous polling thread
"""

import asyncio
import threading
import time
import unittest
from unittest.mock import Mock, MagicMock, patch
from telebot.types import Message, User, Chat

from src.bot.handlers import BotHandlers
from src.tracker.processing_tracker import ProcessingTracker
from src.knowledge_base.manager import KnowledgeBaseManager


class TestHandlersThreadingSafety(unittest.TestCase):
    """Test that handlers work safely across threads"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock bot
        self.mock_bot = Mock()
        self.mock_bot.reply_to = Mock()
        self.mock_bot.send_message = Mock()
        self.mock_bot.edit_message_text = Mock()
        
        # Mock tracker
        self.mock_tracker = Mock(spec=ProcessingTracker)
        self.mock_tracker.is_processed = Mock(return_value=False)
        self.mock_tracker.add_processed = Mock()
        
        # Mock KB manager
        self.mock_kb_manager = Mock(spec=KnowledgeBaseManager)
        
        # Create handlers
        self.handlers = BotHandlers(
            self.mock_bot,
            self.mock_tracker,
            self.mock_kb_manager
        )
    
    def _create_test_message(self, text="Test message"):
        """Create a mock Telegram message"""
        message = Mock(spec=Message)
        message.message_id = 1
        message.text = text
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
        message.date = int(time.time())
        message.photo = None
        message.document = None
        return message
    
    def test_process_message_from_separate_thread(self):
        """Test that _process_message can be called from a separate thread"""
        # This simulates the real scenario where polling happens in a separate thread
        
        # Start an event loop in the main thread (simulating the async main())
        async def run_test():
            # Set the event loop reference (simulating start_background_tasks)
            self.handlers._event_loop = asyncio.get_running_loop()
            self.handlers.start_background_tasks()
            
            # Create a test message
            message = self._create_test_message()
            
            # Mock the bot's reply_to to return a message
            processing_msg = self._create_test_message("Processing...")
            self.mock_bot.reply_to.return_value = processing_msg
            
            # Track if the handler completed successfully
            success = threading.Event()
            error = None
            
            def call_handler():
                """Call handler from separate thread"""
                nonlocal error
                try:
                    self.handlers._process_message(message)
                    success.set()
                except Exception as e:
                    error = e
                    success.set()
            
            # Call handler from a separate thread (simulating polling thread)
            handler_thread = threading.Thread(target=call_handler)
            handler_thread.start()
            
            # Wait for handler to complete (with timeout)
            completed = False
            for _ in range(50):  # Wait up to 5 seconds
                if success.is_set():
                    completed = True
                    break
                await asyncio.sleep(0.1)
            
            handler_thread.join(timeout=1)
            
            # Stop background tasks
            self.handlers.stop_background_tasks()
            
            # Verify the handler completed successfully
            self.assertTrue(completed, "Handler did not complete within timeout")
            if error:
                raise error
            
            # Verify that the bot methods were called
            self.mock_bot.reply_to.assert_called()
        
        # Run the async test
        asyncio.run(run_test())
    
    def test_event_loop_not_available(self):
        """Test that handler handles missing event loop gracefully"""
        # Don't set event loop reference
        self.handlers._event_loop = None
        
        message = self._create_test_message()
        
        # Call handler (should not crash, but should log error)
        self.handlers._process_message(message)
        
        # Verify error message was sent
        self.mock_bot.reply_to.assert_called()
        call_args = self.mock_bot.reply_to.call_args
        self.assertIn("event loop", call_args[0][1].lower())
    
    def test_no_runtime_error_from_get_event_loop(self):
        """Test that we don't get RuntimeError from get_event_loop()"""
        # This test verifies the fix - we should NOT call get_event_loop()
        # or run_until_complete() from a thread without an event loop
        
        async def run_test():
            # Set up event loop
            self.handlers._event_loop = asyncio.get_running_loop()
            self.handlers.start_background_tasks()
            
            message = self._create_test_message()
            processing_msg = self._create_test_message("Processing...")
            self.mock_bot.reply_to.return_value = processing_msg
            
            # Track if RuntimeError occurred
            runtime_error_occurred = False
            
            def call_handler():
                nonlocal runtime_error_occurred
                try:
                    # This should NOT raise RuntimeError
                    self.handlers._process_message(message)
                except RuntimeError as e:
                    if "no running event loop" in str(e).lower() or \
                       "cannot be called from a running event loop" in str(e).lower():
                        runtime_error_occurred = True
                        raise
            
            # Call from thread
            handler_thread = threading.Thread(target=call_handler)
            handler_thread.start()
            handler_thread.join(timeout=5)
            
            self.handlers.stop_background_tasks()
            
            # Verify no RuntimeError occurred
            self.assertFalse(
                runtime_error_occurred,
                "RuntimeError occurred - the fix is not working properly"
            )
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
