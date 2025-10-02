"""
Content Parser
Extracts and parses content from messages
"""

import re
import hashlib
from typing import Dict, List, Optional


class ContentParser:
    """Parses message content and extracts information"""
    
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
        return text or caption
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """
        Extract URLs from text
        
        Args:
            text: Text to parse
        
        Returns:
            List of found URLs
        """
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
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
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
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
            "content_hash": content_hash
        }
    
    def parse_group(self, group) -> Dict:
        """
        Parse a MessageGroup into structured content
        
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
        text = content.get('text', '')
        return self.generate_content_hash(text)