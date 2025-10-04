"""
File Format Processor
Handles various file formats using docling for content extraction
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from loguru import logger

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning("Docling not available. File format recognition will be limited.")


class FileProcessor:
    """Process various file formats and extract content using docling"""
    
    def __init__(self):
        """Initialize file processor"""
        self.logger = logger
        if DOCLING_AVAILABLE:
            try:
                self.converter = DocumentConverter()
                self.logger.info("Docling DocumentConverter initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize DocumentConverter: {e}")
                self.converter = None
        else:
            self.converter = None
    
    def is_available(self) -> bool:
        """Check if docling is available and properly initialized"""
        return DOCLING_AVAILABLE and self.converter is not None
    
    def get_supported_formats(self) -> list:
        """Get list of supported file formats"""
        if not self.is_available():
            return []
        
        # Docling supports various formats
        return [
            'pdf', 'docx', 'pptx', 'xlsx',
            'html', 'md', 'txt',
            'jpg', 'jpeg', 'png', 'tiff'
        ]
    
    def detect_file_format(self, file_path: Path) -> Optional[str]:
        """
        Detect file format from extension
        
        Args:
            file_path: Path to the file
        
        Returns:
            File format (extension without dot) or None if not supported
        """
        extension = file_path.suffix.lower().lstrip('.')
        
        if extension in self.get_supported_formats():
            return extension
        
        return None
    
    async def process_file(self, file_path: Path) -> Optional[Dict]:
        """
        Process file and extract content using docling
        
        Args:
            file_path: Path to the file to process
        
        Returns:
            Dictionary with extracted content and metadata, or None on failure
        """
        if not self.is_available():
            self.logger.warning("Docling not available, cannot process file")
            return None
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return None
        
        file_format = self.detect_file_format(file_path)
        
        if not file_format:
            self.logger.warning(f"Unsupported file format: {file_path.suffix}")
            return None
        
        try:
            self.logger.info(f"Processing file with docling: {file_path.name} (format: {file_format})")
            
            # Convert document using docling
            result = self.converter.convert(str(file_path))
            
            # Extract text content
            text_content = ""
            if hasattr(result, 'document') and result.document:
                # Get markdown representation
                text_content = result.document.export_to_markdown()
            
            # Extract metadata
            metadata = {
                'file_name': file_path.name,
                'file_format': file_format,
                'file_size': file_path.stat().st_size,
            }
            
            # Add document-specific metadata if available
            if hasattr(result, 'document') and result.document:
                doc = result.document
                if hasattr(doc, 'name') and doc.name:
                    metadata['document_title'] = doc.name
                if hasattr(doc, 'origin') and doc.origin:
                    metadata['document_origin'] = str(doc.origin)
            
            self.logger.info(f"Successfully processed file: {file_path.name}, extracted {len(text_content)} characters")
            
            return {
                'text': text_content,
                'metadata': metadata,
                'format': file_format,
                'file_name': file_path.name
            }
            
        except Exception as e:
            self.logger.error(f"Error processing file {file_path.name} with docling: {e}", exc_info=True)
            return None
    
    async def download_and_process_telegram_file(
        self, 
        bot, 
        file_info, 
        original_filename: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Download Telegram file and process it
        
        Args:
            bot: Telegram bot instance
            file_info: Telegram file info object (from bot.get_file)
            original_filename: Original filename (optional, for extension detection)
        
        Returns:
            Dictionary with extracted content and metadata, or None on failure
        """
        temp_dir = None
        temp_file = None
        
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix='tg_note_file_')
            
            # Determine file extension
            file_extension = ''
            if original_filename:
                file_extension = Path(original_filename).suffix
            elif hasattr(file_info, 'file_path') and file_info.file_path:
                file_extension = Path(file_info.file_path).suffix
            
            # Create temporary file path
            temp_filename = f"telegram_file{file_extension}"
            temp_file = Path(temp_dir) / temp_filename
            
            # Download file from Telegram
            self.logger.info(f"Downloading Telegram file: {original_filename or 'unknown'}")
            downloaded_file = await bot.download_file(file_info.file_path)
            
            # Save to temporary file
            with open(temp_file, 'wb') as f:
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
