# Исправление ошибки настройки базы знаний

## Проблема

После выполнения команды `/setkb my-notes` пользователи получали ошибку:

```
❌ База знаний не настроена
Используйте /setkb для настройки базы знаний
```

Это происходило даже после успешной настройки базы знаний.

## Причина

В методе `_process_message_group` (файл `src/bot/handlers.py`, строка 346-478) использовался неправильный источник для получения `user_id`.

### Код ДО исправления (строка 350):

```python
async def _process_message_group(self, group, processing_msg: Message) -> None:
    """Process a complete message group (async)"""
    try:
        # Check if user has KB configured
        user_id = processing_msg.from_user.id  # ❌ ОШИБКА!
        user_kb = self.user_settings.get_user_kb(user_id)
```

**Проблема:** `processing_msg` - это служебное сообщение бота ("🔄 Обрабатываю сообщение..."), а не оригинальное сообщение пользователя. В результате:
- `processing_msg.from_user.id` возвращал ID **бота**, а не ID **пользователя**
- Настройки KB искались для бота, а не для пользователя
- База знаний не находилась, даже если была настроена для пользователя

## Решение

Получать `user_id` из первого сообщения в группе (`group.messages[0]`), которое содержит данные оригинального сообщения пользователя.

### Код ПОСЛЕ исправления (строка 346-365):

```python
async def _process_message_group(self, group, processing_msg: Message) -> None:
    """Process a complete message group (async)"""
    try:
        # Get user_id from the first message in the group (original user message, not bot's processing_msg)
        if not group.messages:
            self.logger.warning("Empty message group, skipping processing")
            return
        
        user_id = group.messages[0].get('user_id')  # ✅ ПРАВИЛЬНО!
        if not user_id:
            self.logger.error("Cannot determine user_id from message group")
            await self.bot.edit_message_text(
                "❌ Ошибка: не удалось определить пользователя",
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
            return
        
        # Check if user has KB configured
        user_kb = self.user_settings.get_user_kb(user_id)
```

## Изменения

1. **Добавлена проверка на пустую группу сообщений**
2. **Изменён источник `user_id`:** с `processing_msg.from_user.id` на `group.messages[0].get('user_id')`
3. **Добавлена валидация `user_id`** с отображением ошибки пользователю

## Тестирование

Создан тест `test_kb_fix.py`, который проверяет:

1. ✅ Начальное состояние (KB не настроена)
2. ✅ Настройка локальной KB через `repo_manager.init_local_kb()`
3. ✅ Сохранение настроек через `user_settings.set_user_kb()`
4. ✅ Получение настроек через `user_settings.get_user_kb()`
5. ✅ Симуляция обработки сообщения с правильным получением `user_id` из группы

### Результат теста:

```
🧪 Testing KB setup and verification logic...

1️⃣ Checking initial state (should be None)...
   ✅ Initial state is correct (no KB configured)

2️⃣ Setting up local KB 'my-notes'...
   Repository init: Knowledge base 'my-notes' initialized successfully
   ✅ KB setup successful

3️⃣ Verifying KB is configured...
   User KB settings: {
  "kb_name": "my-notes",
  "kb_type": "local",
  "github_url": null,
  "has_credentials": false
}
   ✅ KB is configured:
      - Name: my-notes
      - Type: local

4️⃣ Simulating message processing check...
   Retrieved user_id from group: 123456789
   ✅ KB check passed: my-notes (local)

✅ All tests passed! The fix is working correctly.
```

## Влияние

Это исправление решает критическую проблему, из-за которой функционал базы знаний был полностью нерабочим:
- ✅ Теперь команда `/setkb` работает корректно
- ✅ Настройки KB правильно связываются с пользователями
- ✅ Обработка сообщений использует правильную базу знаний пользователя

## Файлы изменены

- `src/bot/handlers.py` - исправлена логика получения `user_id` в методе `_process_message_group`
- `test_kb_fix.py` - добавлен тест для проверки исправления
