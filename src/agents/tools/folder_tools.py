"""
Folder management tools for autonomous agent.

Tools for creating, deleting, and moving folders in the knowledge base.
Each tool is self-contained with its own metadata and implementation.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.core.events import EventType

from ._event_publisher import publish_kb_file_event
from .base_tool import BaseTool, ToolContext


def _validate_safe_path(kb_root_path: Path, relative_path: str) -> tuple[bool, Optional[Path], str]:
    """
    Validate that path is safe and within KB root

    Args:
        kb_root_path: Root path of knowledge base
        relative_path: Relative path from KB root

    Returns:
        Tuple of (is_valid, resolved_path, error_message)
    """
    try:
        # Remove any leading slashes to ensure it's treated as relative
        relative_path = relative_path.lstrip("/").lstrip("\\")

        # Check for path traversal attempts
        if ".." in relative_path:
            return False, None, "Path traversal (..) is not allowed"

        # Resolve full path
        full_path = (kb_root_path / relative_path).resolve()

        # Verify it's within KB root
        try:
            full_path.relative_to(kb_root_path)
        except ValueError:
            return False, None, f"Path must be within knowledge base root: {kb_root_path}"

        return True, full_path, ""

    except Exception as e:
        return False, None, f"Invalid path: {e}"


class FolderCreateTool(BaseTool):
    """Tool for creating a new folder in the knowledge base"""

    @property
    def name(self) -> str:
        return "folder_create"

    @property
    def description(self) -> str:
        return "Создать папку в базе знаний"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        }

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Create a new folder"""
        relative_path = params.get("path", "")

        # Validate path
        is_valid, full_path, error = _validate_safe_path(context.kb_root_path, relative_path)
        if not is_valid or full_path is None:
            logger.error(f"[folder_create] Path validation failed: {error}")
            return {"success": False, "error": error}

        try:
            # Check if already exists
            if full_path.exists():
                if full_path.is_dir():
                    error_msg = f"Folder already exists: {relative_path}"
                    logger.warning(f"[folder_create] {error_msg}")
                    return {"success": False, "error": error_msg}
                else:
                    error_msg = f"Path exists but is not a folder: {relative_path}"
                    logger.warning(f"[folder_create] {error_msg}")
                    return {"success": False, "error": error_msg}

            # Create folder
            full_path.mkdir(parents=True, exist_ok=False)

            logger.info(f"[folder_create] ✓ Created folder: {relative_path}")
            
            # Publish KB change event
            publish_kb_file_event(
                EventType.KB_FOLDER_CREATED,
                full_path,
                user_id=context.user_id,
                source="folder_create_tool"
            )
            
            return {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "message": f"Folder created successfully: {relative_path}",
            }

        except Exception as e:
            logger.error(f"[folder_create] Failed to create folder: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to create folder: {e}"}


class FolderDeleteTool(BaseTool):
    """Tool for deleting a folder and its contents"""

    @property
    def name(self) -> str:
        return "folder_delete"

    @property
    def description(self) -> str:
        return "Удалить папку и её содержимое"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        }

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Delete a folder and its contents"""
        relative_path = params.get("path", "")

        # Validate path
        is_valid, full_path, error = _validate_safe_path(context.kb_root_path, relative_path)
        if not is_valid or full_path is None:
            logger.error(f"[folder_delete] Path validation failed: {error}")
            return {"success": False, "error": error}

        try:
            # Check if exists
            if not full_path.exists():
                error_msg = f"Folder does not exist: {relative_path}"
                logger.warning(f"[folder_delete] {error_msg}")
                return {"success": False, "error": error_msg}

            if not full_path.is_dir():
                error_msg = f"Path is not a folder: {relative_path}"
                logger.warning(f"[folder_delete] {error_msg}")
                return {"success": False, "error": error_msg}

            # Prevent deleting KB root itself
            if full_path == context.kb_root_path:
                error_msg = "Cannot delete knowledge base root folder"
                logger.error(f"[folder_delete] {error_msg}")
                return {"success": False, "error": error_msg}

            # Delete folder and contents
            shutil.rmtree(full_path)

            logger.info(f"[folder_delete] ✓ Deleted folder: {relative_path}")
            
            # Publish KB change event
            publish_kb_file_event(
                EventType.KB_FOLDER_DELETED,
                full_path,
                user_id=context.user_id,
                source="folder_delete_tool"
            )
            
            return {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "message": f"Folder deleted successfully: {relative_path}",
            }

        except Exception as e:
            logger.error(f"[folder_delete] Failed to delete folder: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to delete folder: {e}"}


class FolderMoveTool(BaseTool):
    """Tool for moving/renaming a folder"""

    @property
    def name(self) -> str:
        return "folder_move"

    @property
    def description(self) -> str:
        return "Переместить/переименовать папку"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
        }

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Move/rename a folder"""
        source_path = params.get("source", "")
        dest_path = params.get("destination", "")

        # Validate source path
        is_valid, full_source, error = _validate_safe_path(context.kb_root_path, source_path)
        if not is_valid or full_source is None:
            logger.error(f"[folder_move] Invalid source: {error}")
            return {"success": False, "error": f"Invalid source: {error}"}

        # Validate destination path
        is_valid, full_dest, error = _validate_safe_path(context.kb_root_path, dest_path)
        if not is_valid or full_dest is None:
            logger.error(f"[folder_move] Invalid destination: {error}")
            return {"success": False, "error": f"Invalid destination: {error}"}

        try:
            # Check if source exists
            if not full_source.exists():
                error_msg = f"Source folder does not exist: {source_path}"
                logger.warning(f"[folder_move] {error_msg}")
                return {"success": False, "error": error_msg}

            if not full_source.is_dir():
                error_msg = f"Source is not a folder: {source_path}"
                logger.warning(f"[folder_move] {error_msg}")
                return {"success": False, "error": error_msg}

            # Prevent moving KB root itself
            if full_source == context.kb_root_path:
                error_msg = "Cannot move knowledge base root folder"
                logger.error(f"[folder_move] {error_msg}")
                return {"success": False, "error": error_msg}

            # Check if destination already exists
            if full_dest.exists():
                error_msg = f"Destination already exists: {dest_path}"
                logger.warning(f"[folder_move] {error_msg}")
                return {"success": False, "error": error_msg}

            # Create parent directories if needed
            full_dest.parent.mkdir(parents=True, exist_ok=True)

            # Move folder
            shutil.move(str(full_source), str(full_dest))

            logger.info(f"[folder_move] ✓ Moved folder: {source_path} → {dest_path}")
            return {
                "success": True,
                "source": source_path,
                "destination": dest_path,
                "full_source": str(full_source),
                "full_destination": str(full_dest),
                "message": f"Folder moved successfully: {source_path} → {dest_path}",
            }

        except Exception as e:
            logger.error(f"[folder_move] Failed to move folder: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to move folder: {e}"}


# Export all folder tools
ALL_TOOLS = [
    FolderCreateTool(),
    FolderDeleteTool(),
    FolderMoveTool(),
]
