"""
Tests for ContentParser
"""

import pytest
from src.processor.content_parser import ContentParser


def test_extract_text():
    """Test text extraction from message"""
    message = {"text": "Hello world"}
    assert ContentParser.extract_text(message) == "Hello world"
    
    message_with_caption = {"caption": "Image caption"}
    assert ContentParser.extract_text(message_with_caption) == "Image caption"


def test_extract_urls():
    """Test URL extraction from text"""
    text = "Check out https://example.com and http://test.org"
    urls = ContentParser.extract_urls(text)
    
    assert len(urls) == 2
    assert "https://example.com" in urls
    assert "http://test.org" in urls


def test_generate_content_hash():
    """Test content hash generation"""
    content1 = "Test content"
    content2 = "Test content"
    content3 = "Different content"
    
    hash1 = ContentParser.generate_content_hash(content1)
    hash2 = ContentParser.generate_content_hash(content2)
    hash3 = ContentParser.generate_content_hash(content3)
    
    assert hash1 == hash2  # Same content = same hash
    assert hash1 != hash3  # Different content = different hash
    assert len(hash1) == 64  # SHA256 hash length


def test_parse_message_group():
    """Test parsing message group"""
    messages = [
        {"message_id": 1, "text": "First message https://example.com"},
        {"message_id": 2, "text": "Second message"},
        {"message_id": 3, "caption": "Third message http://test.org"}
    ]
    
    result = ContentParser.parse_message_group(messages)
    
    assert "First message" in result["text"]
    assert "Second message" in result["text"]
    assert "Third message" in result["text"]
    assert len(result["urls"]) == 2
    assert len(result["message_ids"]) == 3
    assert "content_hash" in result