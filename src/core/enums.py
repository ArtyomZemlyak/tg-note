"""
Core Enums
Defines enumerations used throughout the application
"""

from enum import Enum


class UserMode(str, Enum):
    """
    User working modes
    
    NOTE: User creates and saves notes to KB
    ASK: User asks questions about KB content
    AGENT: User interacts with autonomous agent with full KB access
    """
    
    NOTE = "note"
    ASK = "ask"
    AGENT = "agent"
    
    @classmethod
    def get_default(cls) -> "UserMode":
        """Get default user mode"""
        return cls.NOTE
    
    def get_description(self) -> str:
        """Get human-readable description of the mode"""
        descriptions = {
            self.NOTE: "📝 Режим создания заметок",
            self.ASK: "🤔 Режим вопросов",
            self.AGENT: "🤖 Агентный режим (полный доступ к БЗ)",
        }
        return descriptions.get(self, "Unknown mode")
    
    def get_emoji(self) -> str:
        """Get emoji for the mode"""
        emojis = {
            self.NOTE: "📝",
            self.ASK: "🤔",
            self.AGENT: "🤖",
        }
        return emojis.get(self, "❓")
