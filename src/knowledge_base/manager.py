"""
Knowledge Base Manager
Creates and manages markdown files in the knowledge base
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from config.kb_structure import FILENAME_DATE_FORMAT, create_frontmatter, generate_filename
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
        self, content: str, title: str, kb_structure: KBStructure, metadata: Optional[Dict] = None
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
            # Generate filename using config function
            filename = generate_filename(title)

            # Determine file path from KB structure
            try:
                relative_path = kb_structure.get_relative_path()
            except Exception as e:
                raise ValueError(f"Failed to get relative path from KB structure: {e}")

            article_dir = self.kb_path / relative_path
            article_dir.mkdir(parents=True, exist_ok=True)
            file_path = article_dir / filename

            # Create full content with frontmatter using config function
            extra_fields = metadata if metadata else {}
            full_content = create_frontmatter(
                title=title,
                category=kb_structure.category,
                subcategory=kb_structure.subcategory,
                tags=kb_structure.tags,
                extra_fields=extra_fields,
            )
            full_content += "\n" + content

            # Write file
            file_path.write_text(full_content, encoding="utf-8")

            return file_path

        except Exception as e:
            # Log and re-raise with context
            raise RuntimeError(f"Failed to create article '{title}': {e}") from e

    # Removed _create_frontmatter and _slugify - now using config functions

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
        date_str = datetime.now().strftime(FILENAME_DATE_FORMAT)

        category_str = kb_structure.category
        if kb_structure.subcategory:
            category_str += f"/{kb_structure.subcategory}"

        entry = f"- [{title}]({relative_path}) - {date_str} - `{category_str}`\n"

        content += entry

        # Write updated index
        index_path.write_text(content, encoding="utf-8")
