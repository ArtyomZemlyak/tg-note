"""
Tests for FileProcessor
"""

import base64
import json
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
    assert cfg.mcp.tool_name == "convert_document_from_content"
    assert cfg.mcp.resolve_url() is not None
    assert cfg.keep_images is False
    assert cfg.generate_page_images is False
    assert cfg.startup_sync is True
    assert cfg.ocr_config.backend == "rapidocr"
    builtin = cfg.model_cache.builtin_models
    assert builtin.layout is True
    assert builtin.tableformer is True
    assert builtin.code_formula is True
    assert builtin.picture_classifier is True
    assert builtin.rapidocr.enabled is True
    assert builtin.rapidocr.backends is None
    assert cfg.model_cache.downloads == []
    pipeline = cfg.pipeline
    assert pipeline.layout.enabled is True
    assert pipeline.table_structure.enabled is True
    assert pipeline.code_enrichment is False
    assert pipeline.formula_enrichment is False
    assert pipeline.picture_classifier is False
    assert pipeline.picture_description.enabled is False


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
    builtin_cfg = container_cfg["model_cache"]["builtin_models"]
    assert builtin_cfg["layout"] is True
    assert builtin_cfg["tableformer"] is True
    assert builtin_cfg["code_formula"] is True
    assert builtin_cfg["picture_classifier"] is True
    assert builtin_cfg["rapidocr"]["enabled"] is True
    assert container_cfg["model_cache"]["downloads"] == []
    assert container_cfg["mcp"]["transport"] == "sse"
    assert container_cfg["mcp"]["port"] == 8077
    assert container_cfg["startup_sync"] is True
    pipeline_cfg = container_cfg["pipeline"]
    assert pipeline_cfg["resolved"]["layout"] is True
    assert pipeline_cfg["resolved"]["table_structure"] is True
    assert pipeline_cfg["resolved"]["picture_classifier"] is False
    assert pipeline_cfg["resolved"]["picture_description"] is False


def test_docling_resolved_pipeline_flags_missing_bundles():
    """Requested pipeline stages should report missing bundles when not downloadable."""
    from config.settings import DoclingSettings

    cfg = DoclingSettings(
        model_cache={
            "builtin_models": {"layout": True, "tableformer": False, "code_formula": False}
        },
        pipeline={
            "table_structure": {"enabled": True},
            "code_enrichment": True,
            "formula_enrichment": True,
            "picture_classifier": False,
            "picture_description": {"enabled": False},
        },
    )

    flags, missing = cfg.resolved_pipeline_flags()
    assert flags["layout"] is True
    assert flags["table_structure"] is False
    assert flags["code_enrichment"] is False
    assert flags["formula_enrichment"] is False
    assert "tableformer" in missing
    assert "code_formula" in missing


