"""
Knowledge Base Structure Configuration
Centralized configuration for KB directory structure and document naming
"""

from datetime import datetime
import re
from pathlib import Path
from typing import List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Knowledge Base Directory Structure
# ═══════════════════════════════════════════════════════════════════════════════

# Base structure template
KB_BASE_STRUCTURE = {
    "topics": {
        "general": {},
        "ai": {
            "machine-learning": {},
            "nlp": {},
            "computer-vision": {},
            "reinforcement-learning": {},
        },
        "tech": {
            "programming": {},
            "web-development": {},
            "devops": {},
            "databases": {},
            "cloud": {},
        },
        "science": {
            "physics": {},
            "biology": {},
            "chemistry": {},
            "mathematics": {},
        },
        "business": {
            "management": {},
            "finance": {},
            "marketing": {},
            "entrepreneurship": {},
        },
    },
}

# Default categories
DEFAULT_CATEGORIES = [
    "general",
    "ai",
    "tech",
    "science",
    "business",
    "biology",
    "physics",
]

# Category to subcategory mapping
CATEGORY_SUBCATEGORIES = {
    "ai": [
        "machine-learning",
        "nlp",
        "computer-vision",
        "reinforcement-learning",
        "deep-learning",
    ],
    "tech": [
        "programming",
        "web-development",
        "devops",
        "databases",
        "cloud",
        "mobile",
        "security",
    ],
    "science": [
        "physics",
        "biology",
        "chemistry",
        "mathematics",
        "astronomy",
    ],
    "business": [
        "management",
        "finance",
        "marketing",
        "entrepreneurship",
        "strategy",
    ],
}

# Path prefix for all topics
TOPICS_PATH_PREFIX = "topics"


# ═══════════════════════════════════════════════════════════════════════════════
# Document Naming Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Date format for filenames (YYYY-MM-DD)
FILENAME_DATE_FORMAT = "%Y-%m-%d"

# Document filename template: {date}-{slug}.md
FILENAME_TEMPLATE = "{date}-{slug}.md"

# Maximum length for slug part of filename
MAX_SLUG_LENGTH = 50

# Characters to remove from slug
SLUG_REMOVE_CHARS = r'[^\w\s-]'

# Characters to replace with hyphen in slug
SLUG_REPLACE_CHARS = r'[-\s]+'

# Default filename if title cannot be generated
DEFAULT_FILENAME = "untitled"


# ═══════════════════════════════════════════════════════════════════════════════
# Frontmatter Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Frontmatter format (YAML)
FRONTMATTER_FORMAT = "yaml"

# Required frontmatter fields
REQUIRED_FRONTMATTER_FIELDS = [
    "title",
    "category",
    "created_at",
]

# Optional frontmatter fields
OPTIONAL_FRONTMATTER_FIELDS = [
    "subcategory",
    "tags",
    "processed_at",
    "agent",
    "version",
]

# Frontmatter template
FRONTMATTER_TEMPLATE = """---
title: {title}
category: {category}
{subcategory_line}
{tags_line}
created_at: {created_at}
{extra_fields}
---"""


# ═══════════════════════════════════════════════════════════════════════════════
# Index Management
# ═══════════════════════════════════════════════════════════════════════════════

# Index filename
INDEX_FILENAME = "index.md"

# Index header
INDEX_HEADER = "# Knowledge Base Index\n\n"

# Index entry template
INDEX_ENTRY_TEMPLATE = "- [{title}]({relative_path}) - {date} - `{category}`\n"


# ═══════════════════════════════════════════════════════════════════════════════
# Initial KB Structure Files
# ═══════════════════════════════════════════════════════════════════════════════

