"""
Knowledge Base reading tools for autonomous agent.

Tools for reading files, listing directories, and searching content in the knowledge base.
Each tool is self-contained with its own metadata and implementation.
"""

import glob
import fnmatch
from pathlib import Path
from typing import Any, Dict, Optional, List
from loguru import logger

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


class KBReadFileTool(BaseTool):
    """Tool for reading one or multiple files from knowledge base"""
    
    @property
    def name(self) -> str:
        return "kb_read_file"
    
    @property
    def description(self) -> str:
        return "Прочитать один или несколько файлов из базы знаний"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Список относительных путей к файлам",
                }
            },
            "required": ["paths"],
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Read one or multiple files from knowledge base"""
        paths = params.get("paths", [])
        
        if not paths:
            logger.error("[kb_read_file] No paths provided")
            return {"success": False, "error": "No paths provided"}
        
        if not isinstance(paths, list):
            paths = [paths]
        
        results = []
        errors = []
        
        for relative_path in paths:
            # Validate path
            is_valid, full_path, error = _validate_safe_path(context.kb_root_path, relative_path)
            if not is_valid:
                logger.warning(f"[kb_read_file] Invalid path: {relative_path} - {error}")
                errors.append({"path": relative_path, "error": error})
                continue
            
            try:
                # Check if file exists
                if not full_path.exists():
                    errors.append({"path": relative_path, "error": "File does not exist"})
                    continue
                
                if not full_path.is_file():
                    errors.append({"path": relative_path, "error": "Path is not a file"})
                    continue
                
                # Read file content
                content = full_path.read_text(encoding="utf-8")
                
                results.append({
                    "path": relative_path,
                    "full_path": str(full_path),
                    "content": content,
                    "size": len(content)
                })
                
                logger.info(f"[kb_read_file] ✓ Read file: {relative_path} ({len(content)} bytes)")
                
            except Exception as e:
                logger.error(f"[kb_read_file] Failed to read {relative_path}: {e}", exc_info=True)
                errors.append({"path": relative_path, "error": str(e)})
        
        return {
            "success": len(results) > 0,
            "files_read": len(results),
            "results": results,
            "errors": errors if errors else None
        }


class KBListDirectoryTool(BaseTool):
    """Tool for listing contents of a directory in knowledge base"""
    
    @property
    def name(self) -> str:
        return "kb_list_directory"
    
    @property
    def description(self) -> str:
        return "Перечислить содержимое папки в базе знаний"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Относительный путь к папке. Пустая строка для корня.",
                },
                "recursive": {"type": "boolean"},
            },
            "required": ["path"],
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """List contents of a directory in knowledge base"""
        relative_path = params.get("path", "")
        recursive = params.get("recursive", False)
        
        # Validate path
        is_valid, full_path, error = _validate_safe_path(
            context.kb_root_path, 
            relative_path if relative_path else "."
        )
        if not is_valid:
            logger.error(f"[kb_list_directory] Invalid path: {error}")
            return {"success": False, "error": error}
        
        try:
            # Check if directory exists
            if not full_path.exists():
                error_msg = f"Directory does not exist: {relative_path}"
                logger.warning(f"[kb_list_directory] {error_msg}")
                return {"success": False, "error": error_msg}
            
            if not full_path.is_dir():
                error_msg = f"Path is not a directory: {relative_path}"
                logger.warning(f"[kb_list_directory] {error_msg}")
                return {"success": False, "error": error_msg}
            
            files = []
            directories = []
            
            if recursive:
                # Recursive listing
                for item in full_path.rglob("*"):
                    rel_path = str(item.relative_to(context.kb_root_path))
                    if item.is_file():
                        files.append({
                            "path": rel_path,
                            "name": item.name,
                            "size": item.stat().st_size
                        })
                    elif item.is_dir():
                        directories.append({
                            "path": rel_path,
                            "name": item.name
                        })
            else:
                # Non-recursive listing
                for item in full_path.iterdir():
                    rel_path = str(item.relative_to(context.kb_root_path))
                    if item.is_file():
                        files.append({
                            "path": rel_path,
                            "name": item.name,
                            "size": item.stat().st_size
                        })
                    elif item.is_dir():
                        directories.append({
                            "path": rel_path,
                            "name": item.name
                        })
            
            logger.info(f"[kb_list_directory] ✓ Listed {relative_path or 'root'}: {len(files)} files, {len(directories)} directories")
            
            return {
                "success": True,
                "path": relative_path or "root",
                "recursive": recursive,
                "files": files,
                "directories": directories,
                "file_count": len(files),
                "directory_count": len(directories)
            }
            
        except Exception as e:
            logger.error(f"[kb_list_directory] Failed to list directory: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to list directory: {e}"}


class KBSearchFilesTool(BaseTool):
    """Tool for searching files and directories by name or pattern"""
    
    @property
    def name(self) -> str:
        return "kb_search_files"
    
    @property
    def description(self) -> str:
        return "Поиск файлов и папок по названию или шаблону"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "case_sensitive": {"type": "boolean"},
            },
            "required": ["pattern"],
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Search files and directories by name or pattern"""
        pattern = params.get("pattern", "")
        case_sensitive = params.get("case_sensitive", False)
        
        if not pattern:
            logger.error("[kb_search_files] No pattern provided")
            return {"success": False, "error": "No pattern provided"}
        
        try:
            files = []
            directories = []
            
            # Use glob for pattern matching
            glob_pattern = str(context.kb_root_path / pattern)
            
            for match in glob.glob(glob_pattern, recursive=True):
                match_path = Path(match)
                
                # Verify it's within KB root
                try:
                    rel_path = str(match_path.relative_to(context.kb_root_path))
                except ValueError:
                    continue
                
                if match_path.is_file():
                    files.append({
                        "path": rel_path,
                        "name": match_path.name,
                        "size": match_path.stat().st_size
                    })
                elif match_path.is_dir():
                    directories.append({
                        "path": rel_path,
                        "name": match_path.name
                    })
            
            # If glob didn't work well, try fnmatch on all files
            if not files and not directories:
                for item in context.kb_root_path.rglob("*"):
                    rel_path = str(item.relative_to(context.kb_root_path))
                    
                    # Match against full path or just name
                    if case_sensitive:
                        matches = fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(item.name, pattern)
                    else:
                        matches = (fnmatch.fnmatch(rel_path.lower(), pattern.lower()) or 
                                 fnmatch.fnmatch(item.name.lower(), pattern.lower()))
                    
                    if matches:
                        if item.is_file():
                            files.append({
                                "path": rel_path,
                                "name": item.name,
                                "size": item.stat().st_size
                            })
                        elif item.is_dir():
                            directories.append({
                                "path": rel_path,
                                "name": item.name
                            })
            
            logger.info(f"[kb_search_files] ✓ Pattern '{pattern}': found {len(files)} files, {len(directories)} directories")
            
            return {
                "success": True,
                "pattern": pattern,
                "case_sensitive": case_sensitive,
                "files": files,
                "directories": directories,
                "file_count": len(files),
                "directory_count": len(directories)
            }
            
        except Exception as e:
            logger.error(f"[kb_search_files] Failed to search: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to search files: {e}"}


