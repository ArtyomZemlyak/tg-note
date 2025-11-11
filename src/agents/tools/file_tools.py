"""
File management tools for autonomous agent.

Tools for creating, editing, deleting, and moving files in the knowledge base.
Each tool is self-contained with its own metadata and implementation.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.core.events import EventType
from src.processor.markdown_image_validator import validate_agent_generated_markdown

from ._event_publisher import publish_kb_batch_event, publish_kb_file_event
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


class FileCreateTool(BaseTool):
    """Tool for creating a new file in the knowledge base"""

    @property
    def name(self) -> str:
        return "file_create"

    @property
    def description(self) -> str:
        return "Создать файл в базе знаний"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Create a new file"""
        relative_path = params.get("path", "")
        content = params.get("content", "")

        # Validate path
        is_valid, full_path, error = _validate_safe_path(context.kb_root_path, relative_path)
        if not is_valid or full_path is None:
            logger.error(f"[file_create] Path validation failed: {error}")
            return {"success": False, "error": error}

        try:
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file already exists
            if full_path.exists():
                error_msg = f"File already exists: {relative_path}"
                logger.warning(f"[file_create] {error_msg}")
                return {"success": False, "error": error_msg}

            # Write file
            full_path.write_text(content, encoding="utf-8")

            logger.info(f"[file_create] ✓ Created file: {relative_path} ({len(content)} bytes)")

            # AICODE-NOTE: Validate image paths in markdown files
            validation_passed = True
            validation_warnings = []
            if full_path.suffix.lower() == ".md":
                try:
                    validation_passed = validate_agent_generated_markdown(
                        full_path, context.kb_root_path
                    )
                    if not validation_passed:
                        validation_warnings.append(
                            "Image path validation failed - some images may not display correctly"
                        )
                except Exception as e:
                    logger.warning(f"[file_create] Image validation error: {e}")
                    validation_warnings.append(f"Image validation error: {e}")

            # Publish KB change event
            publish_kb_file_event(
                EventType.KB_FILE_CREATED,
                full_path,
                user_id=context.user_id,
                source="file_create_tool",
            )

            result = {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "size": len(content),
                "message": f"File created successfully: {relative_path}",
            }

            if validation_warnings:
                result["validation_warnings"] = validation_warnings
                result["validation_passed"] = validation_passed

            return result

        except Exception as e:
            logger.error(f"[file_create] Failed to create file: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to create file: {e}"}


