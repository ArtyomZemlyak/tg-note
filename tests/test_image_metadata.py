"""Tests for Image Metadata Management"""

import json
import tempfile
from pathlib import Path

import pytest

from src.processor.image_metadata import ImageMetadata


class TestImageMetadata:
    """Test image metadata creation and reading"""

    def setup_method(self):
        """Create temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.images_dir = Path(self.temp_dir) / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up temporary directory"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_metadata_files(self):
        """Test creating .md and .json metadata files"""
        # Create test image file
        image_path = self.images_dir / "img_1234567890_abc12345.jpg"
        image_path.write_bytes(b"fake image data")

        ocr_text = "Test OCR text\nLine 2"
        file_id = "abc12345"
        timestamp = 1234567890
        original_filename = "test_image.jpg"
        file_hash = "abc123hash"

        # Create metadata files
        ImageMetadata.create_metadata_files(
            image_path=image_path,
            ocr_text=ocr_text,
            file_id=file_id,
            timestamp=timestamp,
            original_filename=original_filename,
            file_hash=file_hash,
        )

        # Check .md file exists and has correct content
        md_path = Path(str(image_path.with_suffix("")) + ".md")
        assert md_path.exists()
        md_content = md_path.read_text(encoding="utf-8")
        assert "Test OCR text" in md_content
        assert "img_1234567890_abc12345.jpg" in md_content
        assert "test_image.jpg" in md_content

        # Check .json file exists and has correct content
        json_path = Path(str(image_path.with_suffix("")) + ".json")
        assert json_path.exists()
        json_data = json.loads(json_path.read_text(encoding="utf-8"))
        assert json_data["file_id"] == file_id
        assert json_data["timestamp"] == timestamp
        assert json_data["original_filename"] == original_filename
        assert json_data["file_hash"] == file_hash
        assert json_data["ocr_extracted"] is True

    def test_create_metadata_no_ocr(self):
        """Test creating metadata when no OCR text available"""
        image_path = self.images_dir / "img_test.jpg"
        image_path.write_bytes(b"fake image data")

        ImageMetadata.create_metadata_files(
            image_path=image_path,
            ocr_text="",
            file_id="test123",
            timestamp=1234567890,
            original_filename="test.jpg",
            file_hash="hash123",
        )

        md_path = Path(str(image_path.with_suffix("")) + ".md")
        md_content = md_path.read_text(encoding="utf-8")
        assert "_No text detected in image_" in md_content

        json_path = Path(str(image_path.with_suffix("")) + ".json")
        json_data = json.loads(json_path.read_text(encoding="utf-8"))
        assert json_data["ocr_extracted"] is False

    def test_read_metadata(self):
        """Test reading metadata from files"""
        image_path = self.images_dir / "img_test.jpg"
        image_path.write_bytes(b"fake image data")

        # Create metadata
        ImageMetadata.create_metadata_files(
            image_path=image_path,
            ocr_text="Test OCR content",
            file_id="test123",
            timestamp=1234567890,
            original_filename="test.jpg",
            file_hash="hash123",
        )

        # Read metadata
        metadata = ImageMetadata.read_metadata("img_test.jpg", self.images_dir)

        assert metadata is not None
        assert "description" in metadata
        assert "settings" in metadata
        assert "Test OCR content" in metadata["description"]
        assert metadata["settings"]["file_id"] == "test123"

    def test_read_metadata_nonexistent(self):
        """Test reading metadata for non-existent image"""
        metadata = ImageMetadata.read_metadata("nonexistent.jpg", self.images_dir)
        assert metadata is None

    def test_get_image_description_summary(self):
        """Test getting brief summary of image content"""
        image_path = self.images_dir / "img_test.jpg"
        image_path.write_bytes(b"fake image data")

        long_ocr_text = "A" * 1000  # Long text to test truncation

        ImageMetadata.create_metadata_files(
            image_path=image_path,
            ocr_text=long_ocr_text,
            file_id="test123",
            timestamp=1234567890,
            original_filename="test.jpg",
            file_hash="hash123",
        )

        summary = ImageMetadata.get_image_description_summary("img_test.jpg", self.images_dir)

        # Summary should be truncated
        assert len(summary) <= 503  # 500 chars + "..."
        assert "A" in summary

    def test_get_image_description_summary_no_ocr(self):
        """Test getting summary when no OCR available"""
        image_path = self.images_dir / "img_test.jpg"
        image_path.write_bytes(b"fake image data")

        ImageMetadata.create_metadata_files(
            image_path=image_path,
            ocr_text="",
            file_id="test123",
            timestamp=1234567890,
            original_filename="original_name.jpg",
            file_hash="hash123",
        )

        summary = ImageMetadata.get_image_description_summary("img_test.jpg", self.images_dir)

        assert "original_name.jpg" in summary


class TestImageMetadataIntegration:
    """Integration tests for image metadata with file processing"""

    def setup_method(self):
        """Create temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.images_dir = Path(self.temp_dir) / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up temporary directory"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_metadata_files_companion_structure(self):
        """Test that metadata files follow naming convention"""
        # Create image with specific name
        image_name = "img_1234567890_abc12345.jpg"
        image_path = self.images_dir / image_name
        image_path.write_bytes(b"test")

        ImageMetadata.create_metadata_files(
            image_path=image_path,
            ocr_text="Test",
            file_id="abc12345",
            timestamp=1234567890,
            original_filename="test.jpg",
            file_hash="hash",
        )

        # Check naming convention
        expected_md = self.images_dir / "img_1234567890_abc12345.md"
        expected_json = self.images_dir / "img_1234567890_abc12345.json"

        assert expected_md.exists()
        assert expected_json.exists()

    def test_multiple_images_metadata(self):
        """Test creating metadata for multiple images"""
        images = [
            ("img_001.jpg", "OCR text 1"),
            ("img_002.jpg", "OCR text 2"),
            ("img_003.jpg", "OCR text 3"),
        ]

        for img_name, ocr_text in images:
            image_path = self.images_dir / img_name
            image_path.write_bytes(b"test")

            ImageMetadata.create_metadata_files(
                image_path=image_path,
                ocr_text=ocr_text,
                file_id="test",
                timestamp=1234567890,
                original_filename=img_name,
                file_hash="hash",
            )

        # Verify all metadata files created
        for img_name, ocr_text in images:
            metadata = ImageMetadata.read_metadata(img_name, self.images_dir)
            assert metadata is not None
            assert ocr_text in metadata["description"]
