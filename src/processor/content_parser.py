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

    def __init__(self):
        """Initialize content parser with file processor"""
        self.file_processor = FileProcessor()
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
            kb_path: Path to knowledge base root (for saving images)

        Returns:
            Parsed content dictionary with file contents and image references
        """
        result = self.parse_message_group(group.messages)

        # Track unsupported media types for logging
        unsupported_media = []

        # Process attached files if bot is provided
        if bot and self.file_processor.is_available():
            file_contents = []

            # AICODE-NOTE: Prepare KB images directory for saving Telegram images
            kb_images_dir = None
            if kb_path:
                kb_images_dir = Path(kb_path) / "images"

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
                            kb_images_dir=kb_images_dir,
                            file_id=document.file_id,
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

                # Process photos (images)
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
                                    kb_images_dir=kb_images_dir,
                                    file_id=largest_photo.file_id,
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
                                # AICODE-NOTE: Save path for images so agent can reference them
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

                # Append file contents to text
                file_texts = []
                for file_data in file_contents:
                    # AICODE-NOTE: For saved images, include path so agent can reference them
                    # Images are saved to {kb_path}/images/, but documents are in {kb_path}/topics/
                    # So the relative path from topics/ to images/ is ../images/
                    if "saved_path" in file_data and "saved_filename" in file_data:
                        file_texts.append(
                            f"\n\n--- Содержимое файла: {file_data['file_name']} "
                            f"(сохранено как: ../images/{file_data['saved_filename']}) ---\n"
                            f"{file_data['content']}"
                        )
                    else:
                        file_texts.append(
                            f"\n\n--- Содержимое файла: {file_data['file_name']} ---\n{file_data['content']}"
                        )

                if file_texts:
                    result["text"] = result.get("text", "") + "\n\n".join(file_texts)
                    # Regenerate hash with file contents
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
