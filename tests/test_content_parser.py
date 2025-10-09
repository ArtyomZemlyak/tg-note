"""
Tests for ContentParser
"""

import pytest

from src.processor.content_parser import ContentParser


def test_extract_text():
    """Test text extraction from message"""
    parser = ContentParser()
    message = {"text": "Hello world"}
    assert parser.extract_text(message) == "Hello world"

    message_with_caption = {"caption": "Image caption"}
    assert parser.extract_text(message_with_caption) == "Image caption"


def test_extract_urls():
    """Test URL extraction from text"""
    parser = ContentParser()
    text = "Check out https://example.com and http://test.org"
    urls = parser.extract_urls(text)

    assert len(urls) == 2
    assert "https://example.com" in urls
    assert "http://test.org" in urls


def test_generate_content_hash():
    """Test content hash generation"""
    parser = ContentParser()
    content1 = "Test content"
    content2 = "Test content"
    content3 = "Different content"

    hash1 = parser.generate_content_hash(content1)
    hash2 = parser.generate_content_hash(content2)
    hash3 = parser.generate_content_hash(content3)

    assert hash1 == hash2  # Same content = same hash
    assert hash1 != hash3  # Different content = different hash
    assert len(hash1) == 64  # SHA256 hash length


def test_parse_message_group():
    """Test parsing message group"""
    parser = ContentParser()
    messages = [
        {"message_id": 1, "text": "First message https://example.com"},
        {"message_id": 2, "text": "Second message"},
        {"message_id": 3, "caption": "Third message http://test.org"},
    ]

    result = parser.parse_message_group(messages)

    assert "First message" in result["text"]
    assert "Second message" in result["text"]
    assert "Third message" in result["text"]
    assert len(result["urls"]) == 2
    assert len(result["message_ids"]) == 3
    assert "content_hash" in result


def test_parse_group():
    """Test parsing MessageGroup object"""

    # Create a mock MessageGroup object
    class MockMessageGroup:
        def __init__(self, messages):
            self.messages = messages

    messages = [
        {"message_id": 1, "text": "Test message"},
        {"message_id": 2, "caption": "Test caption"},
    ]

    group = MockMessageGroup(messages)
    parser = ContentParser()
    result = parser.parse_group(group)

    assert "Test message" in result["text"]
    assert "Test caption" in result["text"]
    assert len(result["message_ids"]) == 2
    assert "content_hash" in result


def test_generate_hash():
    """Test generating hash from content dictionary"""
    parser = ContentParser()

    content1 = {"text": "Same content", "urls": []}
    content2 = {"text": "Same content", "urls": ["http://example.com"]}
    content3 = {"text": "Different content", "urls": []}

    hash1 = parser.generate_hash(content1)
    hash2 = parser.generate_hash(content2)
    hash3 = parser.generate_hash(content3)

    # Same text = same hash (urls are ignored)
    assert hash1 == hash2
    # Different text = different hash
    assert hash1 != hash3
    # Valid SHA256 hash
    assert len(hash1) == 64
