# Документация проекта tg-note

## 📖 Где найти документацию

### Онлайн (Рекомендуется)

**GitHub Pages:** https://artyomzemlyak.github.io/tg-note/

Полная документация с удобной навигацией, поиском и современным дизайном.

### Локально

```bash
# Установить зависимости
pip install -r requirements-docs.txt

# Запустить локальный сервер
mkdocs serve

# Открыть в браузере
# http://localhost:8000
```

---

## 🗂️ Структура документации

### Getting Started (Начало работы)
- [Quick Start](https://artyomzemlyak.github.io/tg-note/getting-started/quick-start/) - Быстрый старт за 5 минут
- [Installation](https://artyomzemlyak.github.io/tg-note/getting-started/installation/) - Детальная установка
- [Configuration](https://artyomzemlyak.github.io/tg-note/getting-started/configuration/) - Настройка
- [First Steps](https://artyomzemlyak.github.io/tg-note/getting-started/first-steps/) - Первые шаги

### User Guide (Руководство пользователя)
- [Bot Commands](https://artyomzemlyak.github.io/tg-note/user-guide/bot-commands/) - Команды бота
- [Working with Content](https://artyomzemlyak.github.io/tg-note/user-guide/working-with-content/) - Работа с контентом
- [Settings Management](https://artyomzemlyak.github.io/tg-note/user-guide/settings-management/) - Управление настройками
- [Knowledge Base Setup](https://artyomzemlyak.github.io/tg-note/user-guide/knowledge-base-setup/) - Настройка базы знаний

### Agent System (Система агентов)
- [Overview](https://artyomzemlyak.github.io/tg-note/agents/overview/) - Обзор агентов
- [Qwen Code CLI](https://artyomzemlyak.github.io/tg-note/agents/qwen-code-cli/) - Qwen CLI агент
- [Qwen Code Agent](https://artyomzemlyak.github.io/tg-note/agents/qwen-code/) - Python агент
- [Autonomous Agent](https://artyomzemlyak.github.io/tg-note/agents/autonomous-agent/) - Автономные агенты
- [Stub Agent](https://artyomzemlyak.github.io/tg-note/agents/stub-agent/) - Тестовый агент

### Architecture (Архитектура)
- [Overview](https://artyomzemlyak.github.io/tg-note/architecture/overview/) - Обзор архитектуры
- [Agent Architecture](https://artyomzemlyak.github.io/tg-note/architecture/agent-architecture/) - Архитектура агентов
- [Settings Architecture](https://artyomzemlyak.github.io/tg-note/architecture/settings-architecture/) - Архитектура настроек
- [Data Flow](https://artyomzemlyak.github.io/tg-note/architecture/data-flow/) - Поток данных

### Development (Разработка)
- [Project Structure](https://artyomzemlyak.github.io/tg-note/development/project-structure/) - Структура проекта
- [Testing](https://artyomzemlyak.github.io/tg-note/development/testing/) - Тестирование
- [Code Quality](https://artyomzemlyak.github.io/tg-note/development/code-quality/) - Качество кода
- [Contributing](https://artyomzemlyak.github.io/tg-note/development/contributing/) - Вклад в проект

### Deployment (Развёртывание)
- [Production Setup](https://artyomzemlyak.github.io/tg-note/deployment/production/) - Production
- [Docker](https://artyomzemlyak.github.io/tg-note/deployment/docker/) - Docker
- [CI/CD](https://artyomzemlyak.github.io/tg-note/deployment/cicd/) - CI/CD

### Reference (Справочник)
- [Configuration](https://artyomzemlyak.github.io/tg-note/reference/configuration/) - Конфигурация
- [API](https://artyomzemlyak.github.io/tg-note/reference/api/) - API
- [Troubleshooting](https://artyomzemlyak.github.io/tg-note/reference/troubleshooting/) - Решение проблем
- [FAQ](https://artyomzemlyak.github.io/tg-note/reference/faq/) - Часто задаваемые вопросы

---

## 🛠️ Работа с документацией

### Локальная разработка

```bash
# Клонировать репозиторий
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note

# Установить зависимости для документации
pip install -r requirements-docs.txt

# Запустить локальный сервер (с автообновлением)
mkdocs serve

# Откроется на http://localhost:8000
```

### Редактирование документации

1. Файлы документации находятся в `docs_site/`
2. Используется Markdown формат
3. Структура определена в `mkdocs.yml`
4. При изменении файлов локальный сервер автоматически обновляется

### Добавление новой страницы

1. Создайте `.md` файл в соответствующей директории `docs_site/`
2. Добавьте запись в `mkdocs.yml` в секцию `nav:`
3. Commit и push - GitHub Actions автоматически обновит сайт

Пример:

```yaml
# mkdocs.yml
nav:
  - Home: index.md
  - Getting Started:
    - Quick Start: getting-started/quick-start.md
    - Your New Page: getting-started/your-new-page.md  # Добавьте сюда
```

### Сборка документации

```bash
# Собрать статический сайт
mkdocs build

# Результат в директории site/
```

### Деплой на GitHub Pages

Автоматический деплой настроен через GitHub Actions (`.github/workflows/docs.yml`).

При push в `main` ветку:
1. GitHub Actions собирает документацию
2. Публикует на GitHub Pages
3. Доступно по адресу: https://artyomzemlyak.github.io/tg-note/

Ручной деплой:

```bash
mkdocs gh-deploy
```

---

## 🎨 Возможности документации

### Навигация
- ✅ Вкладки для основных разделов
- ✅ Древовидная структура
- ✅ Breadcrumbs (хлебные крошки)
- ✅ Table of Contents (оглавление)

### Функциональность
- ✅ Полнотекстовый поиск
- ✅ Подсветка синтаксиса кода
- ✅ Копирование кода одним кликом
- ✅ Темная/светлая тема
- ✅ Адаптивный дизайн (мобильные устройства)

### Markdown расширения
- ✅ Эмодзи `:smile:` → 😊
- ✅ Заметки и предупреждения (admonitions)
- ✅ Списки задач
- ✅ Вкладки (tabs)
- ✅ Кнопки и карточки

### Примеры использования

#### Заметки

```markdown
!!! note "Заголовок заметки"
    Текст заметки

!!! warning "Предупреждение"
    Важная информация

!!! tip "Совет"
    Полезный совет
```

#### Вкладки

```markdown
=== "Python"
    ```python
    print("Hello, World!")
    ```

=== "Bash"
    ```bash
    echo "Hello, World!"
    ```
```

#### Кнопки

```markdown
[Кнопка]('https://example.com'){ .md-button }
[Основная кнопка]('https://example.com'){ .md-button .md-button--primary }
```

---

## 📝 Стиль документации

### Структура страницы

```markdown
# Заголовок страницы

Краткое описание страницы.

---

## Основной раздел

Содержимое раздела.

### Подраздел

Детали подраздела.

---

## См. также

- [Ссылка на связанную страницу](../path/to/page.md)
```

### Рекомендации

1. **Заголовки:**
   - H1 (`#`) - только один, заголовок страницы
   - H2 (`##`) - основные разделы
   - H3 (`###`) - подразделы

2. **Код:**
   - Используйте блоки кода с указанием языка
   - Добавляйте комментарии для сложных примеров

3. **Ссылки:**
   - Относительные ссылки для внутренних страниц
   - Абсолютные для внешних ресурсов

4. **Изображения:**
   - Храните в `docs_site/assets/images/`
   - Используйте описательные имена файлов

---

## 🔧 Технические детали

### Зависимости

```txt
mkdocs==1.5.3                        # Основной движок
mkdocs-material==9.5.3               # Material тема
mkdocs-git-revision-date-localized-plugin==1.2.2  # Даты изменений
mkdocs-minify-plugin==0.7.2          # Минификация HTML/CSS/JS
```

### Конфигурация

Основная конфигурация в `mkdocs.yml`:

- `site_name` - Название сайта
- `theme` - Настройки темы
- `nav` - Структура навигации
- `markdown_extensions` - Расширения Markdown
- `plugins` - Плагины MkDocs

### GitHub Actions

Workflow находится в `.github/workflows/docs.yml`:

- **Триггеры:** push в main, изменения в docs_site/
- **Процесс:** установка зависимостей → сборка → деплой
- **Результат:** обновлённая документация на GitHub Pages

---

## 📊 Статистика

- **Страниц:** 32
- **Категорий:** 7
- **Зависимостей:** 4
- **Файлов удалено:** 60
- **Время сборки:** ~30 секунд
- **Размер сайта:** ~5 МБ

---

## 🆘 Помощь

### Проблемы со сборкой

```bash
# Очистить кеш
mkdocs build --clean

# Проверить конфигурацию
mkdocs build --strict

# Вывести подробную информацию
mkdocs build --verbose
```

### Проблемы с деплоем

1. Проверьте GitHub Actions: https://github.com/ArtyomZemlyak/tg-note/actions
2. Проверьте настройки GitHub Pages в настройках репозитория
3. Убедитесь, что ветка `gh-pages` создана

### Ошибки в Markdown

- Проверьте синтаксис Markdown
- Убедитесь, что все ссылки корректны
- Проверьте YAML frontmatter (если используется)

---

## 📚 Дополнительные ресурсы

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Markdown Guide](https://www.markdownguide.org/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)

---

## ✅ Чеклист для контрибьюторов

При добавлении/изменении документации:

- [ ] Файл создан в правильной директории `docs_site/`
- [ ] Добавлена запись в `mkdocs.yml`
- [ ] Проверено локально (`mkdocs serve`)
- [ ] Все ссылки работают
- [ ] Код примеров протестирован
- [ ] Орфография проверена
- [ ] Следует стилю документации
- [ ] Commit message описателен
- [ ] Push в правильную ветку

---

**Для вопросов и предложений:** [Issues](https://github.com/ArtyomZemlyak/tg-note/issues)
