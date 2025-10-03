# Архитектура автономного агента

## Текущая ситуация

### QwenCodeCLIAgent
- ✅ Использует qwen-code CLI (внешний агент)
- ✅ qwen CLI сам составляет план и вызывает тулзы
- ❌ Нет контроля над процессом принятия решений
- ❌ Невозможно кастомизировать логику планирования

### QwenCodeAgent
- ✅ Python-based, есть собственные тулзы
- ✅ Реализована система TodoPlan
- ❌ План жёстко закодирован, не адаптивный
- ❌ LLM не принимает решения о вызове тулзов
- ❌ Тулзы не используются агентом самостоятельно

## Целевая архитектура

### Принцип работы автономного агента

```
┌─────────────────────────────────────────────────────────────┐
│                      АГЕНТСКИЙ ЦИКЛ                          │
└─────────────────────────────────────────────────────────────┘

1. Получение задачи + контекст
           ↓
2. LLM анализирует и решает:
   - Вызвать тулз?
   - Какой тулз?
   - С какими параметрами?
   - ИЛИ завершить работу (END_FLAG)?
           ↓
3. Обработчик:
   - Валидирует вызов тулза
   - Выполняет тулз
   - Собирает результат
           ↓
4. Результат → Обратно в LLM (п.2)
           ↓
5. Повтор до END_FLAG
```

### Компоненты системы

#### 1. Agent Core (Ядро агента)
```python
class AutonomousAgent:
    """
    Автономный агент с самостоятельным планированием
    """
    
    async def run(self, task: str) -> AgentResult:
        """
        Главный цикл агента
        
        1. Инициализация контекста
        2. Цикл планирования:
           - LLM решает что делать
           - Выполнение действия
           - Обновление контекста
        3. Возврат результата
        """
        
    async def _agent_loop(self) -> None:
        """
        Основной цикл агента
        
        while not done:
            decision = await llm.decide(context)
            
            if decision.action == "END":
                break
                
            result = await execute_tool(decision.tool, decision.params)
            context.add(result)
        """
```

#### 2. Tool Executor (Исполнитель тулзов)
```python
class ToolExecutor:
    """
    Безопасное выполнение тулзов с валидацией
    """
    
    def execute(self, tool_name: str, params: Dict) -> ToolResult:
        """
        1. Валидация тулза (существует ли?)
        2. Валидация параметров (пути, команды)
        3. Безопасное выполнение
        4. Обработка ошибок
        """
        
    def validate_params(self, tool_name: str, params: Dict) -> bool:
        """
        Валидация параметров:
        - Пути - только внутри KB root
        - Команды - только безопасные
        - Нет path traversal
        """
```

#### 3. LLM Interface (Интерфейс к LLM)
```python
class LLMInterface:
    """
    Абстракция для работы с разными LLM
    """
    
    async def decide(self, context: AgentContext) -> AgentDecision:
        """
        LLM принимает решение о следующем действии
        
        Возвращает:
        - action: "TOOL_CALL" | "END"
        - tool: название тулза (если TOOL_CALL)
        - params: параметры (если TOOL_CALL)
        - reasoning: объяснение решения
        """
        
    async def plan(self, task: str) -> List[str]:
        """
        LLM составляет план действий
        
        Но ВАЖНО: план может меняться в процессе!
        """
```

## Реализация для разных агентов

### Вариант 1: OpenAI-compatible LLM с function calling

```python
class OpenAIAgent(AutonomousAgent):
    """
    Агент на базе OpenAI API или совместимых (Qwen, etc.)
    
    Использует:
    - Function calling для тулзов
    - Автоматическое планирование
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "qwen-max",
        tools: List[Tool] = None
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.tools = self._register_tools(tools)
    
    async def _agent_loop(self, task: str) -> AgentResult:
        messages = [
            {"role": "system", "content": self.instruction},
            {"role": "user", "content": task}
        ]
        
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            # LLM решает что делать
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,  # Список доступных тулзов
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # LLM вызывает тулз?
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    # Выполнить тулз
                    result = await self.execute_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments)
                    )
                    
                    # Добавить результат в контекст
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
                
                iteration += 1
                continue
            
            # LLM закончил работу
            if message.content:
                return AgentResult(
                    content=message.content,
                    iterations=iteration,
                    tools_used=self.get_used_tools()
                )
            
            iteration += 1
        
        raise MaxIterationsError()
```

### Вариант 2: qwen-code CLI (внешний агент)

```python
class QwenCodeCLIAgent(AutonomousAgent):
    """
    Агент на базе qwen-code CLI
    
    qwen CLI - это ГОТОВЫЙ агент:
    - Сам планирует
    - Сам вызывает тулзы
    - Имеет встроенные capabilities
    
    Мы только:
    1. Передаем задачу
    2. Получаем результат
    """
    
    async def run(self, task: str) -> AgentResult:
        # Подготовить промпт с инструкцией
        prompt = self._prepare_prompt(task)
        
        # qwen CLI делает ВСЁ сам:
        # - Анализирует задачу
        # - Составляет план
        # - Вызывает тулзы
        # - Генерирует результат
        result = await self._execute_qwen_cli(prompt)
        
        return self._parse_result(result)
```

