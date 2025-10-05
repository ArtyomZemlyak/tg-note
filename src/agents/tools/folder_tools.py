"""
Folder management tools for autonomous agent
Handles folder creation, deletion, and moving
"""

import shutil
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


async def tool_folder_create(
    params: Dict[str, Any],
    kb_root_path: Path
) -> Dict[str, Any]:
    """
    Create a new folder
    
    Args:
        params: Tool parameters with 'path' field
        kb_root_path: Root path of knowledge base
        
    Returns:
        Dict with folder creation result
    """
    relative_path = params.get("path", "")
    
    # Validate path
    is_valid, full_path, error = _validate_safe_path(kb_root_path, relative_path)
    if not is_valid:
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
        return {
            "success": True,
            "path": relative_path,
            "full_path": str(full_path),
            "message": f"Folder created successfully: {relative_path}"
        }
        
    except Exception as e:
        logger.error(f"[folder_create] Failed to create folder: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to create folder: {e}"}


async def tool_folder_delete(
    params: Dict[str, Any],
    kb_root_path: Path
) -> Dict[str, Any]:
    """
    Delete a folder and its contents
    
    Args:
        params: Tool parameters with 'path' field
        kb_root_path: Root path of knowledge base
        
    Returns:
        Dict with folder deletion result
    """
    relative_path = params.get("path", "")
    
    # Validate path
    is_valid, full_path, error = _validate_safe_path(kb_root_path, relative_path)
    if not is_valid:
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
        if full_path == kb_root_path:
            error_msg = "Cannot delete knowledge base root folder"
            logger.error(f"[folder_delete] {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Delete folder and contents
        shutil.rmtree(full_path)
        
        logger.info(f"[folder_delete] ✓ Deleted folder: {relative_path}")
        return {
            "success": True,
            "path": relative_path,
            "full_path": str(full_path),
            "message": f"Folder deleted successfully: {relative_path}"
        }
        
    except Exception as e:
        logger.error(f"[folder_delete] Failed to delete folder: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to delete folder: {e}"}


async def tool_folder_move(
    params: Dict[str, Any],
    kb_root_path: Path
) -> Dict[str, Any]:
    """
    Move/rename a folder
    
    Args:
        params: Tool parameters with 'source' and 'destination' fields
        kb_root_path: Root path of knowledge base
        
    Returns:
        Dict with folder move result
    """
    source_path = params.get("source", "")
    dest_path = params.get("destination", "")
    
    # Validate source path
    is_valid, full_source, error = _validate_safe_path(kb_root_path, source_path)
    if not is_valid:
        logger.error(f"[folder_move] Invalid source: {error}")
        return {"success": False, "error": f"Invalid source: {error}"}
    
    # Validate destination path
    is_valid, full_dest, error = _validate_safe_path(kb_root_path, dest_path)
    if not is_valid:
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
        if full_source == kb_root_path:
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
            "message": f"Folder moved successfully: {source_path} → {dest_path}"
        }
        
    except Exception as e:
        logger.error(f"[folder_move] Failed to move folder: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to move folder: {e}"}
