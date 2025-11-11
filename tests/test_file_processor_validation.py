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
    """Create temporary KB structure with images directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_root = Path(tmpdir)
        images_dir = kb_root / "images"
        images_dir.mkdir()

        # Create a test image
        test_img = images_dir / "test.jpg"
        test_img.write_bytes(b"fake image data")

        yield kb_root


def test_validate_image_exists(temp_kb):
    """Test validation passes for existing image."""
    images_dir = temp_kb / "images"
    img_path = images_dir / "test.jpg"

    is_valid, error_msg = validate_image_path(img_path, images_dir)

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
    images_dir = temp_kb / "images"

    is_valid, error_msg = validate_image_path(images_dir, images_dir)

    assert is_valid is False
    assert "not a file" in error_msg


def test_validate_wrong_extension(temp_kb):
    """Test validation fails for non-image extension."""
    images_dir = temp_kb / "images"
    txt_file = images_dir / "file.txt"
    txt_file.write_text("not an image")

    is_valid, error_msg = validate_image_path(txt_file, images_dir)

    assert is_valid is False
    assert "not an image" in error_msg


def test_validate_image_outside_kb(temp_kb):
    """Test validation fails if image is outside KB images directory."""
    images_dir = temp_kb / "images"

    # Create image outside images directory
    outside_img = temp_kb / "outside.jpg"
    outside_img.write_bytes(b"fake image")

    is_valid, error_msg = validate_image_path(outside_img, images_dir)

    assert is_valid is False
    assert "outside KB images directory" in error_msg


def test_validate_image_without_kb_check(temp_kb):
    """Test validation passes without KB directory check."""
    # Create image anywhere
    outside_img = temp_kb / "anywhere.jpg"
    outside_img.write_bytes(b"fake image")

    # No kb_images_dir provided - should only check existence and extension
    is_valid, error_msg = validate_image_path(outside_img, kb_images_dir=None)

    assert is_valid is True
    assert error_msg == ""


def test_validate_various_image_extensions(temp_kb):
    """Test validation works for various image extensions."""
    images_dir = temp_kb / "images"

    extensions = [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp", ".webp"]

    for ext in extensions:
        img_path = images_dir / f"test{ext}"
        img_path.write_bytes(b"fake image")

        is_valid, error_msg = validate_image_path(img_path, images_dir)

        assert is_valid is True, f"Failed for extension {ext}: {error_msg}"
        assert error_msg == ""


def test_validate_case_insensitive_extension(temp_kb):
    """Test validation is case-insensitive for extensions."""
    images_dir = temp_kb / "images"

    # Create image with uppercase extension
    img_path = images_dir / "test.JPG"
    img_path.write_bytes(b"fake image")

    is_valid, error_msg = validate_image_path(img_path, images_dir)

    assert is_valid is True
    assert error_msg == ""


def test_validate_image_in_subdirectory(temp_kb):
    """Test validation works for images in subdirectories of images/."""
    images_dir = temp_kb / "images"
    sub_dir = images_dir / "subfolder"
    sub_dir.mkdir()

    img_path = sub_dir / "test.jpg"
    img_path.write_bytes(b"fake image")

    is_valid, error_msg = validate_image_path(img_path, images_dir)

    assert is_valid is True
    assert error_msg == ""


def test_validate_symlink_image(temp_kb):
    """Test validation follows symlinks."""
    images_dir = temp_kb / "images"
    real_img = images_dir / "real.jpg"
    real_img.write_bytes(b"fake image")

    # Create symlink
    symlink = images_dir / "link.jpg"
    symlink.symlink_to(real_img)

    is_valid, error_msg = validate_image_path(symlink, images_dir)

    # Should be valid (follows symlink)
    assert is_valid is True
    assert error_msg == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
