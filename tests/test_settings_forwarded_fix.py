"""
Test for settings handler forwarded message exclusion
Verifies that forwarded messages are not caught by settings input handler
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from telebot.types import Chat, Message, User

from src.bot.settings_handlers import SettingsHandlers
from src.bot.settings_manager import UserSettingsStorage


class TestSettingsForwardedMessageFix:
    """Test that settings handler correctly excludes forwarded messages"""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary directory for storage"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_bot(self):
        """Create mock async bot"""
        return Mock()

    @pytest.fixture
    def settings_handlers(self, mock_bot, temp_storage_dir):
        """Create settings handlers instance"""
        storage_file = str(Path(temp_storage_dir) / "user_settings_overrides.json")
        # Mock the SettingsManager initialization to avoid file I/O
        with patch('src.bot.settings_handlers.SettingsManager') as mock_manager:
            with patch('src.bot.settings_handlers.SettingsInspector') as mock_inspector:
                mock_manager_instance = Mock()
                mock_inspector_instance = Mock()
                mock_manager.return_value = mock_manager_instance
                mock_inspector.return_value = mock_inspector_instance
                return SettingsHandlers(mock_bot, handlers=None)

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
        message.content_type = "text"
        # Not forwarded by default
        message.forward_from = None
        message.forward_from_chat = None
        message.forward_from_message_id = None
        message.forward_sender_name = None
        message.forward_date = None
        return message

    def test_is_forwarded_message_not_forwarded(self, settings_handlers, test_message):
        """Test that non-forwarded messages are correctly identified"""
        assert not settings_handlers._is_forwarded_message(test_message)

    def test_is_forwarded_message_from_user(self, settings_handlers, test_message):
        """Test forwarded message from user detection"""
        test_message.forward_from = Mock()
        test_message.forward_date = 1234567890
        assert settings_handlers._is_forwarded_message(test_message)

    def test_is_forwarded_message_from_chat(self, settings_handlers, test_message):
        """Test forwarded message from chat/channel detection"""
        test_message.forward_from_chat = Mock()
        test_message.forward_date = 1234567890
        assert settings_handlers._is_forwarded_message(test_message)

    def test_is_forwarded_message_from_privacy_user(self, settings_handlers, test_message):
        """Test forwarded message from privacy-enabled user detection"""
        test_message.forward_sender_name = "Anonymous User"
        test_message.forward_date = 1234567890
        assert settings_handlers._is_forwarded_message(test_message)

        # Test that empty string is NOT considered forwarded
        test_message.forward_sender_name = ""
        test_message.forward_date = None
        assert not settings_handlers._is_forwarded_message(test_message)

        # Test that whitespace-only string is NOT considered forwarded
        test_message.forward_sender_name = "   "
        assert not settings_handlers._is_forwarded_message(test_message)

    def test_is_forwarded_message_by_date(self, settings_handlers, test_message):
        """Test forwarded message detection by forward_date"""
        test_message.forward_date = 1234567890
        assert settings_handlers._is_forwarded_message(test_message)

    def test_handler_filter_excludes_forwarded(self, settings_handlers, test_message):
        """Test that handler filter correctly excludes forwarded messages"""
        # Add user to waiting_for_input
        settings_handlers.waiting_for_input[456] = ("KB_PATH", "knowledge_base")

        # Create the filter function used in handler registration
        handler_filter = (
            lambda m: m.from_user.id in settings_handlers.waiting_for_input
            and not settings_handlers._is_forwarded_message(m)
        )

        # Non-forwarded message should pass filter
        assert handler_filter(test_message) is True

        # Forwarded message should NOT pass filter
        test_message.forward_from = Mock()
        test_message.forward_date = 1234567890
        assert handler_filter(test_message) is False

        # Even with user waiting for input, forwarded messages are excluded
        test_message.forward_from_chat = Mock()
        test_message.forward_from = None
        test_message.forward_date = 1234567890
        assert handler_filter(test_message) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
