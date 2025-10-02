"""
Knowledge Base Manager
Creates and manages markdown files in the knowledge base
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from src.agents.base_agent import KBStructure


class KnowledgeBaseManager:
    """Manages knowledge base files and structure"""
    
    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
        self._ensure_structure()
    
    def _ensure_structure(self) -> None:
        """Ensure knowledge base directory structure exists"""
        # Create base KB directory if it doesn't exist
        self.kb_path.mkdir(parents=True, exist_ok=True)
    
    def create_article(
        self,
        content: str,
        title: str,
        kb_structure: KBStructure,
        metadata: Optional[Dict] = None
    ) -> Path:
        """
        Create a new article in the knowledge base using structure from agent
        
        Args:
            content: Article content (markdown)
            title: Article title
            kb_structure: KB structure object from agent
            metadata: Additional metadata
        
        Returns:
            Path to created file
        
        Raises:
            ValueError: If required parameters are invalid
            OSError: If file operations fail
        """
        # Validate inputs
        if not content:
            raise ValueError("Article content cannot be empty")
        
        if not title:
            raise ValueError("Article title cannot be empty")
        
        if not kb_structure:
            raise ValueError("KB structure cannot be None")
        
        if not isinstance(kb_structure, KBStructure):
            raise TypeError(f"kb_structure must be KBStructure instance, got {type(kb_structure)}")
        
        # Validate KB structure has valid category
        if not kb_structure.category:
            raise ValueError("KB structure must have a valid category")
        
        try:
            # Generate filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            slug = self._slugify(title)
            filename = f"{date_str}-{slug}.md"
            
            # Determine file path from KB structure
            try:
                relative_path = kb_structure.get_relative_path()
            except Exception as e:
                raise ValueError(f"Failed to get relative path from KB structure: {e}")
            
            article_dir = self.kb_path / relative_path
            article_dir.mkdir(parents=True, exist_ok=True)
            file_path = article_dir / filename
            
            # Create full content with frontmatter including structure info
            full_content = self._create_frontmatter(title, kb_structure, metadata)
            full_content += "\n\n" + content
            
            # Write file
            file_path.write_text(full_content, encoding="utf-8")
            
            return file_path
        
        except Exception as e:
            # Log and re-raise with context
            raise RuntimeError(f"Failed to create article '{title}': {e}") from e
    
    def _create_frontmatter(
        self,
        title: str,
        kb_structure: KBStructure,
        metadata: Optional[Dict]
    ) -> str:
        """
        Create YAML frontmatter for markdown file with KB structure
        
        Args:
            title: Article title
            kb_structure: KB structure from agent
            metadata: Additional metadata
        
        Returns:
            Frontmatter string
        """
        lines = [
            "---",
            f"title: {title}",
            f"category: {kb_structure.category}",
        ]
        
        if kb_structure.subcategory:
            lines.append(f"subcategory: {kb_structure.subcategory}")
        
        if kb_structure.tags:
            tags_str = ", ".join(kb_structure.tags)
            lines.append(f"tags: [{tags_str}]")
        
        lines.append(f"created_at: {datetime.now().isoformat()}")
        
        if metadata:
            for key, value in metadata.items():
                if key not in ["category", "subcategory", "tags", "created_at"]:
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
    
    def update_index(self, article_path: Path, title: str, kb_structure: KBStructure) -> None:
        """
        Update index.md with new article
        
        Args:
            article_path: Path to article file
            title: Article title
            kb_structure: KB structure from agent
        """
        index_path = self.kb_path / "index.md"
        
        # Read existing index or create new
        if index_path.exists():
            content = index_path.read_text(encoding="utf-8")
        else:
            content = "# Knowledge Base Index\n\n"
        
        # Add new entry with category info
        relative_path = os.path.relpath(article_path, self.kb_path)
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        category_str = kb_structure.category
        if kb_structure.subcategory:
            category_str += f"/{kb_structure.subcategory}"
        
        entry = f"- [{title}]({relative_path}) - {date_str} - `{category_str}`\n"
        
        content += entry
        
        # Write updated index
        index_path.write_text(content, encoding="utf-8")