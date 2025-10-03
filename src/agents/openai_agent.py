"""
OpenAI Agent
Автономный агент с использованием OpenAI-compatible API и function calling
"""

import json
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
        max_iterations: int = 10
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
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        logger.info(
            f"OpenAIAgent initialized with model={model}, "
            f"base_url={base_url}"
        )
    
    def _get_default_instruction(self) -> str:
        """Get default instruction for OpenAI agent"""
        return """Ты автономный агент для обработки и сохранения информации в базу знаний.

Твоя задача:
1. Проанализировать предоставленный контент
2. Составить план действий и записать его в TODO (используй plan_todo)
3. Выполнить план, используя доступные тулзы
4. Сохранить информацию в структурированном виде

Доступные тулзы:
- plan_todo: Создать план действий (список задач)
- web_search: Найти информацию в интернете
- file_create: Создать файл в базе знаний
- file_edit: Редактировать существующий файл
- folder_create: Создать папку для организации файлов
- analyze_content: Проанализировать контент и извлечь ключевую информацию

Процесс работы:
1. Сначала ОБЯЗАТЕЛЬНО создай plan_todo со списком задач
2. Выполни задачи по порядку, используя необходимые тулзы
3. Когда все задачи выполнены, верни финальный результат в markdown формате

Работай автономно, не задавай вопросов пользователю.
Используй тулзы по мере необходимости.
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
    
    def register_tool(self, name: str, handler: callable) -> None:
        """
        Зарегистрировать тулз
        
        Переопределяем чтобы добавить plan_todo автоматически
        
        Args:
            name: Tool name
            handler: Tool handler function
        """
        super().register_tool(name, handler)
        
        # Добавляем plan_todo если еще не добавлен
        if "plan_todo" not in self.tools:
            self.tools["plan_todo"] = self._handle_plan_todo
