"""
Knowledge Base Manager
Creates and manages markdown files in the knowledge base
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class KnowledgeBaseManager:
    """Manages knowledge base files and structure"""
    
    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
        self._ensure_structure()
    
    def _ensure_structure(self) -> None:
        """Ensure knowledge base directory structure exists"""
        # Note: We're not creating the KB structure as it's in another repo
        # This method is kept for future compatibility
        pass
    
    def create_article(
        self,
        content: str,
        title: str,
        category: str = "general",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create a new article in the knowledge base
        
        Args:
            content: Article content (markdown)
            title: Article title
            category: Article category
            metadata: Additional metadata
        
        Returns:
            Path to created file
        """
        # Generate filename
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = self._slugify(title)
        filename = f"{date_str}-{slug}.md"
        
        # Determine file path
        articles_dir = self.kb_path / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)
        file_path = articles_dir / filename
        
        # Create full content with frontmatter
        full_content = self._create_frontmatter(title, category, metadata)
        full_content += "\n\n" + content
        
        # Write file
        file_path.write_text(full_content, encoding="utf-8")
        
        return str(file_path)
    
    def _create_frontmatter(
        self,
        title: str,
        category: str,
        metadata: Optional[Dict]
    ) -> str:
        """
        Create YAML frontmatter for markdown file
        
        Args:
            title: Article title
            category: Article category
            metadata: Additional metadata
        
        Returns:
            Frontmatter string
        """
        lines = [
            "---",
            f"title: {title}",
            f"category: {category}",
            f"created_at: {datetime.now().isoformat()}",
        ]
        
        if metadata:
            for key, value in metadata.items():
                lines.append(f"{key}: {value}")
        
        lines.append("---")
        return "\n".join(lines)
    
    def _slugify(self, text: str) -> str:
        """
        Convert text to URL-friendly slug
        
        Args:
            text: Text to slugify
        
        Returns:
            Slugified text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Replace spaces and special characters with hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        
        # Remove leading/trailing hyphens
        text = text.strip('-')
        
        # Limit length
        max_length = 50
        if len(text) > max_length:
            text = text[:max_length].rstrip('-')
        
        return text or "untitled"
    
    def update_index(self, article_path: str, title: str) -> None:
        """
        Update index.md with new article
        
        Args:
            article_path: Path to article file
            title: Article title
        """
        index_path = self.kb_path / "index.md"
        
        # Read existing index or create new
        if index_path.exists():
            content = index_path.read_text(encoding="utf-8")
        else:
            content = "# Knowledge Base Index\n\n"
        
        # Add new entry
        relative_path = os.path.relpath(article_path, self.kb_path)
        date_str = datetime.now().strftime("%Y-%m-%d")
        entry = f"- [{title}]({relative_path}) - {date_str}\n"
        
        content += entry
        
        # Write updated index
        index_path.write_text(content, encoding="utf-8")