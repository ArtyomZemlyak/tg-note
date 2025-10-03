"""
User Settings Manager
Stores and retrieves user-specific KB settings
"""

import json
from pathlib import Path
from typing import Dict, Optional
from filelock import FileLock
from loguru import logger


class UserSettings:
    """Manages user-specific settings for knowledge bases"""
    
    def __init__(self, settings_file: str = "./data/user_settings.json"):
        """
        Initialize user settings manager
        
        Args:
            settings_file: Path to settings file
        """
        self.settings_file = Path(settings_file)
        self.lock_file = Path(str(settings_file) + ".lock")
        
        # Ensure parent directory exists
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize settings file if not exists
        if not self.settings_file.exists():
            self._save_settings({})
    
    def get_user_kb(self, user_id: int) -> Optional[Dict]:
        """
        Get KB settings for a user
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Dict with KB settings or None
        """
        settings = self._load_settings()
        user_key = str(user_id)
        
        return settings.get(user_key)
    
    def set_user_kb(
        self,
        user_id: int,
        kb_name: str,
        kb_type: str = "local",
        github_url: Optional[str] = None,
        credentials: Optional[Dict] = None
    ) -> bool:
        """
        Set KB settings for a user
        
        Args:
            user_id: Telegram user ID
            kb_name: Name of the knowledge base
            kb_type: "local" or "github"
            github_url: GitHub repository URL (if type is "github")
            credentials: Optional credentials dict
        
        Returns:
            True if successful
        """
        try:
            settings = self._load_settings()
            user_key = str(user_id)
            
            settings[user_key] = {
                "kb_name": kb_name,
                "kb_type": kb_type,
                "github_url": github_url,
                "has_credentials": credentials is not None
            }
            
            self._save_settings(settings)
            logger.info(f"Updated KB settings for user {user_id}: {kb_name} ({kb_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting user KB: {e}", exc_info=True)
            return False
    
    def remove_user_kb(self, user_id: int) -> bool:
        """
        Remove KB settings for a user
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            True if successful
        """
        try:
            settings = self._load_settings()
            user_key = str(user_id)
            
            if user_key in settings:
                del settings[user_key]
                self._save_settings(settings)
                logger.info(f"Removed KB settings for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing user KB: {e}", exc_info=True)
            return False
    
    def _load_settings(self) -> Dict:
        """Load settings from file with locking"""
        with FileLock(self.lock_file):
            try:
                if self.settings_file.exists():
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in settings file, returning empty dict")
            except Exception as e:
                logger.error(f"Error loading settings: {e}", exc_info=True)
            
            return {}
    
    def _save_settings(self, settings: Dict) -> None:
        """Save settings to file with locking"""
        with FileLock(self.lock_file):
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error saving settings: {e}", exc_info=True)
                raise
