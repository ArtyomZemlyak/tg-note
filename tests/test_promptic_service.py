"""
Tests for Promptic Service Integration

This module tests the unified prompt management system using promptic library.
It verifies that all agent modes (note, ask, agent) can obtain prompts through
a single render() call with version and variable support.
"""

import pytest

from src.prompts.promptic_service import PrompticService, prompt_service


class TestPrompticService:
    """Test suite for PrompticService."""

    def test_service_initialization(self):
        """Test that service initializes correctly."""
        service = PrompticService()
        assert service is not None
        assert service.prompts_dir is not None
        assert service.prompts_dir.exists()

    def test_global_instance_exists(self):
        """Test that global prompt_service instance exists."""
        assert prompt_service is not None
        assert isinstance(prompt_service, PrompticService)

    def test_render_agent_instruction(self):
        """Test rendering agent instruction for note mode."""
        instruction = prompt_service.render_agent_instruction(
            locale="ru",
            version="latest",
        )

        assert instruction is not None
        assert len(instruction) > 0
        # Check that key elements are present
        assert "русский" in instruction.lower() or "РУССКИЙ" in instruction

    def test_render_ask_instruction(self):
        """Test rendering ask mode instruction."""
        instruction = prompt_service.render_ask_instruction(
            locale="ru",
            version="latest",
        )

        assert instruction is not None
        assert len(instruction) > 0
        # Check that ask mode elements are present
        assert "вопрос" in instruction.lower() or "знаний" in instruction.lower()

    def test_render_media_instruction(self):
        """Test rendering media instruction."""
        instruction = prompt_service.render_media_instruction(
            locale="ru",
            version="latest",
        )

        assert instruction is not None
        assert len(instruction) > 0
        # Check that media-related content is present
        assert "media" in instruction.lower() or "медиа" in instruction.lower()

    def test_render_note_mode_prompt(self):
        """Test rendering complete note mode prompt."""
        prompt = prompt_service.render(
            "note_mode_prompt",
            version="latest",
            locale="ru",
            vars={
                "text": "Test content about GPT-4",
                "urls": ["https://example.com"],
            },
        )

        assert prompt is not None
        assert len(prompt) > 0
        # Check that content is included
        assert "Test content about GPT-4" in prompt
        # Check that URL is included
        assert "example.com" in prompt

    def test_render_ask_mode_prompt(self):
        """Test rendering complete ask mode prompt."""
        prompt = prompt_service.render(
            "ask_mode_prompt",
            version="latest",
            locale="ru",
            vars={
                "question": "What is GPT-4?",
                "kb_path": "/test/kb",
                "context": "",
            },
        )

        assert prompt is not None
        assert len(prompt) > 0
        # Check that question is included
        assert "What is GPT-4?" in prompt
        # Check that KB path is included
        assert "/test/kb" in prompt

    def test_render_ask_mode_prompt_with_context(self):
        """Test rendering ask mode prompt with conversation context."""
        context = "Previous conversation about AI models"
        prompt = prompt_service.render(
            "ask_mode_prompt",
            version="latest",
            locale="ru",
            vars={
                "question": "Tell me more",
                "kb_path": "/test/kb",
                "context": context,
            },
        )

        assert prompt is not None
        assert len(prompt) > 0
        # Check that context is included
        assert context in prompt

    def test_render_response_formatter(self):
        """Test rendering response formatter prompt."""
        formatter_prompt = prompt_service.render_response_formatter_prompt(
            locale="ru",
            version="latest",
        )

        assert formatter_prompt is not None
        assert len(formatter_prompt) > 0
        # Check that response format elements are present
        assert "agent-result" in formatter_prompt or "JSON" in formatter_prompt

    def test_render_autonomous_agent_instruction(self):
        """Test rendering autonomous agent instruction."""
        instruction = prompt_service.render_autonomous_agent_instruction(
            locale="en",
            version="latest",
        )

        assert instruction is not None
        assert len(instruction) > 0

    def test_legacy_render_with_version(self):
        """Test legacy render with specific version."""
        # Test that we can request a specific version
        # The service should handle version lookup
        content = prompt_service._legacy_render(
            "media",
            "ru",
            "latest",
            {},
        )

        assert content is not None
        assert len(content) > 0


class TestPrompticServiceHelperMethods:
    """Test helper methods of PrompticService."""

    def test_get_response_format(self):
        """Test response format generation."""
        response_format = prompt_service._get_response_format()

        assert response_format is not None
        # Should be JSON
        assert "{" in response_format
        assert "}" in response_format
        # Should contain expected fields
        assert "summary" in response_format

    def test_get_response_format_cached(self):
        """Test that response format is cached."""
        # First call
        format1 = prompt_service._get_response_format()
        # Second call should use cache
        format2 = prompt_service._get_response_format()

        assert format1 == format2
        # Check cache was populated
        assert "__default__" in prompt_service._response_format_cache


class TestPrompticServiceIntegration:
    """Integration tests for PrompticService with actual files."""

    def test_all_prompt_types_render(self):
        """Test that all prompt types can be rendered without errors."""
        prompt_types = [
            ("agent_instruction", {}),
            ("media", {}),
            ("response_formatter", {}),
        ]

        for prompt_name, vars in prompt_types:
            content = prompt_service._legacy_render(
                prompt_name,
                "ru",
                "latest",
                vars,
            )
            assert content is not None, f"Failed to render {prompt_name}"
            assert len(content) > 0, f"Empty content for {prompt_name}"

    def test_note_mode_prompt_structure(self):
        """Test that note mode prompt has expected structure."""
        prompt = prompt_service.render(
            "note_mode_prompt",
            version="latest",
            locale="ru",
            vars={
                "text": "Test",
                "urls": [],
            },
        )

        # Should contain instruction section
        assert "инструкция" in prompt.lower() or "# " in prompt
        # Should contain the text
        assert "Test" in prompt

    def test_ask_mode_prompt_structure(self):
        """Test that ask mode prompt has expected structure."""
        prompt = prompt_service.render(
            "ask_mode_prompt",
            version="latest",
            locale="ru",
            vars={
                "question": "Test question?",
                "kb_path": "/kb",
                "context": "",
            },
        )

        # Should contain the question
        assert "Test question?" in prompt
        # Should contain KB path
        assert "/kb" in prompt
        # Should contain response format instructions
        assert "agent-result" in prompt or "JSON" in prompt
