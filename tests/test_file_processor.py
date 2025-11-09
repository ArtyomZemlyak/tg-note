"""
Tests for FileProcessor
"""

from pathlib import Path

import pytest

from src.processor.file_processor import FileProcessor


@pytest.fixture
def file_processor():
    """Create FileProcessor instance"""
    return FileProcessor()


def test_file_processor_initialization(file_processor):
    """Test FileProcessor initialization"""
    assert file_processor is not None
    # Check if docling is available (may or may not be installed)
    # This test should pass regardless


def test_get_supported_formats(file_processor):
    """Test getting supported formats"""
    formats = file_processor.get_supported_formats()
    assert isinstance(formats, list)

    # If docling is available, should have formats
    if file_processor.is_available():
        assert len(formats) > 0
        assert "pdf" in formats
        assert "docx" in formats
        assert "txt" in formats


def test_detect_file_format(file_processor):
    """Test file format detection"""
    # Test various file extensions
    test_cases = [
        (Path("test.pdf"), "pdf"),
        (Path("test.docx"), "docx"),
        (Path("test.txt"), "txt"),
        (Path("test.jpg"), "jpg"),
        (Path("document.PDF"), "pdf"),  # Case insensitive
    ]

    for file_path, expected_format in test_cases:
        if file_processor.is_available():
            result = file_processor.detect_file_format(file_path)
            assert (
                result == expected_format
            ), f"Expected {expected_format} for {file_path}, got {result}"


def test_detect_unsupported_format(file_processor):
    """Test detection of unsupported formats"""
    unsupported_file = Path("test.xyz")
    result = file_processor.detect_file_format(unsupported_file)

    # Should return None for unsupported formats
    if not file_processor.is_available():
        assert result is None
    else:
        # If docling is available but format not supported
        assert result is None or result == "xyz"


@pytest.mark.asyncio
async def test_process_nonexistent_file(file_processor):
    """Test processing a file that doesn't exist"""
    nonexistent_file = Path("/tmp/nonexistent_file_12345.pdf")
    result = await file_processor.process_file(nonexistent_file)

    # Should return None for nonexistent files
    assert result is None


def test_is_available(file_processor):
    """Test checking if docling is available"""
    available = file_processor.is_available()
    assert isinstance(available, bool)


def test_format_enabled_via_settings(file_processor):
    """Test that format availability respects settings configuration"""
    if not file_processor.is_available():
        pytest.skip("Docling not available")

    # Get formats from settings
    enabled_formats = file_processor.get_supported_formats()
    assert isinstance(enabled_formats, list)

    # Test that enabled formats are detected correctly
    for fmt in enabled_formats:
        test_file = Path(f"test.{fmt}")
        result = file_processor.detect_file_format(test_file)
        assert result == fmt, f"Format {fmt} should be enabled"

    # Test that format checking uses settings
    from config.settings import settings

    # If pdf is in enabled formats, it should be detected
    if "pdf" in enabled_formats:
        assert settings.is_format_enabled("pdf", "docling")
        assert file_processor.detect_file_format(Path("test.pdf")) == "pdf"


def test_media_processing_enabled_flag():
    """Test media processing enabled flag in settings"""
    from config.settings import settings

    # Test that the flag exists and is accessible
    assert hasattr(settings, "MEDIA_PROCESSING_ENABLED")
    assert isinstance(settings.MEDIA_PROCESSING_ENABLED, bool)

    # Test helper methods
    assert hasattr(settings, "is_media_processing_enabled")
    assert isinstance(settings.is_media_processing_enabled(), bool)


def test_media_processing_disabled_returns_empty_formats():
    """Test that when media processing is disabled, get_supported_formats returns empty list"""
    from config.settings import Settings

    # Create settings instance with media processing disabled
    test_settings = Settings(MEDIA_PROCESSING_ENABLED=False)

    # Should return empty list when disabled
    assert test_settings.get_media_processing_formats("docling") == []
    assert not test_settings.is_format_enabled("pdf", "docling")
    assert not test_settings.is_format_enabled("jpg", "docling")


def test_docling_settings_legacy_formats_compatibility():
    """Legacy MEDIA_PROCESSING_DOCLING_FORMATS should populate new Docling configuration."""
    from config.settings import Settings

    legacy_settings = Settings(MEDIA_PROCESSING_DOCLING_FORMATS=["pdf", "docx", "jpg"])

    assert legacy_settings.MEDIA_PROCESSING_DOCLING.formats == ["pdf", "docx", "jpg"]
    assert legacy_settings.get_media_processing_formats("docling") == ["pdf", "docx", "jpg"]


def test_docling_settings_image_ocr_toggle():
    """Image OCR toggle should exclude image formats when disabled."""
    from config.settings import Settings

    updated_settings = Settings(
        MEDIA_PROCESSING_DOCLING={"formats": ["pdf", "jpg"], "image_ocr_enabled": False}
    )

    assert updated_settings.MEDIA_PROCESSING_DOCLING.is_format_enabled("pdf")
    assert not updated_settings.MEDIA_PROCESSING_DOCLING.is_format_enabled("jpg")
    assert updated_settings.get_media_processing_formats("docling") == ["pdf"]


def test_docling_settings_file_size_limit_conversion():
    """Ensure max file size limit converts to bytes correctly."""
    from config.settings import Settings

    unlimited = Settings(MEDIA_PROCESSING_DOCLING={"max_file_size_mb": 0})
    assert unlimited.MEDIA_PROCESSING_DOCLING.max_file_size_bytes is None

    limited = Settings(MEDIA_PROCESSING_DOCLING={"max_file_size_mb": 5})
    assert limited.MEDIA_PROCESSING_DOCLING.max_file_size_bytes == 5 * 1024 * 1024


def test_docling_settings_defaults():
    """Docling settings should default to MCP backend with sane defaults."""
    from config.settings import DoclingSettings

    cfg = DoclingSettings()
    assert cfg.backend == "mcp"
    assert cfg.use_mcp()
    assert cfg.mcp.transport == "sse"
    assert cfg.mcp.listen_host == "0.0.0.0"
    assert cfg.mcp.listen_port == 8077
    assert cfg.mcp.server_name == "docling"
    assert cfg.mcp.resolve_url() is not None
    assert cfg.keep_images is False
    assert cfg.generate_page_images is False
    assert cfg.startup_sync is True
    assert cfg.ocr_config.backend == "rapidocr"
    assert cfg.model_cache.groups
    assert cfg.model_cache.groups[-1].name == "rapidocr"
    assert cfg.model_cache.downloads == []


def test_docling_settings_local_backend_toggle():
    """Switching to local backend should disable MCP usage."""
    from config.settings import DoclingSettings

    cfg = DoclingSettings(backend="local")
    assert cfg.use_local()
    assert not cfg.use_mcp()


def test_docling_settings_container_config():
    """Ensure container config projection is well-formed."""
    from config.settings import DoclingSettings

    cfg = DoclingSettings()
    container_cfg = cfg.to_container_config()

    assert container_cfg["converter"]["ocr"]["backend"] == "rapidocr"
    assert container_cfg["model_cache"]["groups"]
    assert container_cfg["model_cache"]["groups"][-1]["name"] == "rapidocr"
    assert container_cfg["model_cache"]["downloads"] == []
    assert container_cfg["mcp"]["transport"] == "sse"
    assert container_cfg["mcp"]["port"] == 8077
    assert container_cfg["startup_sync"] is True