class KBSearchContentTool(BaseTool):
    """Tool for searching by file contents in knowledge base"""
    
    @property
    def name(self) -> str:
        return "kb_search_content"
    
    @property
    def description(self) -> str:
        return "Поиск по содержимому файлов в базе знаний"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "case_sensitive": {"type": "boolean"},
                "file_pattern": {"type": "string"},
            },
            "required": ["query"],
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Search by file contents in knowledge base"""
        query = params.get("query", "")
        case_sensitive = params.get("case_sensitive", False)
        file_pattern = params.get("file_pattern", "*.md")
        
        if not query:
            logger.error("[kb_search_content] No query provided")
            return {"success": False, "error": "No query provided"}
        
        try:
            matches = []
            
            # Get all files matching the pattern
            if file_pattern:
                glob_pattern = str(context.kb_root_path / "**" / file_pattern)
                files_to_search = glob.glob(glob_pattern, recursive=True)
            else:
                files_to_search = [str(f) for f in context.kb_root_path.rglob("*") if f.is_file()]
            
            # Search in each file
            for file_path_str in files_to_search:
                file_path = Path(file_path_str)
                
                # Verify it's within KB root
                try:
                    rel_path = str(file_path.relative_to(context.kb_root_path))
                except ValueError:
                    continue
                
                if not file_path.is_file():
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    
                    # Search for query in content
                    search_content = content if case_sensitive else content.lower()
                    search_query = query if case_sensitive else query.lower()
                    
                    if search_query in search_content:
                        # Find all occurrences and their line numbers
                        lines = content.split("\n")
                        occurrences = []
                        
                        for line_num, line in enumerate(lines, 1):
                            search_line = line if case_sensitive else line.lower()
                            if search_query in search_line:
                                # Get context (line before and after)
                                context_start = max(0, line_num - 2)
                                context_end = min(len(lines), line_num + 1)
                                context_lines = lines[context_start:context_end]
                                
                                occurrences.append({
                                    "line_number": line_num,
                                    "line": line.strip(),
                                    "context": "\n".join(context_lines)
                                })
                        
                        matches.append({
                            "path": rel_path,
                            "name": file_path.name,
                            "occurrences": len(occurrences),
                            "matches": occurrences[:5]  # Limit to first 5 matches per file
                        })
                
                except Exception as e:
                    logger.debug(f"[kb_search_content] Failed to read {rel_path}: {e}")
                    continue
            
            logger.info(f"[kb_search_content] ✓ Query '{query}': found in {len(matches)} files")
            
            return {
                "success": True,
                "query": query,
                "case_sensitive": case_sensitive,
                "file_pattern": file_pattern,
                "matches": matches,
                "files_found": len(matches)
            }
            
        except Exception as e:
            logger.error(f"[kb_search_content] Failed to search content: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to search content: {e}"}


# Export all KB reading tools
ALL_TOOLS = [
    KBReadFileTool(),
    KBListDirectoryTool(),
    KBSearchFilesTool(),
    KBSearchContentTool(),
]
