"""
Knowledge Base Change Detection

Represents changes detected in knowledge base files.
"""

from typing import Set


class KnowledgeBaseChange:
    """Represents a change in knowledge base files"""

    def __init__(self):
        self.added: Set[str] = set()
        self.modified: Set[str] = set()
        self.deleted: Set[str] = set()

    def has_changes(self) -> bool:
        """Check if there are any changes"""
        return bool(self.added or self.modified or self.deleted)

    def __repr__(self) -> str:
        return (
            f"KBChange(added={len(self.added)}, "
            f"modified={len(self.modified)}, deleted={len(self.deleted)})"
        )