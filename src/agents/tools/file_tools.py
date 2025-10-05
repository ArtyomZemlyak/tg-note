"""
File management tools for autonomous agent
Handles file creation, editing, deletion, and moving
"""

from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


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


async def tool_file_create(
    params: Dict[str, Any],
    kb_root_path: Path
) -> Dict[str, Any]:
    """
    Create a new file
    
    Args:
        params: Tool parameters with 'path' and 'content' fields
        kb_root_path: Root path of knowledge base
        
    Returns:
        Dict with file creation result
    """
    relative_path = params.get("path", "")
    content = params.get("content", "")
    
    # Validate path
    is_valid, full_path, error = _validate_safe_path(kb_root_path, relative_path)
    if not is_valid:
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
        return {
            "success": True,
            "path": relative_path,
            "full_path": str(full_path),
            "size": len(content),
            "message": f"File created successfully: {relative_path}"
        }
        
    except Exception as e:
        logger.error(f"[file_create] Failed to create file: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to create file: {e}"}


async def tool_file_edit(
    params: Dict[str, Any],
    kb_root_path: Path
) -> Dict[str, Any]:
    """
    Edit an existing file
    
    Args:
        params: Tool parameters with 'path' and 'content' fields
        kb_root_path: Root path of knowledge base
        
    Returns:
        Dict with file editing result
    """
    relative_path = params.get("path", "")
    content = params.get("content", "")
    
    # Validate path
    is_valid, full_path, error = _validate_safe_path(kb_root_path, relative_path)
    if not is_valid:
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
        
        logger.info(f"[file_edit] ✓ Edited file: {relative_path} ({len(old_content)} → {len(content)} bytes)")
        return {
            "success": True,
            "path": relative_path,
            "full_path": str(full_path),
            "old_size": len(old_content),
            "new_size": len(content),
            "message": f"File edited successfully: {relative_path}"
        }
        
    except Exception as e:
        logger.error(f"[file_edit] Failed to edit file: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to edit file: {e}"}


async def tool_file_delete(
    params: Dict[str, Any],
    kb_root_path: Path
) -> Dict[str, Any]:
    """
    Delete a file
    
    Args:
        params: Tool parameters with 'path' field
        kb_root_path: Root path of knowledge base
        
    Returns:
        Dict with file deletion result
    """
    relative_path = params.get("path", "")
    
    # Validate path
    is_valid, full_path, error = _validate_safe_path(kb_root_path, relative_path)
    if not is_valid:
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
        return {
            "success": True,
            "path": relative_path,
            "full_path": str(full_path),
            "message": f"File deleted successfully: {relative_path}"
        }
        
    except Exception as e:
        logger.error(f"[file_delete] Failed to delete file: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to delete file: {e}"}


async def tool_file_move(
    params: Dict[str, Any],
    kb_root_path: Path
) -> Dict[str, Any]:
    """
    Move/rename a file
    
    Args:
        params: Tool parameters with 'source' and 'destination' fields
        kb_root_path: Root path of knowledge base
        
    Returns:
        Dict with file move result
    """
    source_path = params.get("source", "")
    dest_path = params.get("destination", "")
    
    # Validate source path
    is_valid, full_source, error = _validate_safe_path(kb_root_path, source_path)
    if not is_valid:
        logger.error(f"[file_move] Invalid source: {error}")
        return {"success": False, "error": f"Invalid source: {error}"}
    
    # Validate destination path
    is_valid, full_dest, error = _validate_safe_path(kb_root_path, dest_path)
    if not is_valid:
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
        return {
            "success": True,
            "source": source_path,
            "destination": dest_path,
            "full_source": str(full_source),
            "full_destination": str(full_dest),
            "message": f"File moved successfully: {source_path} → {dest_path}"
        }
        
    except Exception as e:
        logger.error(f"[file_move] Failed to move file: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to move file: {e}"}
