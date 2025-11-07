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

### Source Citations (Ссылки на источники)

**NEW REQUIREMENT (v4+):** The Qwen CLI agent now ALWAYS includes source references in created documents:

- **Inline citations** - Links directly in text next to specific facts/concepts
  - Format: `Согласно [название источника](URL), ...` or `... как описано в [источнике](URL)`
  - Example: `Модель GPT-4 использует архитектуру трансформера ([OpenAI Technical Report](https://openai.com/research/gpt-4))`

- **"Источники" section** - Mandatory section at the end of EVERY created file
  - Lists all sources with URLs and brief descriptions
  - Format:
    ```markdown
    ## Источники
    
    1. [Название источника](URL) - краткое описание
    2. [Другой источник](URL) - краткое описание
    ```

- **Additional materials** - Optional "См. также" section for supplementary resources

This ensures all knowledge base entries maintain proper attribution and traceability.

### Connection Descriptions (Связи)

- Agent must add links only to EXISTING KB files (not those created in the same run).
- Each link MUST include a meaningful description (1–2 sentences) explaining the nature of the connection: similarity/difference, dependency, part-whole, alternative, sequence, overlapping concepts.
- Avoid generic placeholders like “Связанная тема”.

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
