"""
Stub Agent
Simple placeholder agent for MVP testing
"""

from datetime import datetime
from typing import Dict
from .base_agent import BaseAgent


class StubAgent(BaseAgent):
    """Stub agent for MVP - minimal processing and formatting"""

    async def process(self, content: Dict) -> Dict:
        """
        Process content with minimal formatting

        Args:
            content: Content dictionary

        Returns:
            Processed content with markdown formatting
        """
        if not self.validate_input(content):
            raise ValueError("Invalid input content")

        text = content.get("text", "")
        urls = content.get("urls", [])

        # Create basic markdown structure
        markdown_content = self._format_markdown(text, urls)

        # Generate metadata
        metadata = {
            "processed_at": datetime.now().isoformat(),
            "agent": "StubAgent",
            "version": "0.1.0",
        }

        return {
            "markdown": markdown_content,
            "metadata": metadata,
            "title": self._generate_title(text),
            "category": "general",  # Default category for stub
        }

    def validate_input(self, content: Dict) -> bool:
        """
        Validate input content

        Args:
            content: Content to validate

        Returns:
            True if valid, False otherwise
        """
        return isinstance(content, dict) and "text" in content

    def _format_markdown(self, text: str, urls: list) -> str:
        """
        Format content as markdown

        Args:
            text: Main text content
            urls: List of URLs

        Returns:
            Formatted markdown string
        """
        lines = ["# Content Note", "", "## Content", "", text, ""]

        if urls:
            lines.extend(["## Links", ""])
            for url in urls:
                lines.append(f"- {url}")
            lines.append("")

        return "\n".join(lines)

    def _generate_title(self, text: str, max_length: int = 50) -> str:
        """
        Generate title from text

        Args:
            text: Text to generate title from
            max_length: Maximum title length

        Returns:
            Generated title
        """
        # Take first line or first N characters
        first_line = text.split("\n")[0].strip()

        if len(first_line) > max_length:
            return first_line[:max_length].strip() + "..."

        return first_line or "Untitled Note"
