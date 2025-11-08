"""
File Format Processor
Handles various file formats using docling for content extraction
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from loguru import logger

from config.settings import DoclingSettings, settings

try:
    from docling.document_converter import DocumentConverter

    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning("Docling not available. File format recognition will be limited.")


class FileProcessor:
    """Process various file formats and extract content using docling"""

    def __init__(self):
        """Initialize file processor"""
        self.logger = logger
        self.settings = settings
        if DOCLING_AVAILABLE:
            try:
                self.converter = DocumentConverter()
                self.logger.info("Docling DocumentConverter initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize DocumentConverter: {e}")
                self.converter = None
        else:
            self.converter = None

    @property
    def docling_config(self) -> DoclingSettings:
        """Return current Docling configuration."""
        return self.settings.MEDIA_PROCESSING_DOCLING

    def is_available(self) -> bool:
        """
        Check if docling is available and media processing is enabled

        Returns:
            True if docling is available, initialized, and media processing is enabled
        """
        return (
            self.settings.is_media_processing_enabled()
            and self.docling_config.enabled
            and DOCLING_AVAILABLE
            and self.converter is not None
        )

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats based on configuration

        Returns:
            List of enabled file format extensions from settings
        """
        if not self.is_available():
            return []

        # Get enabled formats from settings
        return self.docling_config.get_enabled_formats()

    def detect_file_format(self, file_path: Path) -> Optional[str]:
        """
        Detect file format from extension and check if it's enabled in settings

        Args:
            file_path: Path to the file

        Returns:
            File format (extension without dot) or None if not supported/enabled
        """
        extension = file_path.suffix.lower().lstrip(".")

        # Check if format is enabled in settings
        if self.settings.is_format_enabled(extension, "docling"):
            return extension

        self.logger.debug("Docling format disabled in settings: %s", extension)
        return None

    def _extract_document_text(self, document: Any, config: DoclingSettings) -> str:
        """
        Export document content using configured preference with graceful fallback.

        Args:
            document: Docling document object
            config: Docling configuration settings

        Returns:
            Extracted text content (may be empty string if export fails)
        """
        if document is None:
            return ""

        export_order: List[Tuple[str, Callable[[], str]]] = []
        seen: Set[str] = set()

        def add_export(name: str, attribute: str) -> None:
            if name in seen:
                return
            if hasattr(document, attribute):
                method = getattr(document, attribute)
                if callable(method):
                    export_order.append((name, method))
                    seen.add(name)

        if config.prefer_markdown_output:
            add_export("markdown", "export_to_markdown")
        else:
            add_export("text", "export_to_text")

        # Ensure we attempt both exporters if available
        add_export("text", "export_to_text")
        add_export("markdown", "export_to_markdown")

        if config.fallback_plain_text:
            add_export("text", "export_to_text")
            add_export("markdown", "export_to_markdown")

        for name, exporter in export_order:
            try:
                content = exporter()
                if content:
                    if name != "markdown" and config.prefer_markdown_output:
                        self.logger.debug(
                            "Docling used %s export due to fallback configuration", name
                        )
                    return content
            except Exception as export_error:
                self.logger.debug(
                    "Docling export via %s failed: %s", name, export_error, exc_info=True
                )

        return ""

    async def process_file(self, file_path: Path) -> Optional[Dict]:
        """
        Process file and extract content using docling

        Args:
            file_path: Path to the file to process

        Returns:
            Dictionary with extracted content and metadata, or None on failure
        """
        docling_config = self.docling_config

        if not self.settings.is_media_processing_enabled():
            self.logger.info("Media processing is disabled in settings")
            return None

        if not docling_config.enabled:
            self.logger.info("Docling processing disabled in settings")
            return None

        if not self.is_available():
            self.logger.warning("Docling not available, cannot process file")
            return None

        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return None

        raw_extension = file_path.suffix.lower().lstrip(".")
        file_format = self.detect_file_format(file_path)

        if not file_format:
            normalized_formats = docling_config.normalized_formats()
            if raw_extension and raw_extension in normalized_formats:
                self.logger.info(
                    "Docling format %s is disabled in configuration; skipping file %s",
                    raw_extension,
                    file_path.name,
                )
            else:
                self.logger.warning(f"Unsupported file format: {file_path.suffix}")
            return None

        if not docling_config.is_format_enabled(file_format):
            self.logger.info(
                "Docling configuration currently skips format %s; file %s will not be processed",
                file_format,
                file_path.name,
            )
            return None

        file_stats = file_path.stat()

        if docling_config.exceeds_size_limit(file_stats.st_size):
            self.logger.warning(
                "Skipping file %s (%s bytes) because it exceeds Docling limit of %s MB",
                file_path.name,
                file_stats.st_size,
                docling_config.max_file_size_mb,
            )
            return None

        try:
            self.logger.info(
                f"Processing file with docling: {file_path.name} (format: {file_format})"
            )

            # Convert document using docling
            result = self.converter.convert(str(file_path))

            # Extract text content
            document = getattr(result, "document", None)
            text_content = self._extract_document_text(document, docling_config)

            # Extract metadata
            metadata = {
                "file_name": file_path.name,
                "file_format": file_format,
                "file_size": file_stats.st_size,
            }

            # Add document-specific metadata if available
            if document:
                if hasattr(document, "name") and document.name:
                    metadata["document_title"] = document.name
                if hasattr(document, "origin") and document.origin:
                    metadata["document_origin"] = str(document.origin)

            metadata["docling"] = {
                "prefer_markdown_output": docling_config.prefer_markdown_output,
                "fallback_plain_text": docling_config.fallback_plain_text,
                "image_ocr_enabled": docling_config.image_ocr_enabled,
                "max_file_size_mb": docling_config.max_file_size_mb,
                "ocr_languages": list(docling_config.ocr_languages),
            }

            if not text_content:
                self.logger.debug(
                    "Docling returned empty content for file: %s (format: %s)",
                    file_path.name,
                    file_format,
                )

            self.logger.info(
                f"Successfully processed file: {file_path.name}, extracted {len(text_content)} characters"
            )

            return {
                "text": text_content,
                "metadata": metadata,
                "format": file_format,
                "file_name": file_path.name,
            }

        except Exception as e:
            self.logger.error(
                f"Error processing file {file_path.name} with docling: {e}", exc_info=True
            )
            return None

    async def download_and_process_telegram_file(
        self, bot, file_info, original_filename: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Download file and process it

        Args:
            bot: Bot messaging interface
            file_info: File info object (from bot.get_file)
            original_filename: Original filename (optional, for extension detection)

        Returns:
            Dictionary with extracted content and metadata, or None on failure
        """
        if not self.settings.is_media_processing_enabled():
            self.logger.info("Media processing disabled; skipping Telegram file download")
            return None

        if not self.docling_config.enabled:
            self.logger.info("Docling disabled; skipping Telegram file download")
            return None

        if not self.is_available():
            self.logger.warning("Docling not available; skipping Telegram file download")
            return None

        temp_dir = None
        temp_file = None

        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="tg_note_file_")

            # Determine file extension
            file_extension = ""
            if original_filename:
                file_extension = Path(original_filename).suffix
            elif hasattr(file_info, "file_path") and file_info.file_path:
                file_extension = Path(file_info.file_path).suffix

            # Create temporary file path
            temp_filename = f"telegram_file{file_extension}"
            temp_file = Path(temp_dir) / temp_filename

            extension = file_extension.lower().lstrip(".")
            if extension and not self.settings.is_format_enabled(extension, "docling"):
                self.logger.info(
                    "Skipping Telegram file %s because format %s is disabled for Docling",
                    original_filename or file_info.file_path,
                    extension,
                )
                return None

            # Download file from Telegram
            self.logger.info(f"Downloading Telegram file: {original_filename or 'unknown'}")
            downloaded_file = await bot.download_file(file_info.file_path)

            # Save to temporary file
            with open(temp_file, "wb") as f:
                f.write(downloaded_file)

            self.logger.info(f"File downloaded to: {temp_file}")

            # Process the file with docling
            result = await self.process_file(temp_file)

            return result

        except Exception as e:
            self.logger.error(f"Error downloading and processing Telegram file: {e}", exc_info=True)
            return None

        finally:
            # Cleanup temporary files
            try:
                if temp_file and temp_file.exists():
                    os.remove(temp_file)
                    self.logger.debug(f"Removed temporary file: {temp_file}")
                if temp_dir and os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                    self.logger.debug(f"Removed temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                self.logger.warning(f"Error during cleanup: {cleanup_error}")
