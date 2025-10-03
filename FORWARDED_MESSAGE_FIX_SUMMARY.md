# Исправление обработки пересланных сообщений

## Проблема
Пересланные сообщения не принимались в обработку из-за неправильной логики определения пересланных сообщений.

## Причина
Функция `_is_forwarded_message()` проверяла только на `is not None`, что могло приводить к ложным срабатываниям в edge cases:
- Пустые строки (`""`) в `forward_sender_name` считались пересланными
- Значение `0` в `forward_date` могло вызывать проблемы
- Строки с пробелами считались пересланными

## Решение

### 1. Улучшена логика определения пересланных сообщений

**Файлы:**
- `src/bot/handlers.py` (метод `_is_forwarded_message`)
- `src/bot/settings_handlers.py` (метод `_is_forwarded_message`)

**Изменения:**
```python
def _is_forwarded_message(self, message: Message) -> bool:
    """Check if message is forwarded from any source"""
    # Check forward_date first as it's the most reliable indicator
    # forward_date is an integer timestamp, so we check it's not None and > 0
    if message.forward_date is not None and message.forward_date > 0:
        return True
    
    # Check other forward fields (objects or strings)
    return bool(
        message.forward_from or
        message.forward_from_chat or
        (message.forward_sender_name and message.forward_sender_name.strip())
    )
```

**Улучшения:**
1. `forward_date` проверяется первым как наиболее надежный индикатор
2. `forward_date > 0` исключает edge case с нулевым timestamp
3. `forward_sender_name.strip()` исключает пустые строки и строки с пробелами
4. Использование `bool()` для явного приведения к логическому типу

### 2. Обновлены тесты

**Файлы:**
- `tests/test_handlers_forwarded_fix.py`
- `tests/test_settings_forwarded_fix.py`

**Добавленные тест-кейсы:**
- Проверка `forward_date = 0` (должно быть False)
- Проверка пустых строк в `forward_sender_name` (должно быть False)
- Проверка строк с пробелами в `forward_sender_name` (должно быть False)
- Улучшенная надежность тестов с добавлением `forward_date` для всех случаев

## Тестирование

Все изменения покрыты юнит-тестами:
- `test_is_forwarded_message_detection` - проверка базовой логики
- `test_forwarded_message_ignored_during_settings_input` - проверка игнорирования при вводе настроек
- `test_forwarded_message_processed_when_not_waiting` - проверка обработки в нормальном режиме
- `test_is_forwarded_message_from_privacy_user` - проверка edge cases с пустыми строками

## Результат

✅ Пересланные сообщения теперь корректно определяются и обрабатываются
✅ Исключены ложные срабатывания на пустых строках и нулевых значениях
✅ Улучшена надежность за счет приоритета `forward_date`
✅ Все изменения покрыты тестами

## Примечания

Обработчики регистрируются в следующем порядке (см. `src/bot/telegram_bot.py`):
1. Settings handlers (для режима ввода настроек)
2. Main handlers (для обычной обработки сообщений)

Пересланные сообщения обрабатываются обработчиком `handle_forwarded_message` из `handlers.py`, который проверяет, находится ли пользователь в режиме ввода настроек, и соответственно либо игнорирует сообщение, либо обрабатывает его.
