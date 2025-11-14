"""
Image Metadata Management
Handles .md and .json metadata files for saved images
"""

import json
from pathlib import Path
from typing import Dict, Optional

from loguru import logger


class ImageMetadata:
    """Manages metadata files for saved images"""

    @staticmethod
    def create_metadata_files(
        image_path: Path,
        ocr_text: str,
        file_id: str,
        timestamp: int,
        original_filename: str,
        file_hash: str,
    ) -> None:
        """
        Create .md and .json metadata files for an image

        Args:
            image_path: Path to saved image file
            ocr_text: Extracted text from OCR
            file_id: Telegram file_id
            timestamp: Unix timestamp when image was received
            original_filename: Original filename from Telegram
            file_hash: SHA256 hash of image file
        """
        # AICODE-NOTE: Create companion .md and .json files for each image
        # This reduces prompt length and helps agent understand image content
        base_path = image_path.with_suffix("")

        # Create .md file with OCR text and description
        md_path = Path(str(base_path) + ".md")
        md_content = f"""# Image Description

**File:** {image_path.name}
**Original:** {original_filename}
**Received:** {timestamp}

## Extracted Text (OCR)

{ocr_text if ocr_text.strip() else "_No text detected in image_"}

## Usage Instructions

When referencing this image in markdown:
1. Use relative path based on file location
2. Add descriptive alt text based on OCR content above
3. Add text description BELOW the image for GitHub rendering

Example:
```markdown
![Description based on OCR](../images/{image_path.name})

**Image shows:** [Describe what the image contains based on OCR]
```
"""
        md_path.write_text(md_content, encoding="utf-8")
        logger.info(f"Created metadata file: {md_path}")

        # Create .json file with processing settings
        json_path = Path(str(base_path) + ".json")
        json_data = {
            "file_id": file_id,
            "timestamp": timestamp,
            "original_filename": original_filename,
            "file_hash": file_hash,
            "image_filename": image_path.name,
            "ocr_extracted": bool(ocr_text.strip()),
            "ocr_length": len(ocr_text),
        }
        json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Created settings file: {json_path}")

    @staticmethod
    def read_metadata(image_filename: str, images_dir: Path) -> Optional[Dict]:
        """
        Read metadata for an image

        Args:
            image_filename: Name of image file
            images_dir: Directory containing images

        Returns:
            Dict with 'description' (from .md) and 'settings' (from .json), or None if not found
        """
        image_path = images_dir / image_filename
        if not image_path.exists():
            return None

        base_path = image_path.with_suffix("")
        md_path = Path(str(base_path) + ".md")
        json_path = Path(str(base_path) + ".json")

        result = {}

        # Read .md description
        if md_path.exists():
            try:
                result["description"] = md_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to read {md_path}: {e}")
                result["description"] = ""
        else:
            result["description"] = ""

        # Read .json settings
        if json_path.exists():
            try:
                result["settings"] = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to read {json_path}: {e}")
                result["settings"] = {}
        else:
            result["settings"] = {}

        return result if result["description"] or result["settings"] else None

    @staticmethod
    def get_image_description_summary(image_filename: str, images_dir: Path) -> str:
        """
        Get a brief summary of image content for agent prompt

        Args:
            image_filename: Name of image file
            images_dir: Directory containing images

        Returns:
            Brief text description of image content
        """
        metadata = ImageMetadata.read_metadata(image_filename, images_dir)
        if not metadata:
            return "No description available"

        settings = metadata.get("settings", {})
        description = metadata.get("description", "")

        # Extract OCR section from description
        if "## Extracted Text (OCR)" in description:
            parts = description.split("## Extracted Text (OCR)")
            if len(parts) > 1:
                ocr_section = parts[1].split("##")[0].strip()
                if ocr_section and "_No text detected" not in ocr_section:
                    # Return first 500 chars of OCR
                    return ocr_section[:50] + ("..." if len(ocr_section) > 50 else "")

        return f"Image file: {settings.get('original_filename', image_filename)}"
