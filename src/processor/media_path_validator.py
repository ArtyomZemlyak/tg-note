"""
Media path validation for file processor.
Validates media file paths before sending to docling for OCR.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def validate_media_path(file_path: Path, kb_media_dir: Optional[Path] = None) -> tuple[bool, str]:
    """
    Validate image file path before processing.

    Args:
        file_path: Path to image file
        kb_media_dir: Expected KB media directory (if provided)

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> from pathlib import Path
        >>> # Valid image
        >>> validate_media_path(Path("media/photo.jpg"))
        (True, '')

        >>> # Missing file
        >>> validate_media_path(Path("/nonexistent/image.jpg"))
        (False, 'Image file does not exist: /nonexistent/image.jpg')

        >>> # Wrong extension
        >>> validate_media_path(Path("document.txt"))
        (False, "File is not an image (extension: .txt)")
    """
    # Check if file exists
    if not file_path.exists():
        return False, f"Image file does not exist: {file_path}"

    # Check if it's a file (not directory)
    if not file_path.is_file():
        return False, f"Path is not a file: {file_path}"

    # Check if it's an image by extension (currently only images stored in media dir)
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp", ".webp"}
    if file_path.suffix.lower() not in image_extensions:
        return False, f"File is not an image (extension: {file_path.suffix})"

    # If KB media directory provided, verify asset is within it
    if kb_media_dir:
        try:
            # Resolve both paths to absolute
            file_resolved = file_path.resolve()
            kb_dir_resolved = kb_media_dir.resolve()

            # Check if file is within KB media directory
            file_resolved.relative_to(kb_dir_resolved)
        except ValueError:
            return (
                False,
                f"Image is outside KB media directory. Expected in: {kb_media_dir}, got: {file_path}",
            )

    return True, ""


# Backward compatibility alias (deprecated)
def validate_image_path(file_path: Path, kb_media_dir: Optional[Path] = None) -> tuple[bool, str]:
    return validate_media_path(file_path, kb_media_dir)
