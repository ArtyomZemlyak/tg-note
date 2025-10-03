"""
OpenAI Agent
Автономный агент с использованием OpenAI-compatible API и function calling
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai package not installed. OpenAIAgent will not work.")

from .autonomous_agent import (
    ActionType,
    AgentContext,
    AgentDecision,
    AutonomousAgent
)
from .base_agent import KBStructure


class OpenAIAgent(AutonomousAgent):
    """
    Автономный агент на базе OpenAI-compatible API
    
    Использует:
    - Function calling для автоматического вызова тулзов
    - OpenAI Chat Completions API
    - Совместим с Qwen, OpenRouter, и другими OpenAI-compatible API
    """
    
    def __init__(
        self,
        config: Optional[Dict] = None,
        instruction: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "qwen-max",
        max_iterations: int = 10,
        kb_root_path: Optional[Path] = None
    ):
        """
        Initialize OpenAI Agent
        
        Args:
            config: Configuration dictionary
            instruction: Agent instruction
            api_key: OpenAI API key (or compatible)
            base_url: API base URL (for compatible APIs)
            model: Model name
            max_iterations: Maximum iterations in agent loop
            kb_root_path: Path to knowledge base root directory
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required for OpenAIAgent. "
                "Install with: pip install openai"
            )
        
        super().__init__(config, instruction, max_iterations)
        
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.kb_root_path = kb_root_path or Path("./knowledge_base")
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Register built-in KB management tools
        self._register_kb_tools()
        
        logger.info(
            f"OpenAIAgent initialized with model={model}, "
            f"base_url={base_url}, kb_root_path={self.kb_root_path}"
        )
    
    def _get_default_instruction(self) -> str:
        """Get default instruction for OpenAI agent"""
        return """Ты автономный агент для обработки и сохранения информации в базу знаний.

Твоя задача:
1. Проанализировать предоставленный контент
2. Составить план действий и записать его в TODO (используй plan_todo)
3. Выполнить план, используя доступные тулзы
4. Сохранить информацию в структурированном виде В БАЗЕ ЗНАНИЙ

Доступные тулзы:
- plan_todo: Создать план действий (список задач)
- file_create: Создать файл в базе знаний (ОБЯЗАТЕЛЬНО используй для сохранения контента!)
- file_edit: Редактировать существующий файл
- folder_create: Создать папку для организации файлов

Процесс работы:
1. Сначала ОБЯЗАТЕЛЬНО создай plan_todo со списком задач
2. Проанализируй контент и определи категорию (ai, tech, science, general и т.д.)
3. При необходимости создай папку через folder_create
4. ОБЯЗАТЕЛЬНО создай файл через file_create с обработанным контентом
5. Верни финальный результат с информацией о созданных файлах

ВАЖНО:
- ВСЕ изменения базы знаний делай ТОЛЬКО через тулзы (file_create, file_edit, folder_create)
- НЕ возвращай просто markdown - ОБЯЗАТЕЛЬНО сохрани его через file_create
- Работай автономно, не задавай вопросов пользователю

Формат финального ответа должен содержать:
```agent-result
{
  "summary": "Краткое описание выполненных действий",
  "files_created": ["путь/к/файлу.md"],
  "files_edited": [],
  "folders_created": ["путь/к/папке"],
  "metadata": {"category": "категория", "tags": ["тег1", "тег2"]}
}
```
"""
    
    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Построить схему тулзов для OpenAI function calling
        
        Returns:
            List of tool definitions
        """
        tools = []
        
        # Всегда добавляем plan_todo
        tools.append({
            "type": "function",
            "function": {
                "name": "plan_todo",
                "description": "Создать план действий (TODO список). ОБЯЗАТЕЛЬНО вызови первым!",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список задач для выполнения"
                        }
                    },
                    "required": ["tasks"]
                }
            }
        })
        
        # Добавляем зарегистрированные тулзы
        for tool_name in self.tools.keys():
            # Определяем схему в зависимости от типа тулза
            if tool_name == "web_search":
                tools.append({
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Поиск информации в интернете",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Поисковый запрос или URL"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                })
            
            elif tool_name == "file_create":
                tools.append({
                    "type": "function",
                    "function": {
                        "name": "file_create",
                        "description": "Создать файл в базе знаний",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "Относительный путь к файлу (например: 'ai/neural-networks.md')"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Содержимое файла в markdown формате"
                                }
                            },
                            "required": ["path", "content"]
                        }
                    }
                })
            
            elif tool_name == "file_edit":
                tools.append({
                    "type": "function",
                    "function": {
                        "name": "file_edit",
                        "description": "Редактировать существующий файл",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "Относительный путь к файлу"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Новое содержимое файла"
                                }
                            },
                            "required": ["path", "content"]
                        }
                    }
                })
            
            elif tool_name == "folder_create":
                tools.append({
                    "type": "function",
                    "function": {
                        "name": "folder_create",
                        "description": "Создать папку в базе знаний",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "Относительный путь к папке (например: 'ai/concepts')"
                                }
                            },
                            "required": ["path"]
                        }
                    }
                })
            
            elif tool_name == "analyze_content":
                tools.append({
                    "type": "function",
                    "function": {
                        "name": "analyze_content",
                        "description": "Анализировать контент и извлечь ключевую информацию",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "Текст для анализа"
                                }
                            },
                            "required": ["text"]
                        }
                    }
                })
        
        return tools
    
    async def _make_decision(self, context: AgentContext) -> AgentDecision:
        """
        Принять решение используя OpenAI function calling
        
        Args:
            context: Current agent context
        
        Returns:
            AgentDecision
        """
        logger.debug("[OpenAIAgent] Making decision with OpenAI API")
        
        # Подготовить сообщения
        messages = [
            {
                "role": "system",
                "content": self.instruction
            },
            {
                "role": "user",
                "content": context.task
            }
        ]
        
        # Добавить историю выполнения
        if context.executions:
            history = context.get_history()
            messages.append({
                "role": "assistant",
                "content": f"История выполнения:\n{history}"
            })
        
        # Вызвать OpenAI API
        try:
            tools_schema = self._build_tools_schema()
            
            logger.debug(f"[OpenAIAgent] Calling OpenAI with {len(tools_schema)} tools")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools_schema,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Проверка function calling
            if message.tool_calls:
                tool_call = message.tool_calls[0]  # Берем первый вызов
                
                logger.info(
                    f"[OpenAIAgent] LLM decided to call tool: "
                    f"{tool_call.function.name}"
                )
                
                return AgentDecision(
                    action=ActionType.TOOL_CALL,
                    reasoning=message.content or "LLM decided to use a tool",
                    tool_name=tool_call.function.name,
                    tool_params=json.loads(tool_call.function.arguments)
                )
            
            # LLM решил завершить работу
            if message.content:
                logger.info("[OpenAIAgent] LLM decided to END")
                
                return AgentDecision(
                    action=ActionType.END,
                    reasoning="Task completed",
                    final_result=message.content
                )
            
            # Непонятный ответ
            logger.warning("[OpenAIAgent] LLM returned unclear response")
            return AgentDecision(
                action=ActionType.END,
                reasoning="Unclear response from LLM",
                final_result=await self._generate_fallback_markdown(context)
            )
        
        except Exception as e:
            logger.error(f"[OpenAIAgent] Error calling OpenAI API: {e}", exc_info=True)
            
            # Вернуть решение о завершении с ошибкой
            return AgentDecision(
                action=ActionType.END,
                reasoning=f"Error: {e}",
                final_result=await self._generate_fallback_markdown(context)
            )
    
    async def _handle_plan_todo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработать создание TODO плана
        
        Args:
            params: Parameters with 'tasks' list
        
        Returns:
            Result dictionary
        """
        tasks = params.get("tasks", [])
        
        logger.info(f"[OpenAIAgent] Created TODO plan with {len(tasks)} tasks")
        logger.debug(f"[OpenAIAgent] Tasks: {tasks}")
        
        return {
            "success": True,
            "plan": tasks,
            "message": f"План создан: {len(tasks)} задач"
        }
    
    def _register_kb_tools(self) -> None:
        """
        Регистрирует встроенные тулзы для работы с базой знаний
        """
        # Добавляем plan_todo
        self.tools["plan_todo"] = self._handle_plan_todo
        
        # Добавляем тулзы для работы с KB
        self.tools["file_create"] = self._handle_file_create
        self.tools["file_edit"] = self._handle_file_edit
        self.tools["folder_create"] = self._handle_folder_create
        
        logger.info("Registered built-in KB management tools")
    
    async def _handle_file_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать файл в базе знаний
        
        Args:
            params: Parameters with 'path' and 'content'
        
        Returns:
            Result dictionary
        """
        path = params.get("path", "")
        content = params.get("content", "")
        
        if not path:
            return {
                "success": False,
                "error": "Path is required"
            }
        
        if not content:
            return {
                "success": False,
                "error": "Content is required"
            }
        
        try:
            # Ensure path is relative and safe
            file_path = self.kb_root_path / path
            
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            file_path.write_text(content, encoding="utf-8")
            
            logger.info(f"[OpenAIAgent] Created file: {file_path}")
            
            return {
                "success": True,
                "path": str(path),
                "full_path": str(file_path),
                "message": f"File created successfully: {path}"
            }
        
        except Exception as e:
            logger.error(f"[OpenAIAgent] Error creating file: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_file_edit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Редактировать существующий файл
        
        Args:
            params: Parameters with 'path' and 'content'
        
        Returns:
            Result dictionary
        """
        path = params.get("path", "")
        content = params.get("content", "")
        
        if not path:
            return {
                "success": False,
                "error": "Path is required"
            }
        
        try:
            file_path = self.kb_root_path / path
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File does not exist: {path}"
                }
            
            # Write updated content
            file_path.write_text(content, encoding="utf-8")
            
            logger.info(f"[OpenAIAgent] Edited file: {file_path}")
            
            return {
                "success": True,
                "path": str(path),
                "message": f"File edited successfully: {path}"
            }
        
        except Exception as e:
            logger.error(f"[OpenAIAgent] Error editing file: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_folder_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать папку в базе знаний
        
        Args:
            params: Parameters with 'path'
        
        Returns:
            Result dictionary
        """
        path = params.get("path", "")
        
        if not path:
            return {
                "success": False,
                "error": "Path is required"
            }
        
        try:
            folder_path = self.kb_root_path / path
            folder_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"[OpenAIAgent] Created folder: {folder_path}")
            
            return {
                "success": True,
                "path": str(path),
                "message": f"Folder created successfully: {path}"
            }
        
        except Exception as e:
            logger.error(f"[OpenAIAgent] Error creating folder: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def register_tool(self, name: str, handler: callable) -> None:
        """
        Зарегистрировать дополнительный тулз
        
        Args:
            name: Tool name
            handler: Tool handler function
        """
        super().register_tool(name, handler)
    
    async def _determine_kb_structure(
        self,
        markdown: str,
        context: AgentContext
    ) -> KBStructure:
        """
        Определить структуру KB из выполненных действий агента
        
        Извлекает информацию из созданных файлов и метаданных
        
        Args:
            markdown: Markdown content
            context: Agent context
        
        Returns:
            KBStructure
        """
        # Попытка извлечь метаданные из ответа агента
        category = "general"
        subcategory = None
        tags = []
        
        # Парсим agent-result блок если он есть
        agent_result = self.parse_agent_response(markdown)
        if agent_result.metadata:
            category = agent_result.metadata.get("category", category)
            subcategory = agent_result.metadata.get("subcategory")
            tags = agent_result.metadata.get("tags", [])
        
        # Если не нашли в метаданных, пробуем извлечь из созданных файлов
        if category == "general" and context.executions:
            for execution in context.executions:
                if execution.tool_name == "file_create" and execution.success:
                    # Извлекаем категорию из пути файла
                    if isinstance(execution.params, dict):
                        file_path = execution.params.get("path", "")
                        # Путь обычно вида "topics/category/subcategory/file.md"
                        parts = file_path.split("/")
                        if len(parts) >= 2 and parts[0] == "topics":
                            category = parts[1] if len(parts) > 1 else "general"
                            subcategory = parts[2] if len(parts) > 2 else None
                            break
        
        # Фоллбэк: автоопределение категории по контенту
        if category == "general":
            category = self.detect_category(markdown)
        
        return KBStructure(
            category=category,
            subcategory=subcategory,
            tags=tags
        )
