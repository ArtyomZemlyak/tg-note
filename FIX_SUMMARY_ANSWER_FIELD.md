# Fix: Agent Not Returning Answer Field

## Проблема

В режиме `/ask` (вопросы по базе знаний) агент иногда не возвращал поле `answer`, что приводило к ошибке:
```
"Agent did not return 'answer' field, using markdown/text as fallback"
```

В некоторых случаях это могло привести к тому, что пользователь не получал ответ на свой вопрос.

## Причина

Проблема заключалась в том, что метод `parse_agent_response` в `base_agent.py` пытался извлечь поле `answer` из JSON блока `agent-result`, но:

1. Если qwen CLI не возвращал поле `answer` в блоке `agent-result`
2. Если парсинг JSON блока `agent-result` завершался с ошибкой
3. Если агент возвращал ответ в другом формате

То поле `answer` оставалось `None`, и не было механизма fallback для извлечения ответа из самого текста response.

## Решение

### 1. Добавлен fallback механизм в `base_agent.py`

В метод `parse_agent_response` добавлена логика fallback:

```python
# Fallback: If answer is not in agent-result block, try to extract it from the response
if not answer:
    # Try to extract answer from the main content (excluding agent-result and metadata blocks)
    # Remove agent-result block (regex needs to match whitespace before closing ```)
    content_without_result = re.sub(r'```agent-result\s*\n.*?\n\s*```', '', response, flags=re.DOTALL)
    # Remove metadata block
    content_without_metadata = re.sub(r'```metadata\s*\n.*?\n\s*```', '', content_without_result, flags=re.DOTALL)
    
    # Clean up the content
    answer = content_without_metadata.strip()
    
    # If the cleaned content is empty or too short, use the full response
    if not answer or len(answer) < 50:
        answer = response.strip()
    
    import logging
    if answer and answer != response:
        logging.debug(f"Using extracted answer (length: {len(answer)}) as fallback")
    elif answer:
        logging.debug(f"Using full response as answer (length: {len(answer)})")
```

**Логика fallback:**
1. Удаляет блок `agent-result` из ответа
2. Удаляет блок `metadata` из ответа
3. Использует оставшийся контент как ответ
4. Если контент слишком короткий (< 50 символов), использует полный ответ

### 2. Улучшено логирование в `question_answering_service.py`

Добавлена более детальная проверка на пустой ответ:

```python
# Ensure answer is not None or empty
if not answer or not answer.strip():
    self.logger.error(f"Agent returned empty answer. Response keys: {list(response.keys())}")
    raise ValueError("Agent did not return an answer")
```

Теперь в логах будет видно, какие ключи были в response, что поможет в отладке.

### 3. Исправлен regex pattern

Изначальный regex pattern `r'```agent-result\s*\n(.*?)\n```'` не учитывал whitespace перед закрывающим ` ``` `, что приводило к тому, что блок не распознавался корректно.

Исправленный pattern: `r'```agent-result\s*\n(.*?)\n\s*```'`

Это исправление применено в двух местах:
- При извлечении JSON из блока `agent-result`
- При удалении блока `agent-result` в fallback

## Результат

Теперь режим `/ask` работает надежнее:

✅ **Если агент возвращает `answer` в блоке `agent-result`**: используется это поле (основной путь)

✅ **Если агент НЕ возвращает `answer` в блоке**: извлекается ответ из markdown контента (fallback)

✅ **Если ответ слишком короткий**: используется полный response (дополнительный fallback)

✅ **Логирование**: в логах видно, какой путь был использован для извлечения ответа

## Затронутые файлы

1. `src/agents/base_agent.py` - добавлен fallback механизм в `parse_agent_response`
2. `src/services/question_answering_service.py` - улучшено логирование ошибок

## Тестирование

Проведено тестирование с различными форматами ответов агента:

1. ✅ Ответ с полем `answer` в блоке `agent-result` - работает
2. ✅ Ответ БЕЗ поля `answer` в блоке `agent-result` - fallback работает
3. ✅ Ответ БЕЗ блока `agent-result` - fallback работает
4. ✅ Короткий ответ - используется полный response

## Совместимость

Изменения обратно совместимы:
- Если агент возвращает `answer` в блоке `agent-result`, поведение не изменилось
- Добавлен только fallback для случаев, когда `answer` отсутствует
- Не требуется изменений в промптах или других частях системы

## Рекомендации

1. Мониторить логи на предмет сообщений о fallback
2. Если fallback срабатывает часто, возможно нужно улучшить промпт `KB_QUERY_PROMPT_TEMPLATE`
3. Рассмотреть возможность добавления метрик для отслеживания использования fallback