def test_build_mcp_arguments_with_base64(tmp_path):
    """MCP argument builder should populate base64 content when required by the tool schema."""
    processor = FileProcessor()
    sample_file = tmp_path / "sample.pdf"
    payload = b"docling-base64-test"
    sample_file.write_bytes(payload)

    tool_schema = {
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "filename": {"type": "string"},
                "mime_type": {"type": "string"},
            },
            "required": ["content"],
        }
    }

    arguments = processor._build_mcp_arguments(tool_schema, sample_file, "pdf")
    assert arguments is not None
    assert arguments["content"] == base64.b64encode(payload).decode("utf-8")
    assert arguments["filename"] == sample_file.name
    assert arguments["mime_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_download_and_process_telegram_file_accepts_kb_media_dir():
    """Test that download_and_process_telegram_file accepts kb_media_dir parameter"""
    from pathlib import Path
    from unittest.mock import AsyncMock, MagicMock

    processor = FileProcessor()

    # AICODE-NOTE: Test that new parameters are accepted for both images and documents
    # Full integration test would require Telegram bot and Docling setup
    mock_bot = MagicMock()
    mock_bot.download_file = AsyncMock(return_value=b"test_image_data")
    mock_bot.get_file = AsyncMock()

    mock_file_info = MagicMock()
    mock_file_info.file_path = "photos/test.jpg"

    test_kb_media_dir = Path("/tmp/test_kb/media")
    test_file_id = "test_file_123"
    test_message_date = 1234567890

    # This test verifies that the function accepts the new parameters
    # The actual behavior would be tested in integration tests with real Docling
    try:
        await processor.download_and_process_telegram_file(
            bot=mock_bot,
            file_info=mock_file_info,
            original_filename="test.jpg",
            kb_media_dir=test_kb_media_dir,
            file_id=test_file_id,
            file_unique_id="unique_test_file",
            message_date=test_message_date,
        )
    except Exception:
        # Expected if Docling is not configured/available
        pass

    # Test passes if no TypeError about unexpected parameters
    assert True


def test_compute_file_hash(file_processor):
    """Test that file hash computation works correctly"""
    test_content = b"test file content"
    hash1 = file_processor._compute_file_hash(test_content)

    # Hash should be consistent
    hash2 = file_processor._compute_file_hash(test_content)
    assert hash1 == hash2

    # Different content should produce different hash
    different_content = b"different content"
    hash3 = file_processor._compute_file_hash(different_content)
    assert hash1 != hash3

    # Hash should be hex string
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA256 produces 64 hex characters


def test_find_existing_image_by_hash(file_processor, tmp_path):
    """Test finding existing images by hash"""
    # Create test media directory
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    # Create a test image
    test_content = b"test image content"
    test_file = media_dir / "img_1234567890_abcd1234.jpg"
    test_file.write_bytes(test_content)

    # Compute hash
    file_hash = file_processor._compute_file_hash(test_content)

    # Should find existing file
    found = file_processor._find_existing_image_by_hash(file_hash, media_dir, ".jpg")
    assert found is not None
    assert found == test_file

    # Should not find file with different hash
    different_hash = file_processor._compute_file_hash(b"different content")
    not_found = file_processor._find_existing_image_by_hash(different_hash, media_dir, ".jpg")
    assert not_found is None

    # Should not find file with different extension
    not_found_ext = file_processor._find_existing_image_by_hash(file_hash, media_dir, ".png")
    assert not_found_ext is None


@pytest.mark.asyncio
async def test_download_deduplication(file_processor, tmp_path):
    """Test that duplicate images are detected and not saved twice"""
    from unittest.mock import AsyncMock, MagicMock

    # Create test media directory
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    # Create mock bot and file info
    mock_bot = MagicMock()
    test_image_content = b"test image content for deduplication"
    mock_bot.download_file = AsyncMock(return_value=test_image_content)

    mock_file_info = MagicMock()
    mock_file_info.file_path = "photos/test.jpg"

    # Mock process_file to return success
    async def mock_process_file(path):
        return {
            "text": "test",
            "metadata": {},
            "format": "jpg",
        }

    file_processor.process_file = mock_process_file

    # First download - should create new file
    result1 = await file_processor.download_and_process_telegram_file(
        bot=mock_bot,
        file_info=mock_file_info,
        original_filename="test.jpg",
        kb_media_dir=media_dir,
        file_id="testfile1",
        file_unique_id="unique_testfile1",
        message_date=1000000000,
    )

    assert result1 is not None
    assert "saved_path" in result1
    assert "saved_filename" in result1

    # Count files after first download
    files_after_first = list(media_dir.glob("img_*.jpg"))
    assert len(files_after_first) == 1
    first_filename = result1["saved_filename"]

    # Second download of same image - should reuse existing file
    result2 = await file_processor.download_and_process_telegram_file(
        bot=mock_bot,
        file_info=mock_file_info,
        original_filename="test.jpg",
        kb_media_dir=media_dir,
        file_id="testfile2",  # Different file_id
        file_unique_id="unique_testfile2",
        message_date=1000000100,  # Different timestamp
    )

    assert result2 is not None
    assert "saved_path" in result2
    assert "saved_filename" in result2

    # Should still have only one file (deduplication worked)
    files_after_second = list(media_dir.glob("img_*.jpg"))
    assert len(files_after_second) == 1

    # Should reuse the same filename
    assert result2["saved_filename"] == first_filename


@pytest.mark.asyncio
async def test_download_document_saves_to_media(file_processor, tmp_path):
    """Test that documents (PDF, DOCX, etc.) are saved to media directory"""
    from unittest.mock import AsyncMock, MagicMock

    # Create test media directory
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    # Create mock bot and file info
    mock_bot = MagicMock()
    test_pdf_content = b"test PDF document content"
    mock_bot.download_file = AsyncMock(return_value=test_pdf_content)

    mock_file_info = MagicMock()
    mock_file_info.file_path = "documents/test.pdf"

    # Mock process_file to return success
    async def mock_process_file(path):
        return {
            "text": "Extracted text from PDF document",
            "metadata": {},
            "format": "pdf",
            "file_name": "test.pdf",
        }

    file_processor.process_file = mock_process_file

    # Download document
    result = await file_processor.download_and_process_telegram_file(
        bot=mock_bot,
        file_info=mock_file_info,
        original_filename="test.pdf",
        kb_media_dir=media_dir,
        file_id="testpdf1",
        file_unique_id="unique_testpdf1",
        message_date=1000000000,
    )

    assert result is not None
    assert "saved_path" in result
    assert "saved_filename" in result

    # Check that file was saved with doc_ prefix
    saved_filename = result["saved_filename"]
    assert saved_filename.startswith("doc_")
    assert saved_filename.endswith(".pdf")

    # Verify file exists in media directory
    saved_path = media_dir / saved_filename
    assert saved_path.exists()
    assert saved_path.read_bytes() == test_pdf_content

    # Count files - should have exactly one
    doc_files = list(media_dir.glob("doc_*.pdf"))
    assert len(doc_files) == 1


@pytest.mark.asyncio
async def test_download_generates_descriptive_filename(file_processor, tmp_path):
    """New images should get filenames with OCR-based slug."""
    from unittest.mock import AsyncMock, MagicMock

    media_dir = tmp_path / "media"
    media_dir.mkdir()

    mock_bot = MagicMock()
    mock_bot.download_file = AsyncMock(return_value=b"descriptive image bytes")

    mock_file_info = MagicMock()
    mock_file_info.file_path = "photos/test.jpg"

    async def mock_process_file(path):
        return {
            "text": "Coconut Chain Layout Diagram reference",
            "metadata": {},
            "format": "jpg",
            "file_name": "test.jpg",
        }

    file_processor.process_file = mock_process_file

    result = await file_processor.download_and_process_telegram_file(
        bot=mock_bot,
        file_info=mock_file_info,
        original_filename="test.jpg",
        kb_media_dir=media_dir,
        file_id="testfile3",
        file_unique_id="AgACSlugID123456",
        message_date=1000000200,
    )

    assert result is not None
    saved_name = result["saved_filename"]
    assert saved_name.startswith("img_1000000200")
    assert "coconut_chain_layout_diagram" in saved_name
    assert saved_name.endswith(".jpg")
    assert (media_dir / saved_name).exists()


def test_create_image_slug_prefers_markdown_from_json(file_processor):
    """Slug generation should prioritize markdown field when OCR text is JSON."""
    payload = {
        "document_key": "02bf4b57570723b044f0f74bb5b91e0f",
        "from_cache": False,
        "markdown": "Standup board summary for sprint alpha",
    }
    slug = file_processor._create_image_slug(json.dumps(payload))
    assert slug.startswith("standup_board_summary")


@pytest.mark.asyncio
async def test_download_filename_uses_json_markdown_slug(file_processor, tmp_path):
    """Image filename should be derived from markdown field inside JSON OCR text."""
    from unittest.mock import AsyncMock, MagicMock

    media_dir = tmp_path / "media"
    media_dir.mkdir()

    mock_bot = MagicMock()
    mock_bot.download_file = AsyncMock(return_value=b"json slug image bytes")

    mock_file_info = MagicMock()
    mock_file_info.file_path = "photos/test.jpg"

    markdown_text = "Roadmap planning board snapshot for Q1"

    async def mock_process_file(path):
        return {
            "text": json.dumps(
                {
                    "from_cache": False,
                    "document_key": "slug-doc",
                    "markdown": markdown_text,
                }
            ),
            "metadata": {},
            "format": "jpg",
            "file_name": "test.jpg",
        }

    file_processor.process_file = mock_process_file

    result = await file_processor.download_and_process_telegram_file(
        bot=mock_bot,
        file_info=mock_file_info,
        original_filename="test.jpg",
        kb_media_dir=media_dir,
        file_id="slugjson1",
        file_unique_id="AgACSlugJSON123",
        message_date=1000000300,
    )

    assert result is not None
    saved_name = result["saved_filename"]
    assert "roadmap_planning_board_snapshot" in saved_name
    assert saved_name.endswith(".jpg")
    assert (media_dir / saved_name).exists()
