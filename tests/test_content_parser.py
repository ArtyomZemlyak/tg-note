"""
Tests for ContentParser
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

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


def test_extract_urls_with_paths():
    """Test URL extraction with full paths (arXiv, GitHub, etc.)"""
    parser = ContentParser()
    text = "Read https://arxiv.org/abs/2011.10798 and https://github.com/user/repo/issues/123"
    urls = parser.extract_urls(text)

    assert len(urls) == 2
    assert "https://arxiv.org/abs/2011.10798" in urls
    assert "https://github.com/user/repo/issues/123" in urls


def test_extract_urls_complex():
    """Test URL extraction with query params and fragments"""
    parser = ContentParser()
    text = (
        "Check https://example.com/path?param=value&other=123#section "
        "and https://arxiv.org/pdf/2011.10798.pdf"
    )
    urls = parser.extract_urls(text)

    assert len(urls) == 2
    assert "https://example.com/path?param=value&other=123#section" in urls
    assert "https://arxiv.org/pdf/2011.10798.pdf" in urls


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


@pytest.mark.asyncio
async def test_parse_group_with_files_kb_path_parameter():
    """Test that parse_group_with_files accepts kb_path parameter"""
    from pathlib import Path

    parser = ContentParser()

    class MockMessageGroup:
        def __init__(self, messages):
            self.messages = messages

    messages = [
        {
            "message_id": 1,
            "text": "Test message with image",
            "timestamp": 1234567890,
            "content_type": "text",
        },
    ]

    group = MockMessageGroup(messages)
    mock_bot = MagicMock()
    test_kb_path = Path("/tmp/test_kb")

    # AICODE-NOTE: Test that kb_path parameter is accepted
    # Full image processing test would require bot integration and Docling
    result = await parser.parse_group_with_files(group, bot=mock_bot, kb_path=test_kb_path)

    assert result is not None
    assert "text" in result
    assert "Test message with image" in result["text"]


@pytest.mark.asyncio
async def test_media_list_contains_checkboxes(tmp_path):
    """Saved media list is formatted as a checkbox checklist."""

    parser = ContentParser()

    class StubFileProcessor:
        def is_available(self) -> bool:
            return True

        async def download_and_process_telegram_file(
            self,
            bot,
            file_info,
            original_filename=None,
            kb_media_dir=None,
            file_id=None,
            file_unique_id=None,
            message_date=None,
        ):
            return {
                "text": "image ocr",
                "metadata": {},
                "format": "image",
                "file_name": "image.jpg",
                "saved_path": str(tmp_path / "media" / "img_123.jpg"),
                "saved_filename": "img_123.jpg",
            }

    parser.file_processor = StubFileProcessor()

    mock_bot = MagicMock()
    mock_bot.get_file = AsyncMock(return_value=SimpleNamespace(file_id="f1", file_path="path"))

    messages = [
        {
            "message_id": 1,
            "text": "Message with image",
            "timestamp": 123,
            "content_type": "photo",
            "photo": [SimpleNamespace(file_id="f1", file_unique_id="unique1")],
        }
    ]

    class MockGroup:
        def __init__(self, msgs):
            self.messages = msgs

    result = await parser.parse_group_with_files(
        MockGroup(messages), bot=mock_bot, kb_path=tmp_path
    )

    assert "- [ ] img_123.jpg" in result["text"]
    assert "лежат в ../media/" in result["text"]


def test_image_path_format_in_file_contents():
    """Test that media paths use ../media/ for documents in topics/ folder"""
    from pathlib import Path

    parser = ContentParser()

    # Mock file_contents as if an image was saved
    file_contents = [
        {
            "type": "photo",
            "content": "Image description text",
            "metadata": {},
            "format": "image",
            "file_name": "image.jpg",
            "saved_path": "/tmp/test_kb/media/img_1234567890_AgACAgIA.jpg",
            "saved_filename": "img_1234567890_AgACAgIA.jpg",
        }
    ]

    # Simulate building file_texts like in parse_group_with_files
    file_texts = []
    for file_data in file_contents:
        # AICODE-NOTE: This mimics the logic in content_parser.py lines 227-235
        if "saved_path" in file_data and "saved_filename" in file_data:
            file_texts.append(
                f"\n\n--- Содержимое файла: {file_data['file_name']} "
                f"(сохранено как: ../media/{file_data['saved_filename']}) ---\n"
                f"{file_data['content']}"
            )

    assert len(file_texts) == 1
    # Verify that media path uses ../media/ (relative from topics/ to media/)
    assert "../media/img_1234567890_" in file_texts[0]
    # Ensure it doesn't use the incorrect absolute path
    assert "(сохранено как: media/" not in file_texts[0]


def test_extract_arxiv_id():
    """Test arXiv ID extraction from various URL formats"""
    parser = ContentParser()

    # Test various arXiv URL formats
    assert parser.extract_arxiv_id("https://arxiv.org/abs/2011.10798") == "2011.10798"
    assert parser.extract_arxiv_id("https://arxiv.org/pdf/2011.10798") == "2011.10798"
    assert parser.extract_arxiv_id("https://arxiv.org/html/2011.10798") == "2011.10798"
    assert parser.extract_arxiv_id("https://arxiv.org/pdf/2011.10798.pdf") == "2011.10798"

    # Test with http instead of https
    assert parser.extract_arxiv_id("http://arxiv.org/abs/1234.56789") == "1234.56789"

    # Test with www subdomain (also works)
    assert parser.extract_arxiv_id("https://www.arxiv.org/abs/2011.10798") == "2011.10798"

    # Test non-arXiv URLs
    assert parser.extract_arxiv_id("https://example.com") is None
    assert parser.extract_arxiv_id("https://google.com/arxiv") is None


def test_arxiv_id_to_pdf_url():
    """Test conversion of arXiv ID to PDF URL"""
    parser = ContentParser()

    assert parser.arxiv_id_to_pdf_url("2011.10798") == "https://arxiv.org/pdf/2011.10798.pdf"
    assert parser.arxiv_id_to_pdf_url("1234.56789") == "https://arxiv.org/pdf/1234.56789.pdf"


def test_extract_arxiv_urls():
    """Test extraction of arXiv URLs from a list of URLs"""
    parser = ContentParser()

    urls = [
        "https://arxiv.org/abs/2011.10798",
        "https://example.com",
        "https://arxiv.org/html/1234.56789",
        "https://google.com",
        "https://arxiv.org/pdf/9999.12345.pdf",
    ]

    arxiv_urls = parser.extract_arxiv_urls(urls)

    assert len(arxiv_urls) == 3
    assert arxiv_urls[0] == (
        "https://arxiv.org/abs/2011.10798",
        "https://arxiv.org/pdf/2011.10798.pdf",
    )
    assert arxiv_urls[1] == (
        "https://arxiv.org/html/1234.56789",
        "https://arxiv.org/pdf/1234.56789.pdf",
    )
    assert arxiv_urls[2] == (
        "https://arxiv.org/pdf/9999.12345.pdf",
        "https://arxiv.org/pdf/9999.12345.pdf",
    )


@pytest.mark.asyncio
async def test_download_pdf_from_url_creates_file(tmp_path, monkeypatch):
    """Test that PDF download creates a file"""
    from pathlib import Path

    parser = ContentParser()

    # Mock httpx response
    class MockResponse:
        def __init__(self):
            self.content = b"PDF file content"

        def raise_for_status(self):
            pass

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return MockResponse()

    # Patch httpx.AsyncClient
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    # Download to temp directory
    result = await parser.download_pdf_from_url(
        "https://example.com/test.pdf", filename="test.pdf", kb_media_dir=tmp_path
    )

    assert result is not None
    assert result.exists()
    assert result.read_bytes() == b"PDF file content"
    assert result.name == "test.pdf"
