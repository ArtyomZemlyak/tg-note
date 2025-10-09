"""
Stub Agent
Simple placeholder agent for MVP testing
"""

from datetime import datetime
from typing import Dict

from .base_agent import BaseAgent, KBStructure


class StubAgent(BaseAgent):
    """Stub agent for MVP - minimal processing and formatting"""

    async def process(self, content: Dict) -> Dict:
        """
        Process content with minimal formatting

        Args:
            content: Content dictionary

        Returns:
            Processed content with markdown formatting and KB structure
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
            "version": "0.2.0",
        }

        # Determine KB structure (simple heuristic for stub)
        kb_structure = self._determine_kb_structure(text, urls)

        return {
            "markdown": markdown_content,
            "metadata": metadata,
            "title": BaseAgent.generate_title(text),
            "kb_structure": kb_structure,
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

    def _determine_kb_structure(self, text: str, urls: list) -> KBStructure:
        """
        Determine KB structure based on content (simple heuristic for stub)

        Args:
            text: Content text
            urls: List of URLs

        Returns:
            KBStructure object
        """
        text_lower = text.lower()

        # Simple keyword-based categorization
        if any(
            keyword in text_lower
            for keyword in [
                "ai",
                "artificial intelligence",
                "machine learning",
                "neural network",
                "llm",
                "gpt",
            ]
        ):
            return KBStructure(category="ai", subcategory="machine-learning", tags=["ai"])
        elif any(
            keyword in text_lower for keyword in ["biology", "gene", "dna", "protein", "cell"]
        ):
            return KBStructure(category="biology", tags=["biology"])
        elif any(
            keyword in text_lower for keyword in ["physics", "quantum", "particle", "relativity"]
        ):
            return KBStructure(category="physics", tags=["physics"])
        elif any(
            keyword in text_lower
            for keyword in ["programming", "code", "software", "python", "javascript"]
        ):
            return KBStructure(category="tech", subcategory="programming", tags=["programming"])
        else:
            # Default category
            return KBStructure(category="general", tags=["uncategorized"])
