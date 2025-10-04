"""
Tests for FileProcessor
"""

import pytest
from pathlib import Path
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
        assert 'pdf' in formats
        assert 'docx' in formats
        assert 'txt' in formats


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
            assert result == expected_format, f"Expected {expected_format} for {file_path}, got {result}"


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