README_CONTENT = """# Knowledge Base

This is an automated knowledge base created by tg-note.

## Structure

- `topics/` - Articles organized by topic
  - `general/` - General notes
  - `ai/` - AI and machine learning topics
  - `tech/` - Technology and programming
  - `science/` - Scientific topics
  - `business/` - Business and management
- `README.md` - This file
- `index.md` - Chronological index of all articles

## Categories

### AI
Machine learning, NLP, computer vision, deep learning, and other AI topics.

### Tech
Programming, web development, DevOps, databases, cloud computing, and technology.

### Science
Physics, biology, chemistry, mathematics, and other scientific topics.

### Business
Management, finance, marketing, entrepreneurship, and business strategy.

### General
Miscellaneous notes that don't fit into other categories.

## Document Format

All documents are in Markdown format with YAML frontmatter:

```markdown
---
title: Document Title
category: ai
subcategory: machine-learning
tags: [python, tensorflow, neural-networks]
created_at: 2025-10-03T12:00:00
---

# Document Title

Content goes here...
```

## Naming Convention

Documents are named using the format: `YYYY-MM-DD-title-slug.md`

Example: `2025-10-03-introduction-to-machine-learning.md`
"""

GITIGNORE_CONTENT = """# OS files
.DS_Store
Thumbs.db

# Editor files
*.swp
*.swo
*~
.vscode/
.idea/

# Temporary files
*.tmp
*.temp
.~*

# Logs
*.log
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

def generate_filename(title: str, date: Optional[datetime] = None) -> str:
    """
    Generate filename from title and date
    
    Args:
        title: Document title
        date: Optional date (defaults to now)
    
    Returns:
        Filename string
    """
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime(FILENAME_DATE_FORMAT)
    slug = slugify(title)
    
    return FILENAME_TEMPLATE.format(date=date_str, slug=slug)


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug
    
    Args:
        text: Text to slugify
    
    Returns:
        Slugified text
    """
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters
    text = re.sub(SLUG_REMOVE_CHARS, '', text)
    
    # Replace spaces and hyphens with single hyphen
    text = re.sub(SLUG_REPLACE_CHARS, '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    # Limit length
    if len(text) > MAX_SLUG_LENGTH:
        text = text[:MAX_SLUG_LENGTH].rstrip('-')
    
    return text or DEFAULT_FILENAME


def get_relative_path(
    category: str,
    subcategory: Optional[str] = None,
    custom_path: Optional[str] = None
) -> str:
    """
    Get relative path for document based on structure
    
    Args:
        category: Main category
        subcategory: Optional subcategory
        custom_path: Optional custom path
    
    Returns:
        Relative path string
    """
    if custom_path:
        return custom_path
    
    category = category if category else DEFAULT_CATEGORIES[0]
    
    parts = [TOPICS_PATH_PREFIX, category]
    if subcategory:
        parts.append(subcategory)
    
    return "/".join(parts)


def create_frontmatter(
    title: str,
    category: str,
    subcategory: Optional[str] = None,
    tags: Optional[List[str]] = None,
    extra_fields: Optional[dict] = None
) -> str:
    """
    Create YAML frontmatter for document
    
    Args:
        title: Document title
        category: Category
        subcategory: Optional subcategory
        tags: Optional list of tags
        extra_fields: Optional extra fields
    
    Returns:
        Frontmatter string
    """
    created_at = datetime.now().isoformat()
    
    # Build optional lines
    subcategory_line = f"subcategory: {subcategory}" if subcategory else ""
    
    tags_line = ""
    if tags:
        tags_str = ", ".join(tags)
        tags_line = f"tags: [{tags_str}]"
    
    extra_lines = []
    if extra_fields:
        for key, value in extra_fields.items():
            if key not in REQUIRED_FRONTMATTER_FIELDS:
                extra_lines.append(f"{key}: {value}")
    
    extra_fields_str = "\n".join(extra_lines)
    
    return FRONTMATTER_TEMPLATE.format(
        title=title,
        category=category,
        subcategory_line=subcategory_line,
        tags_line=tags_line,
        created_at=created_at,
        extra_fields=extra_fields_str
    ).strip() + "\n"


def get_valid_categories() -> List[str]:
    """Get list of valid categories"""
    return DEFAULT_CATEGORIES.copy()


def get_valid_subcategories(category: str) -> List[str]:
    """Get list of valid subcategories for a category"""
    return CATEGORY_SUBCATEGORIES.get(category, [])


def is_valid_category(category: str) -> bool:
    """Check if category is valid"""
    return category in DEFAULT_CATEGORIES


def is_valid_subcategory(category: str, subcategory: str) -> bool:
    """Check if subcategory is valid for category"""
    return subcategory in CATEGORY_SUBCATEGORIES.get(category, [])
