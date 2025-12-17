"""
Content Parser
Extracts and parses content from messages
"""

import hashlib
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger

from src.processor.file_processor import FileProcessor


class ContentParser:
    """Parses message content and extracts information"""

    def __init__(self, kb_topics_only: bool = True):
        """
        Initialize content parser with file processor

        Args:
            kb_topics_only: If True, agent works in topics/ folder (media path: ../media/)
                          If False, agent works in KB root (media path: media/)
        """
        self.file_processor = FileProcessor()
        self.kb_topics_only = kb_topics_only
        self.logger = logger

        # AICODE-NOTE: Cache for domain availability checks to avoid long timeouts
        # Format: {domain: (is_available, timestamp)}
        self._domain_availability_cache: Dict[str, Tuple[bool, float]] = {}
        self._cache_ttl = 300  # 5 minutes TTL for availability cache

        if self.file_processor.is_available():
            self.logger.info(
                f"File processor initialized. Supported formats: {', '.join(self.file_processor.get_supported_formats())}"
            )
        else:
            self.logger.warning(
                "File processor not available. Document processing will be limited."
            )

    @staticmethod
    def extract_text(message: Dict) -> str:
        """
        Extract text from message

        Args:
            message: Message dictionary

        Returns:
            Extracted text
        """
        text = message.get("text", "")
        caption = message.get("caption", "")
        result: str = text or caption
        return result

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """
        Extract URLs from text

        Args:
            text: Text to parse

        Returns:
            List of found URLs
        """
        # AICODE-NOTE: Improved URL regex to capture full paths including /abs/1234.5678
        # Matches http(s)://domain.com/path?query#fragment
        # Strip trailing punctuation that's not part of URL (., ), comma, etc.)
        url_pattern = r"https?://[^\s<>\"{}|\\^`\[\]]+"
        urls = re.findall(url_pattern, text)

        # Clean up trailing punctuation
        cleaned_urls = []
        for url in urls:
            # Remove trailing punctuation that's likely not part of the URL
            url = re.sub(r"[.,;:!?\)]+$", "", url)
            cleaned_urls.append(url)

        return cleaned_urls

    @staticmethod
    def extract_arxiv_id(url: str) -> Optional[str]:
        """
        Extract arXiv ID from URL.

        Supports formats:
        - https://arxiv.org/abs/2011.10798
        - https://arxiv.org/pdf/2011.10798
        - https://arxiv.org/html/2011.10798
        - https://arxiv.org/pdf/2011.10798.pdf
        - https://export.arxiv.org/pdf/2011.10798.pdf (alternative domain)

        Args:
            url: arXiv URL (may contain trailing punctuation)

        Returns:
            arXiv ID (e.g., "2011.10798") or None if not an arXiv URL
        """
        # AICODE-NOTE: Clean URL first to remove trailing punctuation
        url = re.sub(r"[.,;:!?\)]+$", "", url)

        # Match arXiv URLs with various formats (both arxiv.org and export.arxiv.org)
        pattern = r"(?:export\.)?arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def arxiv_id_to_pdf_url(arxiv_id: str, use_export: bool = False) -> str:
        """
        Convert arXiv ID to PDF download URL.

        Args:
            arxiv_id: arXiv ID (e.g., "2011.10798")
            use_export: If True, use export.arxiv.org domain (fallback for connection issues)

        Returns:
            PDF URL (e.g., "https://arxiv.org/pdf/2011.10798.pdf")
        """
        domain = "export.arxiv.org" if use_export else "arxiv.org"
        return f"https://{domain}/pdf/{arxiv_id}.pdf"

    @staticmethod
    def convert_to_export_url(url: str) -> str:
        """
        Convert arxiv.org URL to export.arxiv.org URL (fallback for connection issues).

        Args:
            url: Original URL (e.g., "https://arxiv.org/pdf/2011.10798.pdf")

        Returns:
            URL with export.arxiv.org domain
        """
        return url.replace("arxiv.org", "export.arxiv.org")

    async def check_domain_availability(self, domain: str, timeout: float = 5.0) -> bool:
        """
        Quick check if a domain is available for downloads.
        Uses cached result if available and not expired.

        Args:
            domain: Domain to check (e.g., "arxiv.org")
            timeout: Timeout for the check in seconds (default: 5s)

        Returns:
            True if domain is available, False otherwise
        """
        current_time = time.time()

        # Check cache first
        if domain in self._domain_availability_cache:
            is_available, timestamp = self._domain_availability_cache[domain]
            if current_time - timestamp < self._cache_ttl:
                self.logger.debug(
                    f"Using cached availability for {domain}: {is_available} "
                    f"(age: {current_time - timestamp:.1f}s)"
                )
                return is_available

        # Perform quick HEAD request to check availability
        try:
            self.logger.info(f"Checking availability of {domain} (timeout: {timeout}s)...")
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                # Try a simple HEAD request to the main page
                response = await client.head(f"https://{domain}")
                is_available = response.status_code < 500  # 2xx, 3xx, 4xx are OK

            self._domain_availability_cache[domain] = (is_available, current_time)
            self.logger.info(f"Domain {domain} availability: {is_available}")
            return is_available

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            self.logger.warning(f"Domain {domain} is not available: {type(e).__name__}")
            self._domain_availability_cache[domain] = (False, current_time)
            return False
        except Exception as e:
            self.logger.warning(f"Error checking {domain} availability: {type(e).__name__}: {e}")
            # Don't cache errors, allow retry next time
            return False

    @staticmethod
    def extract_arxiv_urls(urls: List[str]) -> List[Tuple[str, str]]:
        """
        Extract and normalize arXiv URLs from a list of URLs.

        Args:
            urls: List of URLs to check

        Returns:
            List of tuples (original_url, pdf_url) for arXiv papers
        """
        arxiv_urls = []
        for url in urls:
            arxiv_id = ContentParser.extract_arxiv_id(url)
            if arxiv_id:
                pdf_url = ContentParser.arxiv_id_to_pdf_url(arxiv_id)
                arxiv_urls.append((url, pdf_url))
        return arxiv_urls

    async def download_pdf_from_url(
        self, url: str, filename: Optional[str] = None, kb_media_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Download PDF from URL to temporary or KB media directory.
        Automatically retries with export.arxiv.org if arxiv.org fails.

        Args:
            url: PDF URL to download
            filename: Optional filename (if not provided, will be generated)
            kb_media_dir: If provided, save to KB media directory

        Returns:
            Path to downloaded file or None if download failed
        """
        # AICODE-NOTE: Smart URL selection based on domain availability
        urls_to_try = []

        # If this is an arxiv.org URL, check availability and decide order
        if "arxiv.org" in url and "export.arxiv.org" not in url:
            # Quick availability check (5 seconds timeout)
            arxiv_available = await self.check_domain_availability("arxiv.org", timeout=5.0)

            if arxiv_available:
                # arxiv.org is available, try it first
                urls_to_try = [url, self.convert_to_export_url(url)]
            else:
                # arxiv.org is not available, use export.arxiv.org directly
                self.logger.info("arxiv.org is not available, using export.arxiv.org directly")
                urls_to_try = [self.convert_to_export_url(url)]
        else:
            # Not an arxiv.org URL, use as-is
            urls_to_try = [url]

        last_error = None
        for attempt_num, current_url in enumerate(urls_to_try, 1):
            try:
                self.logger.info(
                    f"Downloading PDF from URL (attempt {attempt_num}/{len(urls_to_try)}): {current_url}"
                )

                # AICODE-NOTE: Increase timeout for large PDFs (arXiv papers can be 10-20MB)
                async with httpx.AsyncClient(follow_redirects=True, timeout=90.0) as client:
                    response = await client.get(current_url)
                    response.raise_for_status()

                    if not filename:
                        # Generate filename from URL
                        filename = Path(url).name
                        if not filename.endswith(".pdf"):
                            filename = f"{filename}.pdf"

                    # Determine save location
                    if kb_media_dir:
                        kb_media_dir = Path(kb_media_dir)
                        kb_media_dir.mkdir(parents=True, exist_ok=True)
                        save_path = kb_media_dir / filename
                    else:
                        # Save to temp directory
                        temp_dir = tempfile.mkdtemp(prefix="tg_note_url_")
                        save_path = Path(temp_dir) / filename

                    save_path.write_bytes(response.content)
                    file_size_mb = len(response.content) / (1024 * 1024)
                    self.logger.info(
                        f"PDF downloaded successfully: {save_path} ({file_size_mb:.2f} MB)"
                    )
                    return save_path

            except httpx.TimeoutException as e:
                last_error = e
                self.logger.warning(
                    f"Timeout downloading PDF from {current_url} after 90 seconds: {e}"
                )
                if attempt_num < len(urls_to_try):
                    self.logger.info(f"Retrying with alternative URL...")
                continue

            except httpx.HTTPStatusError as e:
                last_error = e
                self.logger.warning(
                    f"HTTP error downloading PDF from {current_url}: {e.response.status_code} {e.response.reason_phrase}"
                )
                if attempt_num < len(urls_to_try):
                    self.logger.info(f"Retrying with alternative URL...")
                continue

            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Error downloading PDF from {current_url}: {type(e).__name__}: {e}"
                )
                if attempt_num < len(urls_to_try):
                    self.logger.info(f"Retrying with alternative URL...")
                continue

        # All attempts failed
        self.logger.error(
            f"Failed to download PDF after {len(urls_to_try)} attempts. Last error: {last_error}",
            exc_info=True,
        )
        return None

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """
        Generate SHA256 hash of content

        Args:
            content: Content to hash

        Returns:
            SHA256 hash hex string
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def parse_message_group(messages: List[Dict]) -> Dict:
        """
        Parse a group of messages into structured content

        Args:
            messages: List of message dictionaries

        Returns:
            Parsed content dictionary
        """
        all_text = []
        all_urls = []
        message_ids = []

        for msg in messages:
            text = ContentParser.extract_text(msg)
            all_text.append(text)
            all_urls.extend(ContentParser.extract_urls(text))
            message_ids.append(msg.get("message_id"))

        combined_text = "\n\n".join(filter(None, all_text))
        content_hash = ContentParser.generate_content_hash(combined_text)

        return {
            "text": combined_text,
            "urls": list(set(all_urls)),  # Remove duplicates
            "message_ids": message_ids,
            "content_hash": content_hash,
        }

    async def parse_group_with_files(self, group, bot=None, kb_path: Optional[Path] = None) -> Dict:
        """
        Parse a MessageGroup into structured content, including file processing

        Args:
            group: MessageGroup object with messages attribute
            bot: Bot messaging interface (required for downloading files)
            kb_path: Path to knowledge base root (for saving media files)

        Returns:
            Parsed content dictionary with file contents and image references
        """
        result = self.parse_message_group(group.messages)

        # Track unsupported media types for logging
        unsupported_media = []

        # Process attached files if bot is provided
        if bot and self.file_processor.is_available():
            file_contents = []

            # AICODE-NOTE: Prepare KB media directory for saving Telegram media files
            kb_media_dir = None
            if kb_path:
                kb_media_dir = Path(kb_path) / "media"

            for msg in group.messages:
                msg_timestamp = msg.get("timestamp") or msg.get("date")

                # Process documents
                if msg.get("document"):
                    document = msg.get("document")
                    try:
                        file_info = await bot.get_file(document.file_id)
                        file_result = await self.file_processor.download_and_process_telegram_file(
                            bot=bot,
                            file_info=file_info,
                            original_filename=(
                                document.file_name if hasattr(document, "file_name") else None
                            ),
                            kb_media_dir=kb_media_dir,
                            file_id=document.file_id,
                            file_unique_id=getattr(document, "file_unique_id", None),
                            message_date=msg_timestamp,
                        )

                        if file_result:
                            file_data = {
                                "type": "document",
                                "content": file_result["text"],
                                "metadata": file_result["metadata"],
                                "format": file_result["format"],
                                "file_name": file_result["file_name"],
                            }
                            # Add saved path if image was saved to KB
                            if "saved_path" in file_result:
                                file_data["saved_path"] = file_result["saved_path"]
                                file_data["saved_filename"] = file_result["saved_filename"]

                            file_contents.append(file_data)
                            self.logger.info(
                                f"Successfully processed document: {file_result['file_name']}"
                            )
                    except Exception as e:
                        self.logger.error(f"Error processing document: {e}", exc_info=True)

                # Process photos (currently supported media asset)
                if msg.get("photo"):
                    photos = msg.get("photo")
                    if photos:
                        # Get the largest photo (last in the list)
                        largest_photo = photos[-1] if isinstance(photos, list) else photos
                        try:
                            file_info = await bot.get_file(largest_photo.file_id)
                            file_result = (
                                await self.file_processor.download_and_process_telegram_file(
                                    bot=bot,
                                    file_info=file_info,
                                    original_filename="image.jpg",
                                    kb_media_dir=kb_media_dir,
                                    file_id=largest_photo.file_id,
                                    file_unique_id=getattr(largest_photo, "file_unique_id", None),
                                    message_date=msg_timestamp,
                                )
                            )

                            if file_result:
                                file_data = {
                                    "type": "photo",
                                    "content": file_result["text"],
                                    "metadata": file_result["metadata"],
                                    "format": file_result["format"],
                                    "file_name": file_result.get("file_name", "image.jpg"),
                                }
                                # AICODE-NOTE: Save path for media files so agent can reference them
                                if "saved_path" in file_result:
                                    file_data["saved_path"] = file_result["saved_path"]
                                    file_data["saved_filename"] = file_result["saved_filename"]

                                file_contents.append(file_data)
                                self.logger.info(f"Successfully processed photo")
                        except Exception as e:
                            self.logger.error(f"Error processing photo: {e}", exc_info=True)

                # Log unsupported media types (but still process the message)
                # This allows graceful handling of video, audio, voice, etc.
                content_type = msg.get("content_type", "")
                if content_type in ["video", "audio", "voice", "video_note", "animation"]:
                    if msg.get(content_type):
                        unsupported_media.append(content_type)
                        self.logger.info(
                            f"Message contains {content_type} media (not yet supported for processing). "
                            f"Text/caption will still be extracted."
                        )

            # AICODE-NOTE: Process arXiv URLs found in message text
            # Extract and download PDFs from arXiv links
            if result.get("urls"):
                arxiv_urls = self.extract_arxiv_urls(result["urls"])
                if arxiv_urls:
                    self.logger.info(f"Found {len(arxiv_urls)} arXiv URL(s) in message text")

                    for original_url, pdf_url in arxiv_urls:
                        try:
                            # Extract arXiv ID for filename
                            arxiv_id = self.extract_arxiv_id(original_url)
                            if not arxiv_id:
                                continue

                            # Generate timestamp for filename (use first message timestamp if available)
                            timestamp = int(time.time())
                            if group.messages:
                                first_msg = group.messages[0]
                                timestamp = (
                                    first_msg.get("timestamp") or first_msg.get("date") or timestamp
                                )

                            # AICODE-NOTE: Check if arXiv paper already exists in KB before downloading
                            existing_arxiv_file = None
                            if kb_media_dir:
                                kb_media_dir_abs = Path(kb_media_dir).resolve()
                                kb_media_dir_abs.mkdir(parents=True, exist_ok=True)

                                # Look for existing arXiv files with same ID
                                pattern = f"doc_*_arxiv_{arxiv_id}.pdf"
                                existing_files = list(kb_media_dir_abs.glob(pattern))
                                if existing_files:
                                    existing_arxiv_file = existing_files[0]
                                    self.logger.info(
                                        f"Found existing arXiv paper: {existing_arxiv_file.name}"
                                    )

                            # If file exists, use it; otherwise download
                            if existing_arxiv_file:
                                # Use existing file
                                final_path = existing_arxiv_file
                                final_filename = existing_arxiv_file.name
                                self.logger.info(
                                    f"Reusing existing arXiv paper (duplicate detected): {final_path}"
                                )

                                # Still process it to get the text content
                                try:
                                    file_result = await self.file_processor.process_file(final_path)
                                except Exception as process_error:
                                    self.logger.warning(
                                        f"Failed to process existing arXiv file: {process_error}"
                                    )
                                    file_result = None
                            else:
                                # Download PDF
                                downloaded_path = await self.download_pdf_from_url(
                                    pdf_url, filename=f"arxiv_{arxiv_id}.pdf", kb_media_dir=None
                                )

                                if not downloaded_path:
                                    self.logger.warning(
                                        f"Failed to download arXiv PDF: {original_url}"
                                    )
                                    continue

                                # Process downloaded PDF through docling
                                try:
                                    file_result = await self.file_processor.process_file(
                                        downloaded_path
                                    )

                                    if file_result:
                                        # Save to KB media directory if available
                                        if kb_media_dir:
                                            # Generate unique filename with doc_ prefix
                                            file_hash = self.file_processor._compute_file_hash(
                                                downloaded_path.read_bytes()
                                            )
                                            identifier = (
                                                self.file_processor._extract_unique_identifier(
                                                    file_unique_id=None,
                                                    file_id=None,
                                                    file_hash=file_hash,
                                                )
                                            )
                                            final_filename = (
                                                f"doc_{timestamp}_{identifier}_arxiv_{arxiv_id}.pdf"
                                            )
                                            final_path = kb_media_dir_abs / final_filename
                                            final_path = self.file_processor._ensure_unique_path(
                                                final_path
                                            )

                                            # Copy file to KB media directory
                                            import shutil

                                            shutil.copy2(downloaded_path, final_path)
                                            self.logger.info(f"Saved arXiv PDF to KB: {final_path}")

                                            # Create metadata files (only for new downloads)
                                            try:
                                                from src.processor.media_metadata import (
                                                    MediaMetadata,
                                                )

                                                MediaMetadata.create_metadata_files(
                                                    image_path=final_path,
                                                    ocr_text=file_result.get("text", ""),
                                                    file_id=arxiv_id,
                                                    timestamp=timestamp,
                                                    original_filename=f"arxiv_{arxiv_id}.pdf",
                                                    file_hash=file_hash,
                                                    processing_metadata=file_result.get("metadata"),
                                                )
                                            except Exception as metadata_error:
                                                self.logger.warning(
                                                    f"Failed to create metadata for arXiv PDF: {metadata_error}"
                                                )
                                        else:
                                            # No KB directory - set filename for non-saved file
                                            final_filename = f"arxiv_{arxiv_id}.pdf"
                                            final_path = downloaded_path

                                finally:
                                    # Cleanup temporary download if not saved to KB
                                    if (
                                        not existing_arxiv_file
                                        and not kb_media_dir
                                        and downloaded_path
                                        and downloaded_path.exists()
                                    ):
                                        try:
                                            downloaded_path.unlink()
                                            if downloaded_path.parent.name.startswith(
                                                "tg_note_url_"
                                            ):
                                                downloaded_path.parent.rmdir()
                                        except Exception as cleanup_error:
                                            self.logger.debug(f"Cleanup error: {cleanup_error}")

                            # Add file data to results if processing succeeded
                            if file_result:
                                if kb_media_dir:
                                    file_data = {
                                        "type": "arxiv_document",
                                        "content": file_result["text"],
                                        "metadata": file_result["metadata"],
                                        "format": "pdf",
                                        "file_name": final_filename,
                                        "saved_path": str(final_path),
                                        "saved_filename": final_filename,
                                        "arxiv_url": original_url,
                                        "arxiv_id": arxiv_id,
                                    }
                                else:
                                    # No KB directory - just include the content
                                    file_data = {
                                        "type": "arxiv_document",
                                        "content": file_result["text"],
                                        "metadata": file_result["metadata"],
                                        "format": "pdf",
                                        "file_name": f"arxiv_{arxiv_id}.pdf",
                                        "arxiv_url": original_url,
                                        "arxiv_id": arxiv_id,
                                    }

                                file_contents.append(file_data)
                                self.logger.info(
                                    f"Successfully processed arXiv paper: {arxiv_id} from {original_url}"
                                )

                        except Exception as e:
                            self.logger.error(
                                f"Error processing arXiv URL {original_url}: {e}", exc_info=True
                            )

            # Add file contents to result
            if file_contents:
                result["files"] = file_contents

                # AICODE-NOTE: New approach - just list media filenames, agent reads .md files
                # Track unique media assets to prevent duplicates in prompt
                seen_media_files = set()
                media_filenames = []
                unsaved_document_texts = []

                for file_data in file_contents:
                    # AICODE-NOTE: For saved media files (images AND documents), just collect filenames
                    # Assets are saved to {kb_path}/media/, agent will read .md files
                    if "saved_path" in file_data and "saved_filename" in file_data:
                        saved_filename = file_data["saved_filename"]

                        # Check for duplicates
                        if saved_filename in seen_media_files:
                            self.logger.info(
                                f"Skipping duplicate media reference in prompt: {saved_filename}"
                            )
                            continue
                        seen_media_files.add(saved_filename)
                        media_filenames.append(saved_filename)
                    else:
                        # Unsaved files (not processed or failed to save): include full content
                        unsaved_document_texts.append(
                            f"\n\n--- Содержимое файла: {file_data['file_name']} ---\n{file_data['content']}"
                        )

                # Add media list if any
                if media_filenames:
                    # Determine correct path to media based on agent working directory
                    # If kb_topics_only=True: agent works in topics/, so path is ../media/
                    # If kb_topics_only=False: agent works in KB root, so path is media/
                    media_path = "../media/" if self.kb_topics_only else "media/"

                    media_checklist = "\n".join(f"- [ ] {name}" for name in media_filenames)
                    media_list_text = (
                        "\n\nМедиафайлы и документы:\n"
                        f"лежат в {media_path}\n"
                        "Отметь чекбокс после чтения .md/.json и вставки медиа/документа в БЗ:\n"
                        f"{media_checklist}"
                    )
                    result["text"] = result.get("text", "") + media_list_text

                # Add unsaved document contents if any
                if unsaved_document_texts:
                    result["text"] = result.get("text", "") + "\n\n".join(unsaved_document_texts)

                # Regenerate hash with file contents
                if media_filenames or unsaved_document_texts:
                    result["content_hash"] = self.generate_content_hash(result["text"])

        # Add metadata about unsupported media
        if unsupported_media:
            result["unsupported_media"] = list(set(unsupported_media))

        return result

    def parse_group(self, group) -> Dict:
        """
        Parse a MessageGroup into structured content (synchronous, no file processing)

        Args:
            group: MessageGroup object with messages attribute

        Returns:
            Parsed content dictionary
        """
        return self.parse_message_group(group.messages)

    def generate_hash(self, content: Dict) -> str:
        """
        Generate hash from parsed content dictionary

        Args:
            content: Parsed content dictionary (must have 'text' key)

        Returns:
            SHA256 hash hex string
        """
        text = content.get("text", "")
        return self.generate_content_hash(text)
