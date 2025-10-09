"""
Processing Tracker
Manages history of processed messages using JSON storage
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from filelock import FileLock
from loguru import logger


class ProcessingTracker:
    """Tracks processed messages to prevent duplicates"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.lock_path = Path(str(storage_path) + ".lock")
        self._ensure_storage()
    
    def _ensure_storage(self) -> None:
        """Ensure storage file and directory exist"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.storage_path.exists():
            self._write_data({
                "processed_messages": [],
                "pending_groups": []
            })
    
    def _read_data(self) -> Dict:
        """Read data from JSON file with file locking"""
        lock = FileLock(self.lock_path)
        
        with lock:
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data: Dict[Any, Any] = json.load(f)
                    return data
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON, returning empty data")
                return {"processed_messages": [], "pending_groups": []}
    
    def _write_data(self, data: Dict) -> None:
        """Write data to JSON file with file locking"""
        lock = FileLock(self.lock_path)
        
        with lock:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    def is_processed(self, content_hash: str) -> bool:
        """
        Check if content has been processed
        
        Args:
            content_hash: SHA256 hash of content
        
        Returns:
            True if already processed, False otherwise
        """
        data = self._read_data()
        
        for msg in data["processed_messages"]:
            if msg.get("content_hash") == content_hash:
                return True
        
        return False
    
    def add_processed(
        self,
        content_hash: str,
        message_ids: List[int],
        chat_id: int,
        status: str = "completed"
    ) -> None:
        """
        Add processed message to tracker
        
        Args:
            content_hash: SHA256 hash of content
            message_ids: List of message IDs
            chat_id: Telegram chat ID
            status: Processing status
        """
        data = self._read_data()
        
        entry = {
            "message_ids": message_ids,
            "chat_id": chat_id,
            "content_hash": content_hash,
            "processed_at": datetime.now().isoformat(),
            "status": status
        }
        
        data["processed_messages"].append(entry)
        self._write_data(data)
        
        logger.info(f"Added processed message: hash={content_hash[:8]}, messages={message_ids}")
    
    def add_pending_group(self, group_id: str, message_ids: List[int]) -> None:
        """
        Add pending message group
        
        Args:
            group_id: Unique group ID
            message_ids: List of message IDs in group
        """
        data = self._read_data()
        
        entry = {
            "group_id": group_id,
            "message_ids": message_ids,
            "started_at": datetime.now().isoformat()
        }
        
        data["pending_groups"].append(entry)
        self._write_data(data)
    
    def remove_pending_group(self, group_id: str) -> None:
        """
        Remove pending group after processing
        
        Args:
            group_id: Unique group ID
        """
        data = self._read_data()
        
        data["pending_groups"] = [
            g for g in data["pending_groups"]
            if g.get("group_id") != group_id
        ]
        
        self._write_data(data)
    
    def get_stats(self) -> Dict:
        """
        Get processing statistics
        
        Returns:
            Dictionary with statistics
        """
        data = self._read_data()
        
        return {
            "total_processed": len(data["processed_messages"]),
            "pending_groups": len(data["pending_groups"]),
            "completed": len([
                m for m in data["processed_messages"]
                if m.get("status") == "completed"
            ]),
            "failed": len([
                m for m in data["processed_messages"]
                if m.get("status") == "failed"
            ])
        }