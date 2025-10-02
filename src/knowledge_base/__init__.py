"""
Knowledge Base Manager
Manages markdown files, git operations, and repositories
"""

from .manager import KnowledgeBaseManager
from .git_ops import GitOperations
from .repository import RepositoryManager
from .user_settings import UserSettings

__all__ = [
    'KnowledgeBaseManager',
    'GitOperations',
    'RepositoryManager',
    'UserSettings',
]