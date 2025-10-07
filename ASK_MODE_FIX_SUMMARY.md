# Исправление режима `/ask` - Форматирование ответа

## Проблема

Режим `/ask` работал некорректно:
1. Агент возвращал весь вывод (включая процесс поиска), а не только итоговый ответ пользователю
2. Ответ не всегда был на русском языке
3. Формат ответа был непредсказуемым - показывалась техническая информация вместо понятного ответа

## Причина

В коде был разрыв между тем, что агент возвращал и тем, что ожидал код парсинга:

1. **Промпт `KB_QUERY_PROMPT_TEMPLATE`** просил агента вернуть результат в блоке `agent-result` с полем `answer`
2. **Метод `parse_agent_response`** в `base_agent.py` НЕ извлекал поле `answer` из блока `agent-result`
3. **Код в `question_answering_service.py`** искал ключ `answer` в response, но его там не было
4. В промпте не было чёткого требования отвечать на русском языке и форматировать ответ для конечного пользователя

## Решение

### 1. Обновлён промпт `KB_QUERY_PROMPT_TEMPLATE` (`config/agent_prompts.py`)

**Изменения:**
- Добавлены яркие маркеры 🔴 с требованием отвечать НА РУССКОМ
- Явно указано, что поле `answer` - это ИТОГОВЫЙ ответ пользователю
- Подчёркнуто, что в `answer` НЕ должно быть технической информации о процессе поиска
- Добавлен пример хорошего ответа
- Улучшено описание формата блока `agent-result`

**Ключевые добавления:**
```
🔴 КРИТИЧНО: Твой основной язык - РУССКИЙ! ВСЕ ответы должны быть ТОЛЬКО на РУССКОМ языке!
🔴 ВАЖНО: Ответь пользователю ПОНЯТНО и СТРУКТУРИРОВАННО!

ВНИМАНИЕ: Поле "answer" - это ИТОГОВЫЙ ОТВЕТ пользователю! Он должен быть:
- На РУССКОМ языке
- Полным и исчерпывающим
- Понятным для пользователя
- С указанием источников
- Хорошо отформатированным в markdown

Это поле напрямую покажется пользователю, поэтому НЕ пиши туда техническую информацию о процессе поиска!
```

### 2. Обновлён `AgentResult` класс (`src/agents/base_agent.py`)

**Изменения:**
- Добавлено поле `answer: Optional[str] = None` в dataclass `AgentResult`
- Поле `answer` добавлено в метод `to_dict()`

**Код:**
```python
@dataclass
class AgentResult:
    # ... existing fields ...
    answer: Optional[str] = None  # For ask mode - final answer to user
```

### 3. Обновлён метод `parse_agent_response` (`src/agents/base_agent.py`)

**Изменения:**
- Добавлено извлечение поля `answer` из блока `agent-result`
- Поле `answer` передаётся в конструктор `AgentResult`

**Код:**
```python
answer = None

# In JSON parsing block:
answer = result_data.get("answer")  # Extract answer for ask mode

# In return statement:
return AgentResult(
    # ... existing fields ...
    answer=answer
)
```

### 4. Обновлён `QwenCodeCLIAgent.process()` (`src/agents/qwen_code_cli_agent.py`)

**Изменения:**
- Добавлено поле `answer` в возвращаемый результат

**Код:**
```python
result = {
    "markdown": agent_result.markdown,
    "metadata": metadata,
    "title": title,
    "kb_structure": kb_structure,
    "answer": agent_result.answer  # Include answer for ask mode
}
```

### 5. Обновлён `QuestionAnsweringService._query_kb()` (`src/services/question_answering_service.py`)

**Изменения:**
- Приоритет извлечения ответа: сначала `answer`, затем `markdown`, затем `text`
- Добавлено логирование предупреждения, если поле `answer` отсутствует
- Улучшены комментарии

**Код:**
```python
# Extract answer from response (priority: answer field, then markdown, then text)
# The 'answer' field contains the final formatted answer from agent-result block
answer = response.get('answer')

# Fallback to markdown or text if answer is not present
if not answer:
    self.logger.warning("Agent did not return 'answer' field, using markdown/text as fallback")
    answer = response.get('markdown') or response.get('text', '')

if not answer:
    raise ValueError("Agent did not return an answer")

return answer
```

## Результат

Теперь режим `/ask` работает правильно:

1. ✅ **Агент понимает**, что нужно вернуть итоговый ответ в поле `answer`
2. ✅ **Промпт явно требует** отвечать на русском языке
3. ✅ **Парсинг извлекает** поле `answer` из блока `agent-result`
4. ✅ **Код показывает пользователю** только итоговый ответ, а не весь процесс поиска
5. ✅ **Есть fallback** на `markdown`/`text` если агент не вернул `answer`

## Затронутые файлы

1. `config/agent_prompts.py` - обновлён промпт `KB_QUERY_PROMPT_TEMPLATE`
2. `src/agents/base_agent.py` - добавлено поле `answer` в `AgentResult` и `parse_agent_response`
3. `src/agents/qwen_code_cli_agent.py` - добавлено поле `answer` в result
4. `src/services/question_answering_service.py` - улучшена логика извлечения ответа

## Тестирование

Для проверки:
1. Переключитесь в режим `/ask`
2. Задайте вопрос по вашей базе знаний
3. Проверьте что:
   - Ответ на русском языке
   - Ответ понятный и структурированный
   - Нет технической информации о процессе поиска
   - Указаны источники (файлы из базы знаний)
