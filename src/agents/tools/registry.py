"""
Tool registry and manager for autonomous agents.

Provides a unified Tool interface, contextual dependency injection,
OpenAI-compatible tool schemas, and a single execution entrypoint.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger

# Import existing tool functions (logic remains in their modules)
from .planning_tools import tool_plan_todo, tool_analyze_content
from .kb_reading_tools import (
    tool_kb_read_file,
    tool_kb_list_directory,
    tool_kb_search_files,
    tool_kb_search_content,
)
from .vector_search_tools import tool_kb_vector_search, tool_kb_reindex_vector
from .web_tools import tool_web_search
from .git_tools import tool_git_command
from .github_tools import tool_github_api
from .shell_tools import tool_shell_command
from .file_tools import (
    tool_file_create,
    tool_file_edit,
    tool_file_delete,
    tool_file_move,
)
from .folder_tools import (
    tool_folder_create,
    tool_folder_delete,
    tool_folder_move,
)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters_schema: Dict[str, Any]

    def to_openai_function(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


@dataclass
class Tool:
    spec: ToolSpec
    runner: Callable[[Dict[str, Any], "ToolContext"], Awaitable[Dict[str, Any]]]


@dataclass
class ToolContext:
    kb_root_path: Path
    base_agent_class: Any
    github_token: Optional[str] = None
    enable_shell: bool = False
    vector_search_manager: Optional[Any] = None
    # Optional callbacks for agent-owned state (e.g., plan)
    get_current_plan: Optional[Callable[[], Any]] = None
    set_current_plan: Optional[Callable[[Any], None]] = None


class ToolManager:
    def __init__(self, context: ToolContext):
        self._context = context
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool
        logger.debug(f"[ToolManager] Registered tool: {tool.spec.name}")

    def register_many(self, tools: List[Tool]) -> None:
        for t in tools:
            self.register(t)

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def build_llm_tools_schema(self) -> List[Dict[str, Any]]:
        return [t.spec.to_openai_function() for t in self._tools.values()]

    async def execute(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return {"success": False, "error": f"Tool not found: {name}"}
        return await self._tools[name].runner(params, self._context)


# ----------------------------------------------------------------------------
# Factory for default tools set
# ----------------------------------------------------------------------------

def _plan_todo_tool() -> Tool:
    spec = ToolSpec(
        name="plan_todo",
        description="Создать план действий (TODO список). ОБЯЗАТЕЛЬНО вызови первым!",
        parameters_schema={
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Список задач для выполнения",
                }
            },
            "required": ["tasks"],
        },
    )

    async def runner(params: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        current_plan = ctx.get_current_plan() if ctx.get_current_plan else None
        result, new_plan = await tool_plan_todo(params, current_plan, ctx.base_agent_class)
        if ctx.set_current_plan:
            ctx.set_current_plan(new_plan)
        return result

    return Tool(spec=spec, runner=runner)


def _analyze_content_tool() -> Tool:
    spec = ToolSpec(
        name="analyze_content",
        description="Анализировать контент и извлечь ключевую информацию",
        parameters_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Текст для анализа"}
            },
            "required": ["text"],
        },
    )

    async def runner(params: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        return await tool_analyze_content(params, ctx.base_agent_class)

    return Tool(spec=spec, runner=runner)


def _kb_tools() -> List[Tool]:
    tools: List[Tool] = []

    tools.append(
        Tool(
            ToolSpec(
                name="kb_read_file",
                description="Прочитать один или несколько файлов из базы знаний",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список относительных путей к файлам",
                        }
                    },
                    "required": ["paths"],
                },
            ),
            runner=lambda params, ctx: tool_kb_read_file(params, ctx.kb_root_path),
        )
    )

    tools.append(
        Tool(
            ToolSpec(
                name="kb_list_directory",
                description="Перечислить содержимое папки в базе знаний",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Относительный путь к папке. Пустая строка для корня.",
                        },
                        "recursive": {"type": "boolean"},
                    },
                    "required": ["path"],
                },
            ),
            runner=lambda params, ctx: tool_kb_list_directory(params, ctx.kb_root_path),
        )
    )

    tools.append(
        Tool(
            ToolSpec(
                name="kb_search_files",
                description="Поиск файлов и папок по названию или шаблону",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "case_sensitive": {"type": "boolean"},
                    },
                    "required": ["pattern"],
                },
            ),
            runner=lambda params, ctx: tool_kb_search_files(params, ctx.kb_root_path),
        )
    )

    tools.append(
        Tool(
            ToolSpec(
                name="kb_search_content",
                description="Поиск по содержимому файлов в базе знаний",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "case_sensitive": {"type": "boolean"},
                        "file_pattern": {"type": "string"},
                    },
                    "required": ["query"],
                },
            ),
            runner=lambda params, ctx: tool_kb_search_content(params, ctx.kb_root_path),
        )
    )

    return tools


def _file_tools() -> List[Tool]:
    return [
        Tool(
            ToolSpec(
                name="file_create",
                description="Создать файл в базе знаний",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            ),
            runner=lambda params, ctx: tool_file_create(params, ctx.kb_root_path),
        ),
        Tool(
            ToolSpec(
                name="file_edit",
                description="Редактировать существующий файл",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            ),
            runner=lambda params, ctx: tool_file_edit(params, ctx.kb_root_path),
        ),
        Tool(
            ToolSpec(
                name="file_delete",
                description="Удалить файл из базы знаний",
                parameters_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            runner=lambda params, ctx: tool_file_delete(params, ctx.kb_root_path),
        ),
        Tool(
            ToolSpec(
                name="file_move",
                description="Переместить/переименовать файл",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "destination": {"type": "string"},
                    },
                    "required": ["source", "destination"],
                },
            ),
            runner=lambda params, ctx: tool_file_move(params, ctx.kb_root_path),
        ),
    ]


def _folder_tools() -> List[Tool]:
    return [
        Tool(
            ToolSpec(
                name="folder_create",
                description="Создать папку в базе знаний",
                parameters_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            runner=lambda params, ctx: tool_folder_create(params, ctx.kb_root_path),
        ),
        Tool(
            ToolSpec(
                name="folder_delete",
                description="Удалить папку и её содержимое",
                parameters_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            runner=lambda params, ctx: tool_folder_delete(params, ctx.kb_root_path),
        ),
        Tool(
            ToolSpec(
                name="folder_move",
                description="Переместить/переименовать папку",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "destination": {"type": "string"},
                    },
                    "required": ["source", "destination"],
                },
            ),
            runner=lambda params, ctx: tool_folder_move(params, ctx.kb_root_path),
        ),
    ]


def _web_git_github_shell_tools() -> List[Tool]:
    return [
        Tool(
            ToolSpec(
                name="web_search",
                description="Поиск информации в интернете",
                parameters_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
            runner=lambda params, ctx: tool_web_search(params),
        ),
        Tool(
            ToolSpec(
                name="git_command",
                description="Выполнить безопасную git-команду",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"},
                    },
                    "required": ["command"],
                },
            ),
            runner=lambda params, ctx: tool_git_command(params),
        ),
        Tool(
            ToolSpec(
                name="github_api",
                description="Вызов GitHub API",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string"},
                        "method": {"type": "string"},
                        "data": {"type": "object"},
                    },
                    "required": ["endpoint"],
                },
            ),
            runner=lambda params, ctx: tool_github_api(params, ctx.github_token),
        ),
        Tool(
            ToolSpec(
                name="shell_command",
                description="Выполнить shell-команду (по умолчанию отключено)",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"},
                    },
                    "required": ["command"],
                },
            ),
            runner=lambda params, ctx: tool_shell_command(params, ctx.enable_shell),
        ),
    ]


def _vector_tools() -> List[Tool]:
    return [
        Tool(
            ToolSpec(
                name="kb_vector_search",
                description="Семантический векторный поиск по базе знаний",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            ),
            runner=lambda params, ctx: tool_kb_vector_search(params, ctx.vector_search_manager),
        ),
        Tool(
            ToolSpec(
                name="kb_reindex_vector",
                description="Переиндексировать базу знаний для векторного поиска",
                parameters_schema={
                    "type": "object",
                    "properties": {"force": {"type": "boolean"}},
                },
            ),
            runner=lambda params, ctx: tool_kb_reindex_vector(params, ctx.vector_search_manager),
        ),
    ]


def build_default_tool_manager(
    kb_root_path: Path,
    base_agent_class: Any,
    *,
    enable_web_search: bool = True,
    enable_git: bool = True,
    enable_github: bool = True,
    enable_shell: bool = False,
    enable_file_management: bool = True,
    enable_folder_management: bool = True,
    enable_vector_search: bool = False,
    github_token: Optional[str] = None,
    vector_search_manager: Optional[Any] = None,
    get_current_plan: Optional[Callable[[], Any]] = None,
    set_current_plan: Optional[Callable[[Any], None]] = None,
) -> ToolManager:
    """Create a ToolManager with the default toolset based on flags."""
    ctx = ToolContext(
        kb_root_path=kb_root_path,
        base_agent_class=base_agent_class,
        github_token=github_token,
        enable_shell=enable_shell,
        vector_search_manager=vector_search_manager,
        get_current_plan=get_current_plan,
        set_current_plan=set_current_plan,
    )

    manager = ToolManager(context=ctx)

    # Always-available planning tools
    manager.register_many([_plan_todo_tool(), _analyze_content_tool()])

    # KB reading tools
    manager.register_many(_kb_tools())

    # Optional categories
    if enable_web_search or enable_git or enable_github or enable_shell:
        tools = _web_git_github_shell_tools()
        if not enable_web_search:
            tools = [t for t in tools if t.spec.name != "web_search"]
        if not enable_git:
            tools = [t for t in tools if t.spec.name != "git_command"]
        if not enable_github:
            tools = [t for t in tools if t.spec.name != "github_api"]
        if not enable_shell:
            tools = [t for t in tools if t.spec.name != "shell_command"]
        manager.register_many(tools)

    if enable_file_management:
        manager.register_many(_file_tools())
    if enable_folder_management:
        manager.register_many(_folder_tools())
    if enable_vector_search:
        manager.register_many(_vector_tools())

    return manager