### Вариант 3: Custom Loop Agent (полный контроль)

```python
class CustomLoopAgent(AutonomousAgent):
    """
    Агент с полным контролем над процессом
    
    Мы сами:
    - Вызываем LLM для принятия решений
    - Парсим решения (какой тулз вызвать)
    - Выполняем тулзы
    - Собираем контекст
    """
    
    async def _agent_loop(self, task: str) -> AgentResult:
        context = AgentContext(task=task)
        
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            # 1. LLM принимает решение
            decision = await self._llm_decide(context)
            
            # 2. Проверка завершения
            if decision.action == "END":
                return decision.final_result
            
            # 3. Валидация тулза
            if not self._validate_tool_call(decision):
                context.add_error(f"Invalid tool call: {decision}")
                iteration += 1
                continue
            
            # 4. Выполнение тулза
            try:
                result = await self.tool_executor.execute(
                    decision.tool_name,
                    decision.tool_params
                )
                context.add_tool_result(decision.tool_name, result)
            except Exception as e:
                context.add_error(f"Tool execution failed: {e}")
            
            iteration += 1
        
        raise MaxIterationsError()
    
    async def _llm_decide(self, context: AgentContext) -> AgentDecision:
        """
        Вызов LLM для принятия решения
        
        Промпт содержит:
        - Задачу
        - Историю действий
        - Доступные тулзы
        - Инструкцию (формат ответа)
        """
        
        prompt = f"""
{self.instruction}

# Задача
{context.task}

# История действий
{context.get_history()}

# Доступные тулзы
{self.get_tools_description()}

# Решение
Проанализируй ситуацию и реши что делать:

1. Если задача НЕ завершена:
   Ответь в формате:
   {{
     "action": "TOOL_CALL",
     "tool": "название_тулза",
     "params": {{"param1": "value1"}},
     "reasoning": "объяснение почему"
   }}

2. Если задача ЗАВЕРШЕНА:
   Ответь в формате:
   {{
     "action": "END",
     "result": "итоговый результат в markdown"
   }}
"""
        
        response = await self.llm.generate(prompt)
        return self._parse_decision(response)
```

## Сравнение подходов

### qwen-code CLI
✅ **Плюсы:**
- Готовое решение
- Оптимизировано для Qwen моделей
- Встроенные тулзы
- Автоматическое планирование

❌ **Минусы:**
- Нет контроля над процессом
- Зависимость от Node.js
- Сложно кастомизировать

### OpenAI Function Calling
✅ **Плюсы:**
- Нативная поддержка в API
- Чистая интеграция
- Хорошая документация

❌ **Минусы:**
- Нужен API с function calling
- Стоимость API вызовов

### Custom Loop
✅ **Плюсы:**
- Полный контроль
- Можно использовать любой LLM
- Гибкая кастомизация

❌ **Минусы:**
- Больше кода
- Нужно парсить ответы LLM
- Может быть менее надежно

## Рекомендации

### Для production
**Используйте qwen-code CLI**, если:
- Не нужен полный контроль над процессом
- Устраивают встроенные capabilities
- Можно установить Node.js

**Используйте OpenAI Function Calling**, если:
- Есть API с function calling (Qwen, OpenAI, etc.)
- Нужна интеграция с вашими тулзами
- Важна гибкость

**Используйте Custom Loop**, если:
- Нужен полный контроль
- Специфичные требования
- Нужно использовать локальные модели

## Следующие шаги

1. ✅ Документация архитектуры (этот файл)
2. ⏳ Реализовать базовый AgentLoop
3. ⏳ Реализовать OpenAI-compatible агент с function calling
4. ⏳ Интеграция с существующими тулзами
5. ⏳ Тесты и валидация
6. ⏳ Документация по использованию

## Пример использования (целевой API)

```python
# Создать агента
agent = AutonomousAgent(
    type="openai",
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    model="qwen-max",
    instruction="""
    Ты агент для анализа и сохранения информации в базу знаний.
    Используй доступные тулзы для:
    - Поиска информации в интернете
    - Создания файлов и папок
    - Анализа контента
    
    Работай автономно, составляй план и выполняй его.
    """
)

# Зарегистрировать тулзы
agent.register_tool(WebSearchTool())
agent.register_tool(FileCreateTool(kb_root="/path/to/kb"))
agent.register_tool(FolderCreateTool(kb_root="/path/to/kb"))

# Запустить агента
result = await agent.run(
    task="""
    Проанализируй статью о машинном обучении:
    https://example.com/ml-article
    
    Сохрани информацию в базу знаний:
    - Создай структуру папок
    - Создай файлы с информацией
    - Добавь метаданные
    """
)

print(result.final_output)
print(f"Использовано тулзов: {result.tools_used}")
print(f"Итераций: {result.iterations}")
```
