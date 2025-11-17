"""
Media Metadata Management
Handles .md and .json metadata files for saved media assets
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class MediaMetadata:
    """Manages metadata files for saved media assets"""

    @staticmethod
    def create_metadata_files(
        image_path: Path,
        ocr_text: str,
        file_id: str,
        timestamp: int,
        original_filename: str,
        file_hash: str,
        processing_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create .md and .json metadata files for a media asset.

        Args:
            image_path: Path to saved media file (currently images)
            ocr_text: Extracted text from OCR (can be plain text or JSON string)
            file_id: Telegram file_id
            timestamp: Unix timestamp when asset was received
            original_filename: Original filename from Telegram
            file_hash: SHA256 hash of file
            processing_metadata: Optional metadata from file processor (docling settings, etc.)
        """
        # AICODE-NOTE: Create companion .md and .json files for each media asset
        # This reduces prompt length and helps agent understand the attachment content
        base_path = image_path.with_suffix("")

        # AICODE-NOTE: Extract markdown from JSON if ocr_text is a JSON string
        markdown_text = ocr_text
        structured_data = None

        if ocr_text.strip():
            try:
                # Try to parse as JSON
                parsed = json.loads(ocr_text)
                if isinstance(parsed, dict):
                    structured_data = parsed
                    # Extract text content from JSON structure
                    # Priority: markdown > text > content
                    if "markdown" in parsed:
                        markdown_text = parsed["markdown"]
                        logger.info(f"Extracted markdown field from structured OCR data")
                    elif "text" in parsed:
                        markdown_text = parsed["text"]
                        logger.info(f"Extracted text field from structured OCR data")
                    elif "content" in parsed:
                        markdown_text = parsed["content"]
                        logger.info(f"Extracted content field from structured OCR data")
                    else:
                        # JSON without readable content fields, keep original
                        logger.warning(
                            f"JSON structure has no markdown/text/content fields, using raw JSON"
                        )
                        markdown_text = json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # Not JSON, use as-is
                pass

        # Create .md file with extracted markdown text
        md_path = Path(str(base_path) + ".md")
        md_content = f"""# Image Description

**File:** {image_path.name}
**Original:** {original_filename}
**Received:** {timestamp}

## Extracted Text (OCR)

{markdown_text if markdown_text.strip() else "_No text detected in image_"}

## Usage Instructions

When referencing this image in markdown:
1. Use relative path based on file location
2. Add descriptive alt text based on OCR content above
3. Add text description BELOW the image for GitHub rendering

Example:
```markdown
![Description based on OCR](../media/{image_path.name})

**Image shows:** [Describe what the image contains based on OCR]
```
"""
        md_path.write_text(md_content, encoding="utf-8")
        logger.info(f"Created metadata file: {md_path}")

        # Create .json file with ALL processing settings
        json_path = Path(str(base_path) + ".json")
        json_data = {
            "file_id": file_id,
            "timestamp": timestamp,
            "original_filename": original_filename,
            "file_hash": file_hash,
            "media_filename": image_path.name,
            "ocr_extracted": bool(markdown_text.strip()),
            "ocr_length": len(markdown_text),
        }

        # AICODE-NOTE: Include structured OCR data if present (from MCP/docling)
        if structured_data:
            json_data["ocr_structured"] = structured_data

        # AICODE-NOTE: Include all processing metadata (docling backend, settings, etc.)
        if processing_metadata:
            json_data["processing_metadata"] = processing_metadata

        json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Created settings file: {json_path}")

    @staticmethod
    def read_metadata(media_filename: str, media_dir: Path) -> Optional[Dict]:
        """
        Read metadata for an image

        Args:
            media_filename: Name of media file
            media_dir: Directory containing media assets

        Returns:
            Dict with 'description' (from .md) and 'settings' (from .json), or None if not found
        """
        image_path = media_dir / media_filename
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
    def get_media_description_summary(media_filename: str, media_dir: Path) -> str:
        """
        Get a brief summary of image content for agent prompt

        Args:
            media_filename: Name of media file
            media_dir: Directory containing media assets

        Returns:
            Brief text description of image content
        """
        metadata = MediaMetadata.read_metadata(media_filename, media_dir)
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

        return f"Media file: {settings.get('original_filename', media_filename)}"
