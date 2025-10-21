"""
File Change Monitor

Responsible for monitoring file system changes and detecting
which files have been added, modified, or deleted.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Set

from loguru import logger

from src.bot.knowledge_base_change import KnowledgeBaseChange


class FileChangeMonitor:
    """
    Monitors file system changes in knowledge base directories.
    
    Responsibilities:
    - Scan file system for changes
    - Compute file hashes for change detection
    - Detect added, modified, and deleted files
    - Persist file state for next comparison
    """
    
    def __init__(self, kb_root_path: Path, hash_file: Path):
        """
        Initialize file change monitor
        
        Args:
            kb_root_path: Root path to knowledge bases
            hash_file: Path to store file hashes
        """
        self.kb_root_path = kb_root_path
        self.hash_file = hash_file
        self._file_hashes: Dict[str, str] = {}  # file_path -> hash
    
    async def detect_changes(self) -> KnowledgeBaseChange:
        """
        Detect changes in knowledge base files
        
        Returns:
            KnowledgeBaseChange with detected changes
        """
        # Load previous hashes
        previous_hashes = self._file_hashes.copy()
        
        # Scan current state
        await self._scan_knowledge_bases()
        current_hashes = self._file_hashes
        
        # Detect changes
        changes = self._detect_changes(previous_hashes, current_hashes)
        
        logger.debug(f"📊 File change detection: {changes}")
        return changes
    
    async def _scan_knowledge_bases(self) -> None:
        """
        Scan all knowledge bases and compute file hashes
        """
        self._file_hashes.clear()
        
        if not self.kb_root_path.exists():
            logger.warning(f"⚠️  KB root path does not exist: {self.kb_root_path}")
            return
        
        # Find all markdown files in all KBs
        markdown_files = list(self.kb_root_path.rglob("*.md"))
        
        for file_path in markdown_files:
            try:
                # Compute relative path for consistent tracking
                rel_path = str(file_path.relative_to(self.kb_root_path))
                
                # Compute file hash
                content = file_path.read_bytes()
                file_hash = hashlib.md5(content).hexdigest()
                
                self._file_hashes[rel_path] = file_hash
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to hash file {file_path}: {e}")
        
        logger.debug(f"📊 Scanned {len(self._file_hashes)} markdown files")
    
    def _detect_changes(
        self, previous: Dict[str, str], current: Dict[str, str]
    ) -> KnowledgeBaseChange:
        """
        Detect changes between previous and current file states
        
        Args:
            previous: Previous file hashes
            current: Current file hashes
            
        Returns:
            KnowledgeBaseChange with detected changes
        """
        changes = KnowledgeBaseChange()
        
        # Find new and modified files
        for file_path, current_hash in current.items():
            if file_path not in previous:
                changes.added.add(file_path)
            elif previous[file_path] != current_hash:
                changes.modified.add(file_path)
        
        # Find deleted files
        for file_path in previous:
            if file_path not in current:
                changes.deleted.add(file_path)
        
        return changes
    
    async def load_file_hashes(self) -> None:
        """Load file hashes from storage"""
        try:
            if self.hash_file.exists():
                with open(self.hash_file, "r") as f:
                    self._file_hashes = json.load(f)
                logger.debug(f"📥 Loaded {len(self._file_hashes)} file hashes")
            else:
                self._file_hashes = {}
                logger.debug("📝 No previous file hashes found")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load file hashes: {e}")
            self._file_hashes = {}
    
    async def save_file_hashes(self) -> None:
        """Save file hashes to storage"""
        try:
            self.hash_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.hash_file, "w") as f:
                json.dump(self._file_hashes, f, indent=2)
            logger.debug(f"💾 Saved {len(self._file_hashes)} file hashes")
        except Exception as e:
            logger.error(f"❌ Failed to save file hashes: {e}", exc_info=True)
    
    async def read_documents_by_paths(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Read specific files by paths and prepare documents
        
        Args:
            file_paths: List of relative file paths
            
        Returns:
            List of document structures
        """
        documents = []
        
        for rel_path in file_paths:
            try:
                file_path = self.kb_root_path / rel_path
                
                if not file_path.exists():
                    logger.warning(f"⚠️  File not found: {rel_path}")
                    continue
                
                # Read file content
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                # Prepare document structure
                doc = {
                    "id": rel_path,
                    "content": content,
                    "metadata": {
                        "file_path": rel_path,
                        "file_name": file_path.name,
                        "file_size": len(content),
                    },
                }
                
                documents.append(doc)
                
            except Exception as e:
                logger.error(f"❌ Failed to read file {rel_path}: {e}")
        
        return documents
    
    async def read_all_documents(self) -> List[Dict[str, Any]]:
        """
        Read all markdown files and prepare documents
        
        Returns:
            List of document structures
        """
        documents = []
        
        if not self.kb_root_path.exists():
            logger.warning(f"⚠️  KB root path does not exist: {self.kb_root_path}")
            return documents
        
        markdown_files = list(self.kb_root_path.rglob("*.md"))
        
        for file_path in markdown_files:
            try:
                # Compute relative path as document ID
                doc_id = str(file_path.relative_to(self.kb_root_path))
                
                # Read file content
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                # Prepare document structure
                doc = {
                    "id": doc_id,
                    "content": content,
                    "metadata": {
                        "file_path": doc_id,
                        "file_name": file_path.name,
                        "file_size": len(content),
                    },
                }
                
                documents.append(doc)
                
            except Exception as e:
                logger.error(f"❌ Failed to read file {file_path}: {e}")
        
        logger.info(f"📖 Read {len(documents)} documents")
        return documents