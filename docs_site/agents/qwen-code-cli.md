# Qwen Code CLI Agent

Complete guide to using the Qwen Code CLI agent.

---

## Overview

The Qwen Code CLI agent is the most powerful option, using the official [qwen-code](https://github.com/QwenLM/qwen-code) CLI tool for advanced AI processing.

---

## Features

- ✅ Full integration with Qwen3-Coder models
- ✅ Automatic TODO planning
- ✅ Built-in tools: web search, git, github, shell
- ✅ Free tier: 2000 requests/day
- ✅ Vision model support
- ✅ **DEBUG трейсинг выполнения CLI** - [Подробнее →](qwen-cli-debug-trace.md)

---

## Installation

### 1. Install Node.js 20+

```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node@20

# Windows
# Download from nodejs.org
```

### 2. Install Qwen Code CLI

```bash
npm install -g @qwen-code/qwen-code@latest
```

Docker: The bot image already includes Node.js 20 and the Qwen CLI. You only need to authenticate inside the running container once (persisted via `~/.qwen` bind mount):

```bash
docker exec -it tg-note-bot bash -lc "qwen"
```

### 3. Verify Installation

```bash
qwen --version
```

### 4. Authenticate

```bash
qwen
```

Follow the prompts to authenticate via qwen.ai.

### 5. Configure Approval Mode (IMPORTANT!)

**⚠️ КРИТИЧЕСКИ ВАЖНО:** Для корректной работы CLI с ботом необходимо настроить режим одобрения инструментов:

```bash
qwen
/approval-mode yolo --project
```

Docker one-liners for non-interactive application:

```bash
docker exec -it tg-note-bot bash -lc "qwen <<<'/approval-mode yolo --project'"
```

**Зачем это нужно?**

- CLI по умолчанию требует ручного подтверждения для каждого действия
- Бот работает в автономном режиме и не может взаимодействовать с CLI интерактивно
- Режим `yolo` автоматически одобряет все операции агента

**⚠️ Внимание!** Использование режима `yolo` - на ваш страх и риск. Агент получит полный доступ к файловым операциям и командам.

**Доступные режимы одобрения:**

- `plan` - только анализ, без изменения файлов
- `default` - требует подтверждения для редактирования файлов и команд
- `auto-edit` - автоматически одобряет редактирование файлов
- `yolo` - автоматически одобряет все операции (требуется для бота)

**Области применения:**

- `--session` - только для текущей сессии
- `--project` - для текущего проекта (рекомендуется)
- `--user` - для всех проектов пользователя

**Рекомендуется ознакомиться с [официальной документацией qwen-code-cli](https://github.com/QwenLM/qwen-code) для полного понимания возможностей и ограничений.**

---

## Configuration

Update `config.yaml`:

```yaml
AGENT_TYPE: "qwen_code_cli"
AGENT_QWEN_CLI_PATH: "qwen"
AGENT_TIMEOUT: 300
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false
```

Tip: The CLI path is configurable via `AGENT_QWEN_CLI_PATH` and defaults to `qwen`. Ensure `qwen --version` succeeds on your system before enabling this agent.

---

## How It Works

1. Message received
2. Agent prepares prompt
3. CLI working directory set to user's knowledge base path
4. Calls `qwen` CLI in KB directory
5. Qwen creates TODO plan
6. Executes plan with tools (files created in correct KB location)
7. Returns structured markdown
8. Saved to KB

**Important:** The CLI automatically runs inside your knowledge base directory (`knowledge_bases/your-kb-name/`). This ensures that any files created by the agent are saved to the correct location in your knowledge base structure.

### Note Mode: Structure and Quality Gates

Use these rules to maximize the quality of the knowledge base in note mode:

- **Атомарность**: одна заметка = один концепт/определение/процедура/решение. Если тем несколько — разделяйте на несколько файлов.
- **Дедупликация**: перед созданием ищите существующие файлы по ключевым словам/синонимам; при совпадении — дополняйте существующую заметку, а не создавайте дубликат.
- **Фронтматтер**: каждый новый файл должен начинаться с YAML-блока.

```yaml
---
title: <канонический термин>
category: <категория>
subcategory: <подкатегория|опционально>
tags: [тег1, тег2]
sources: ["url1", "url2"]
synonyms: ["синоним1", "синоним2"]
---
```

- **Тело заметки**: `# Заголовок` (совпадает с title) → краткий Summary (≤3 предложения) → точные определения/шаги/параметры/ограничения.
- **Связи**: добавляйте 2–5 ссылок на уже существующие файлы через `[[путь/к/файлу.md]]` и давайте содержательные описания (1–2 предложения).
- **Источники**: как минимум один источник (URL/локатор).
- **Ограничения**: не изменяйте `index.md` и корневой `README.md`, если это явно не требуется.

### Connection Descriptions (Связи)

- Agent must add links only to EXISTING KB files (not those created in the same run).
- Each link MUST include a meaningful description (1–2 sentences) explaining the nature of the connection: similarity/difference, dependency, part-whole, alternative, sequence, overlapping concepts.
- Avoid generic placeholders like “Связанная тема”.

### Именование и пути
- Все новые файлы хранятся в `topics/<category>/<subcategory?>/`.
- Имя файла: `YYYY-MM-DD-<slug>.md` (slug из заголовка, латиница, `-`).

### Quality Gates (перед возвратом результата)
1) RU‑язык. 2) Атомарность соблюдена. 3) Есть фронтматтер. 4) ≥1 источник. 5) Внутренние связи ≥2 (если уместно). 6) Дубликатов нет. 7) `agent-result` и `metadata` присутствуют.

---

## Troubleshooting

### Files Created in Wrong Location

**Проблема:** CLI создаёт файлы в корне проекта, а не в `knowledge_bases/your-kb-name/`

**Решение:** Это было исправлено в последней версии. Бот автоматически устанавливает рабочую директорию CLI в путь вашей базы знаний перед каждым запросом. Убедитесь, что вы используете актуальную версию бота.

**Как это работает:**

- При обработке сообщения бот определяет путь к вашей базе знаний
- Перед вызовом `qwen` CLI устанавливается `working_directory` в этот путь
- Все файлы, созданные агентом, попадают в правильную структуру KB

### CLI Requires Manual Approval

**Проблема:** CLI требует подтверждения каждого действия, бот зависает

**Решение:** Настройте режим `yolo` как описано в разделе установки:

```bash
qwen
/approval-mode yolo --project
```

**Почему это необходимо:**

- CLI по умолчанию работает в интерактивном режиме
- Бот не может взаимодействовать с CLI в интерактивном режиме
- Режим `yolo` отключает все запросы подтверждения

### Authentication Issues

**Проблема:** CLI не может авторизоваться

**Решение:**

1. Запустите `qwen` в терминале
2. Следуйте инструкциям для OAuth авторизации через qwen.ai
3. Либо настройте OpenAI-совместимый API:

   ```bash
   export OPENAI_API_KEY="your-key"
   export OPENAI_BASE_URL="your-url"
   ```

### CLI Not Found

**Проблема:** `qwen: command not found`

**Решение:**

1. Проверьте установку: `npm list -g @qwen-code/qwen-code`
2. Переустановите: `npm install -g @qwen-code/qwen-code@latest`
3. Проверьте PATH: `echo $PATH`
4. Если используете nvm: убедитесь, что Node.js активирован

---

## See Also

- [Agent Overview](overview.md)
- [Autonomous Agent](autonomous-agent.md)
- [Stub Agent](stub-agent.md)
