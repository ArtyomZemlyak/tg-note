"""
KB Changes Tracker
Tracks changes to knowledge base during agent execution
"""

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .base_agent import KBStructure


class KBChangesTracker:
    """
    Отслеживает изменения в базе знаний во время работы агента
    
    Используется managed agents (QwenCodeAgent, OpenAIAgent) для
    автоматического сбора информации о создан��ых/измененных файлах
    """
    
    def __init__(self, kb_root_path: Path):
        """
        Initialize tracker
        
        Args:
            kb_root_path: Root path of knowledge base
        """
        self.kb_root_path = kb_root_path.resolve()
        self.files_created: List[Dict] = []
        self.files_edited: List[str] = []
        self.folders_created: List[str] = []
        
        logger.debug(f"[KBChangesTracker] Initialized with KB root: {self.kb_root_path}")
    
    def add_file_created(
        self, 
        path: str, 
        title: str, 
        kb_structure: KBStructure,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Зарегистрировать создание файла
        
        Args:
            path: Relative path to file
            title: File title
            kb_structure: KB structure for the file
            metadata: Optional metadata
        """
        full_path = self.kb_root_path / path
        
        # Прочитать контент файла если он существует
        try:
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
            else:
                logger.warning(f"[KBChangesTracker] File not found: {path}")
                content = ""
        except Exception as e:
            logger.error(f"[KBChangesTracker] Error reading file {path}: {e}")
            content = ""
        
        file_info = {
            "path": path,
            "markdown": content,
            "title": title,
            "kb_structure": kb_structure,
            "metadata": metadata or {}
        }
        
        self.files_created.append(file_info)
        logger.info(f"[KBChangesTracker] Registered file creation: {path}")
    
    def add_folder_created(self, path: str) -> None:
        """
        Зарегистрировать создание папки
        
        Args:
            path: Relative path to folder
        """
        if path not in self.folders_created:
            self.folders_created.append(path)
            logger.info(f"[KBChangesTracker] Registered folder creation: {path}")
    
    def add_file_edited(self, path: str) -> None:
        """
        Зарегистрировать редактирование файла
        
        Args:
            path: Relative path to file
        """
        if path not in self.files_edited:
            self.files_edited.append(path)
            logger.info(f"[KBChangesTracker] Registered file edit: {path}")
    
    def has_changes(self) -> bool:
        """
        Проверить есть ли изменения
        
        Returns:
            True if there are any changes
        """
        return bool(
            self.files_created or 
            self.files_edited or 
            self.folders_created
        )
    
    def get_files_report(self) -> List[Dict]:
        """
        Получить отчет о созданных файлах в формате для handlers
        
        Returns:
            List of file dicts with markdown, title, kb_structure, metadata
        """
        return self.files_created
    
    def get_summary(self) -> str:
        """
        Получить текстовое резюме изменений
        
        Returns:
            Text summary of all changes
        """
        summary_lines = []
        
        if self.files_created:
            summary_lines.append(f"📄 Создано файлов: {len(self.files_created)}")
            for f in self.files_created:
                summary_lines.append(f"  • {f['path']} - {f['title']}")
        
        if self.folders_created:
            summary_lines.append(f"📁 Создано папок: {len(self.folders_created)}")
            for folder in self.folders_created:
                summary_lines.append(f"  • {folder}")
        
        if self.files_edited:
            summary_lines.append(f"✏️ Изменено файлов: {len(self.files_edited)}")
            for f in self.files_edited:
                summary_lines.append(f"  • {f}")
        
        return "\n".join(summary_lines) if summary_lines else "Изменений нет"
    
    def get_stats(self) -> Dict[str, int]:
        """
        Получить статистику изменений
        
        Returns:
            Dictionary with counts
        """
        return {
            "files_created": len(self.files_created),
            "folders_created": len(self.folders_created),
            "files_edited": len(self.files_edited),
            "total_changes": len(self.files_created) + len(self.folders_created) + len(self.files_edited)
        }
    
    def reset(self) -> None:
        """Сбросить все зарегистрированные изменения"""
        self.files_created.clear()
        self.files_edited.clear()
        self.folders_created.clear()
        logger.debug("[KBChangesTracker] Reset all changes")
