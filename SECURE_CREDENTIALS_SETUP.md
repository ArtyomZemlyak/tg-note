# 🔐 Безопасная передача Git Credentials через Telegram бота

## Проблема

При работе с несколькими пользователями возникает проблема:
- ❌ В `.env` файле можно хранить только один токен
- ❌ Все пользователи используют один и тот же токен
- ❌ Передача токена через другие каналы небезопасна

## Решение

✅ **Персональные зашифрованные токены для каждого пользователя**

Теперь каждый пользователь может безопасно добавить свой личный токен GitHub или GitLab прямо через Telegram бота!

## Безопасность

🔐 **Как это работает:**

1. **Шифрование**: Токены шифруются с помощью Fernet (AES-128)
2. **Автоматическое удаление**: Сообщения с токенами автоматически удаляются
3. **Не логируются**: Токены не попадают в логи
4. **Безопасное хранение**: Файлы с credentials имеют права доступа 600

## Быстрый старт

### 1. Установка зависимостей

```bash
poetry install
# или
pip install -e .
```

Это установит новую зависимость `cryptography` для шифрования.

### 2. Получение токена

**GitHub:**
1. Перейдите: https://github.com/settings/tokens
2. Generate new token (classic)
3. Выберите scope: `repo`
4. Скопируйте токен

**GitLab:**
1. Перейдите: https://gitlab.com/-/profile/personal_access_tokens
2. Создайте токен
3. Выберите scope: `write_repository`
4. Скопируйте токен

### 3. Добавление токена через бота

```
1. Откройте чат с ботом
2. Отправьте: /settoken
3. Выберите платформу (GitHub или GitLab)
4. Введите username
5. Введите токен
6. ✅ Готово! Токен зашифрован и сохранен
```

## Команды

### `/settoken` - Добавить токен
Безопасно добавляет ваш персональный Git токен. Поддерживает GitHub и GitLab.

### `/listcredentials` - Просмотр токенов
Показывает информацию о сохраненных токенах (без раскрытия самих токенов).

### `/removetoken` - Удалить токен
Удаляет сохраненные токены для выбранной платформы или все сразу.

## Как это работает внутри?

### Приоритет credentials

При выполнении Git операций (pull, push, commit):

1. **Персональный токен** (из `/settoken`) - высший приоритет
2. **Глобальный токен** (из `.env`) - fallback

Это значит:
- Пользователи с персональными токенами используют их автоматически
- Пользователи без персональных токенов используют глобальный (если настроен)

### Автоматическое определение платформы

Бот автоматически определяет какой токен использовать:

```
https://github.com/user/repo.git  → GitHub credentials
https://gitlab.com/user/repo.git  → GitLab credentials
```

### Инжектирование credentials

При выполнении Git операций:

```
https://github.com/user/repo.git
    ↓
https://username:token@github.com/user/repo.git
```

## Архитектура

```
┌─────────────────────────────────────────────┐
│           Telegram Bot                       │
│                                               │
│  User → /settoken → CredentialsHandlers     │
│                            ↓                  │
│                    CredentialsManager        │
│                            ↓                  │
│                    Encrypt (Fernet)          │
│                            ↓                  │
│                    Save to disk              │
│                                               │
│  Git Operation → GitOperations               │
│                            ↓                  │
│                    Get credentials           │
│                            ↓                  │
│                    Inject to URL             │
│                            ↓                  │
│                    Execute Git command       │
└─────────────────────────────────────────────┘
```

## Файлы

### Новые файлы

- `src/knowledge_base/credentials_manager.py` - Менеджер шифрования и хранения credentials
- `src/bot/credentials_handlers.py` - Telegram handlers для управления токенами
- `docs_site/user-guide/git-credentials.md` - Полная документация

### Измененные файлы

- `config/settings.py` - Добавлены `GITLAB_TOKEN` и `GITLAB_USERNAME`
- `src/knowledge_base/git_ops.py` - Поддержка персональных credentials
- `src/services/agent_task_service.py` - Использование credentials_manager
- `src/services/note_creation_service.py` - Использование credentials_manager
- `src/bot/telegram_bot.py` - Интеграция credentials_handlers
- `src/core/service_container.py` - Регистрация credentials_manager
- `pyproject.toml` - Добавлена зависимость `cryptography`

### Хранилище credentials

После первого использования будут созданы:

- `./data/.credentials_key` - Ключ шифрования (права: 600)
- `./data/user_credentials.enc` - Зашифрованные токены (права: 600)

**⚠️ Важно:**
- Не удаляйте ключ шифрования!
- Делайте резервные копии ключа
- Добавьте эти файлы в `.gitignore` (уже добавлено)

## Обновление .env

Теперь можно (опционально) добавить GitLab credentials в `.env`:

```env
# GitHub credentials (fallback)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_USERNAME=username

# GitLab credentials (fallback)
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_USERNAME=username
```

## Миграция для существующих пользователей

Если у вас уже настроен глобальный GitHub токен в `.env`:

1. Он продолжит работать как fallback
2. Пользователи могут добавить свои персональные токены через `/settoken`
3. Персональные токены будут иметь приоритет

## Тестирование

```bash
# Установите зависимости
poetry install

# Запустите бота
poetry run tg-note

# В Telegram:
1. /settoken
2. Выберите платформу
3. Введите credentials
4. Проверьте: /listcredentials
```

## Дополнительная информация

Полная документация: `docs_site/user-guide/git-credentials.md`

## Безопасность - FAQ

**Q: Безопасно ли передавать токен через Telegram?**

A: Да:
- Telegram использует шифрование
- Сообщение автоматически удаляется
- Токен шифруется перед сохранением
- Токен не попадает в логи

**Q: Может ли администратор видеть токены?**

A: Нет, токены хранятся в зашифрованном виде.

**Q: Что если я потеряю ключ шифрования?**

A: Токены станут нечитаемыми. Нужно будет добавить их заново через `/settoken`.

## Поддержка

Вопросы и issues: https://github.com/ArtyomZemlyak/tg-note/issues

---

Made with ❤️ for secure multi-user Git operations
