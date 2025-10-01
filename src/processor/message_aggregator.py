"""
Message Aggregator
Groups consecutive messages into single content blocks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from uuid import uuid4


class MessageGroup:
    """Represents a group of related messages"""
    
    def __init__(self, timeout: int = 30):
        self.group_id = str(uuid4())
        self.messages: List[Dict] = []
        self.started_at = datetime.now()
        self.timeout = timeout
        self.closed = False
    
    def add_message(self, message: Dict) -> None:
        """Add message to group"""
        if not self.closed:
            self.messages.append(message)
    
    def should_close(self) -> bool:
        """Check if group should be closed based on timeout"""
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed >= self.timeout
    
    def close(self) -> None:
        """Close the group"""
        self.closed = True


class MessageAggregator:
    """Aggregates messages into groups"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.active_groups: Dict[int, MessageGroup] = {}
        self.logger = logging.getLogger(__name__)
        self._background_task: Optional[asyncio.Task] = None
        self._running = False
        self._timeout_callback: Optional[Callable] = None
        self._lock = asyncio.Lock()
    
    async def add_message(self, chat_id: int, message: Dict) -> Optional[MessageGroup]:
        """
        Add message to aggregator
        
        Args:
            chat_id: Telegram chat ID
            message: Message data
        
        Returns:
            Closed MessageGroup if timeout reached, None otherwise
        """
        async with self._lock:
            # Get or create group for this chat
            if chat_id not in self.active_groups:
                self.active_groups[chat_id] = MessageGroup(self.timeout)
            
            group = self.active_groups[chat_id]
            
            # Check if current group should be closed
            if group.should_close():
                group.close()
                closed_group = group
                # Start new group
                self.active_groups[chat_id] = MessageGroup(self.timeout)
                self.active_groups[chat_id].add_message(message)
                return closed_group
            
            # Add message to current group
            group.add_message(message)
            return None
    
    async def force_close_group(self, chat_id: int) -> Optional[MessageGroup]:
        """
        Force close group for a chat
        
        Args:
            chat_id: Telegram chat ID
        
        Returns:
            Closed MessageGroup if exists, None otherwise
        """
        async with self._lock:
            if chat_id in self.active_groups:
                group = self.active_groups[chat_id]
                group.close()
                del self.active_groups[chat_id]
                return group
            return None
    
    def set_timeout_callback(self, callback: Callable) -> None:
        """
        Set callback function to be called when a group times out
        
        Args:
            callback: Async function that takes chat_id and MessageGroup as arguments
        """
        self._timeout_callback = callback
    
    def start_background_task(self) -> None:
        """Start the background task to check for timed-out groups"""
        if self._background_task is not None:
            self.logger.warning("Background task already running")
            return
        
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._background_task = loop.create_task(self._check_timeouts())
            self.logger.info("MessageAggregator background task started")
        except RuntimeError:
            # No event loop running, will be started later
            self.logger.warning("No event loop running, background task not started")
    
    def stop_background_task(self) -> None:
        """Stop the background task"""
        self._running = False
        if self._background_task is not None:
            self._background_task.cancel()
            self._background_task = None
            self.logger.info("MessageAggregator background task stopped")
    
    async def _check_timeouts(self) -> None:
        """Background task that periodically checks for timed-out groups"""
        self.logger.info("Starting timeout checker background task")
        
        while self._running:
            try:
                # Check every 5 seconds
                await asyncio.sleep(5)
                
                # Find timed-out groups (with lock protection)
                timed_out = []
                async with self._lock:
                    for chat_id, group in list(self.active_groups.items()):
                        if group.should_close() and not group.closed and len(group.messages) > 0:
                            timed_out.append((chat_id, group))
                            group.close()
                            del self.active_groups[chat_id]
                
                # Process timed-out groups (outside lock to avoid blocking)
                for chat_id, group in timed_out:
                    self.logger.info(f"Group for chat {chat_id} timed out, processing {len(group.messages)} messages")
                    
                    # Call callback if registered (non-blocking)
                    if self._timeout_callback:
                        try:
                            # Create task to run callback asynchronously without blocking
                            asyncio.create_task(self._timeout_callback(chat_id, group))
                        except Exception as e:
                            self.logger.error(f"Error creating timeout callback task for chat {chat_id}: {e}", exc_info=True)
                
            except asyncio.CancelledError:
                self.logger.info("Timeout checker task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in timeout checker: {e}", exc_info=True)