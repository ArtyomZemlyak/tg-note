"""
Tests for file processor image path validation.
"""

import tempfile
from pathlib import Path

import pytest

# Import the validation function
from src.processor.image_path_validator import validate_image_path


@pytest.fixture
def temp_kb():
    """Create temporary KB structure with media directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_root = Path(tmpdir)
        media_dir = kb_root / "media"
        media_dir.mkdir()

        # Create a test image
        test_img = media_dir / "test.jpg"
        test_img.write_bytes(b"fake image data")

        yield kb_root


def test_validate_image_exists(temp_kb):
    """Test validation passes for existing image."""
    media_dir = temp_kb / "media"
    img_path = media_dir / "test.jpg"

    is_valid, error_msg = validate_image_path(img_path, media_dir)

    assert is_valid is True
    assert error_msg == ""


def test_validate_image_missing():
    """Test validation fails for non-existent image."""
    img_path = Path("/nonexistent/image.jpg")

    is_valid, error_msg = validate_image_path(img_path)

    assert is_valid is False
    assert "does not exist" in error_msg


def test_validate_not_a_file(temp_kb):
    """Test validation fails if path is directory."""
    media_dir = temp_kb / "media"

    is_valid, error_msg = validate_image_path(media_dir, media_dir)

    assert is_valid is False
    assert "not a file" in error_msg


def test_validate_wrong_extension(temp_kb):
    """Test validation fails for non-image extension."""
    media_dir = temp_kb / "media"
    txt_file = media_dir / "file.txt"
    txt_file.write_text("not an image")

    is_valid, error_msg = validate_image_path(txt_file, media_dir)

    assert is_valid is False
    assert "not an image" in error_msg


def test_validate_image_outside_kb(temp_kb):
    """Test validation fails if image is outside KB media directory."""
    media_dir = temp_kb / "media"

    # Create image outside media directory
    outside_img = temp_kb / "outside.jpg"
    outside_img.write_bytes(b"fake image")

    is_valid, error_msg = validate_image_path(outside_img, media_dir)

    assert is_valid is False
    assert "outside KB media directory" in error_msg


def test_validate_image_without_kb_check(temp_kb):
    """Test validation passes without KB directory check."""
    # Create image anywhere
    outside_img = temp_kb / "anywhere.jpg"
    outside_img.write_bytes(b"fake image")

    # No kb_media_dir provided - should only check existence and extension
    is_valid, error_msg = validate_image_path(outside_img, kb_media_dir=None)

    assert is_valid is True
    assert error_msg == ""


def test_validate_various_image_extensions(temp_kb):
    """Test validation works for various image extensions."""
    media_dir = temp_kb / "media"

    extensions = [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp", ".webp"]

    for ext in extensions:
        img_path = media_dir / f"test{ext}"
        img_path.write_bytes(b"fake image")

        is_valid, error_msg = validate_image_path(img_path, media_dir)

        assert is_valid is True, f"Failed for extension {ext}: {error_msg}"
        assert error_msg == ""


def test_validate_case_insensitive_extension(temp_kb):
    """Test validation is case-insensitive for extensions."""
    media_dir = temp_kb / "media"

    # Create image with uppercase extension
    img_path = media_dir / "test.JPG"
    img_path.write_bytes(b"fake image")

    is_valid, error_msg = validate_image_path(img_path, media_dir)

    assert is_valid is True
    assert error_msg == ""


def test_validate_image_in_subdirectory(temp_kb):
    """Test validation works for images in subdirectories of media/."""
    media_dir = temp_kb / "media"
    sub_dir = media_dir / "subfolder"
    sub_dir.mkdir()

    img_path = sub_dir / "test.jpg"
    img_path.write_bytes(b"fake image")

    is_valid, error_msg = validate_image_path(img_path, media_dir)

    assert is_valid is True
    assert error_msg == ""


def test_validate_symlink_image(temp_kb):
    """Test validation follows symlinks."""
    media_dir = temp_kb / "media"
    real_img = media_dir / "real.jpg"
    real_img.write_bytes(b"fake image")

    # Create symlink
    symlink = media_dir / "link.jpg"
    symlink.symlink_to(real_img)

    is_valid, error_msg = validate_image_path(symlink, media_dir)

    # Should be valid (follows symlink)
    assert is_valid is True
    assert error_msg == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