class FileEditTool(BaseTool):
    """Tool for editing an existing file"""

    @property
    def name(self) -> str:
        return "file_edit"

    @property
    def description(self) -> str:
        return "Редактировать существующий файл"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Edit an existing file"""
        relative_path = params.get("path", "")
        content = params.get("content", "")

        # Validate path
        is_valid, full_path, error = _validate_safe_path(context.kb_root_path, relative_path)
        if not is_valid or full_path is None:
            logger.error(f"[file_edit] Path validation failed: {error}")
            return {"success": False, "error": error}

        try:
            # Check if file exists
            if not full_path.exists():
                error_msg = f"File does not exist: {relative_path}"
                logger.warning(f"[file_edit] {error_msg}")
                return {"success": False, "error": error_msg}

            if not full_path.is_file():
                error_msg = f"Path is not a file: {relative_path}"
                logger.warning(f"[file_edit] {error_msg}")
                return {"success": False, "error": error_msg}

            # Backup old content
            old_content = full_path.read_text(encoding="utf-8")

            # Write new content
            full_path.write_text(content, encoding="utf-8")

            logger.info(
                f"[file_edit] ✓ Edited file: {relative_path} ({len(old_content)} → {len(content)} bytes)"
            )

            # AICODE-NOTE: Validate image paths in markdown files
            validation_passed = True
            validation_warnings = []
            if full_path.suffix.lower() == ".md":
                try:
                    validation_passed = validate_agent_generated_markdown(
                        full_path, context.kb_root_path
                    )
                    if not validation_passed:
                        validation_warnings.append(
                            "Image path validation failed - some images may not display correctly"
                        )
                except Exception as e:
                    logger.warning(f"[file_edit] Image validation error: {e}")
                    validation_warnings.append(f"Image validation error: {e}")

            # Publish KB change event
            publish_kb_file_event(
                EventType.KB_FILE_MODIFIED,
                full_path,
                user_id=context.user_id,
                source="file_edit_tool",
            )

            result = {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "old_size": len(old_content),
                "new_size": len(content),
                "message": f"File edited successfully: {relative_path}",
            }

            if validation_warnings:
                result["validation_warnings"] = validation_warnings
                result["validation_passed"] = validation_passed

            return result

        except Exception as e:
            logger.error(f"[file_edit] Failed to edit file: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to edit file: {e}"}


class FileDeleteTool(BaseTool):
    """Tool for deleting a file"""

    @property
    def name(self) -> str:
        return "file_delete"

    @property
    def description(self) -> str:
        return "Удалить файл из базы знаний"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        }

    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Delete a file"""
        relative_path = params.get("path", "")

        # Validate path
        is_valid, full_path, error = _validate_safe_path(context.kb_root_path, relative_path)
        if not is_valid or full_path is None:
            logger.error(f"[file_delete] Path validation failed: {error}")
            return {"success": False, "error": error}

        try:
            # Check if file exists
            if not full_path.exists():
                error_msg = f"File does not exist: {relative_path}"
                logger.warning(f"[file_delete] {error_msg}")
                return {"success": False, "error": error_msg}

            if not full_path.is_file():
                error_msg = f"Path is not a file: {relative_path}"
                logger.warning(f"[file_delete] {error_msg}")
                return {"success": False, "error": error_msg}

            # Delete file
            full_path.unlink()

            logger.info(f"[file_delete] ✓ Deleted file: {relative_path}")

            # Publish KB change event
            publish_kb_file_event(
                EventType.KB_FILE_DELETED,
                full_path,
                user_id=context.user_id,
                source="file_delete_tool",
            )

            return {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "message": f"File deleted successfully: {relative_path}",
            }

        except Exception as e:
            logger.error(f"[file_delete] Failed to delete file: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to delete file: {e}"}


class FileMoveTool(BaseTool):
    """Tool for moving/renaming a file"""

    @property
    def name(self) -> str:
        return "file_move"

    @property
    def description(self) -> str:
        return "Переместить/переименовать файл"

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
        """Move/rename a file"""
        source_path = params.get("source", "")
        dest_path = params.get("destination", "")

        # Validate source path
        is_valid, full_source, error = _validate_safe_path(context.kb_root_path, source_path)
        if not is_valid or full_source is None:
            logger.error(f"[file_move] Invalid source: {error}")
            return {"success": False, "error": f"Invalid source: {error}"}

        # Validate destination path
        is_valid, full_dest, error = _validate_safe_path(context.kb_root_path, dest_path)
        if not is_valid or full_dest is None:
            logger.error(f"[file_move] Invalid destination: {error}")
            return {"success": False, "error": f"Invalid destination: {error}"}

        try:
            # Check if source exists
            if not full_source.exists():
                error_msg = f"Source file does not exist: {source_path}"
                logger.warning(f"[file_move] {error_msg}")
                return {"success": False, "error": error_msg}

            if not full_source.is_file():
                error_msg = f"Source is not a file: {source_path}"
                logger.warning(f"[file_move] {error_msg}")
                return {"success": False, "error": error_msg}

            # Check if destination already exists
            if full_dest.exists():
                error_msg = f"Destination already exists: {dest_path}"
                logger.warning(f"[file_move] {error_msg}")
                return {"success": False, "error": error_msg}

            # Create parent directories if needed
            full_dest.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            full_source.rename(full_dest)

            logger.info(f"[file_move] ✓ Moved file: {source_path} → {dest_path}")

            # Publish KB change events (delete old + create new)
            publish_kb_batch_event(
                files=[full_source, full_dest], user_id=context.user_id, source="file_move_tool"
            )

            return {
                "success": True,
                "source": source_path,
                "destination": dest_path,
                "full_source": str(full_source),
                "full_destination": str(full_dest),
                "message": f"File moved successfully: {source_path} → {dest_path}",
            }

        except Exception as e:
            logger.error(f"[file_move] Failed to move file: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to move file: {e}"}


# Export all file tools
ALL_TOOLS = [
    FileCreateTool(),
    FileEditTool(),
    FileDeleteTool(),
    FileMoveTool(),
]
