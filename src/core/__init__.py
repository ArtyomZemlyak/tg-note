"""
Core Infrastructure
Provides core infrastructure components like DI container.

Note:
- We intentionally avoid importing `service_container` here to prevent
  circular imports during low-level module imports (e.g., when a module imports
  `src.core.rate_limiter`). High-level factory functions should be imported
  directly from `src.core.service_container` by consumers that need them.
"""

from src.core.background_task_manager import BackgroundTaskManager
from src.core.container import Container

__all__ = [
    "BackgroundTaskManager",
    "Container",
]
