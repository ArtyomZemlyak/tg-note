"""
Content Parser
Extracts and parses content from messages
"""

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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
        url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
        return re.findall(url_pattern, text)

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
