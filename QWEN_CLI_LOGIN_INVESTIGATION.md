# Исследование процесса аутентификации qwen-cli

## Дата исследования
2025-10-02

## Резюме
**qwen-cli требует аутентификацию через браузер для OAuth метода, что делает его непригодным для использования в headless/remote окружениях без настройки альтернативных методов аутентификации.**

## Детали исследования

### 1. Установка qwen-code CLI

✅ **Успешно установлено:**
```bash
npm install -g @qwen-code/qwen-code@latest
# Установлено: версия 0.0.14
# 490 пакетов установлено за 27 секунд
```

### 2. Методы аутентификации

qwen-code CLI поддерживает **3 метода аутентификации**:

#### A. Qwen OAuth (Рекомендуется разработчиками, НО требует браузер)

**Характеристики:**
- ✅ 2,000 запросов в день бесплатно
- ✅ 60 запросов в минуту
- ✅ Без лимитов на токены
- ✅ Автоматическое управление credentials
- ❌ **ТРЕБУЕТ БРАУЗЕР для аутентификации**

**Процесс:**
```bash
qwen  # Запускает интерактивный режим
# CLI автоматически открывает браузер
# Пользователь логинится через qwen.ai
# Credentials сохраняются в ~/.qwen/
```

**Проблема в headless окружении:**
- CLI пытается открыть браузер через системный вызов
- В remote/headless окружении браузер недоступен
- Невозможно пройти аутентификацию в автоматическом режиме

#### B. OpenAI-совместимый API (РАБОТАЕТ в headless)

**Характеристики:**
- ✅ Работает без браузера
- ✅ Настраивается через переменные окружения
- ⚠️ Требует API ключ от стороннего провайдера
- ⚠️ Может требовать оплаты (в зависимости от провайдера)

**Настройка:**
```bash
# Вариант 1: Переменные окружения
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # или другой endpoint
export OPENAI_MODEL="gpt-4"  # или другая модель

# Вариант 2: .env файл в проекте
echo "OPENAI_API_KEY=your_key" >> .env
echo "OPENAI_BASE_URL=https://api.openai.com/v1" >> .env
echo "OPENAI_MODEL=gpt-4" >> .env

# Вариант 3: settings.json
cat > ~/.qwen/settings.json << 'EOF'
{
  "authMethod": "openai"
}
EOF
```

**Бесплатные провайдеры для международных пользователей:**
- **OpenRouter**: до 1,000 бесплатных вызовов в день
  ```bash
  export OPENAI_API_KEY="your_openrouter_key"
  export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
  export OPENAI_MODEL="qwen/qwen3-coder:free"
  ```

- **Alibaba Cloud ModelStudio** (международный):
  ```bash
  export OPENAI_API_KEY="your_dashscope_key"
  export OPENAI_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
  export OPENAI_MODEL="qwen3-coder-plus"
  ```

**Для пользователей в Китае:**
- **ModelScope**: 2,000 бесплатных вызовов в день
  ```bash
  export OPENAI_API_KEY="your_modelscope_key"
  export OPENAI_BASE_URL="https://api-inference.modelscope.cn/v1"
  export OPENAI_MODEL="Qwen/Qwen3-Coder-480B-A35B-Instruct"
  ```

- **Alibaba Cloud Bailian**:
  ```bash
  export OPENAI_API_KEY="your_dashscope_key"
  export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
  export OPENAI_MODEL="qwen3-coder-plus"
  ```

#### C. Google Gemini API (альтернатива)

```bash
export GEMINI_API_KEY="your_gemini_key"
```

### 3. Результаты тестирования

#### Тест без аутентификации:
```bash
$ echo "test prompt" | qwen -p "Summarize this in one sentence"
# Ошибка: Please set an Auth method in your /home/ubuntu/.qwen/settings.json 
# or specify one of the following environment variables before running: 
# GEMINI_API_KEY, OPENAI_API_KEY, GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_GENAI_USE_GCA
```

**Вывод:** qwen-cli **не работает** без настроенной аутентификации.

### 4. Структура конфигурации

**Расположение файлов:**
```
~/.qwen/
├── settings.json     # Основные настройки
└── config.json       # Credentials (создается после OAuth аутентификации)
```

**Пример settings.json:**
```json
{
  "authMethod": "openai",
  "sessionTokenLimit": 32000,
  "experimental": {
    "vlmSwitchMode": "once",
    "visionModelPreview": true
  }
}
```

### 5. Файлы credentials после OAuth (НЕДОСТУПНО в headless)

После успешной OAuth аутентификации через браузер, qwen создает:
- `~/.qwen/config.json` - содержит OAuth tokens
- Токены автоматически обновляются
- **НО**: первоначальную аутентификацию НЕЛЬЗЯ провести без браузера

## Выводы и рекомендации

### ❌ Невозможно в headless окружении:
1. **Qwen OAuth аутентификация** - требует браузер для первоначального входа
2. **Передача файла config.json** - теоретически возможно, но:
   - OAuth токены привязаны к сессии и машине
   - Токены имеют срок действия
   - Безопасность: передача credentials между машинами небезопасна
   - Не рекомендуется разработчиками

### ✅ Возможные решения для headless окружения:

#### Решение 1: Использовать OpenAI-совместимый API (Рекомендуется)

**Преимущества:**
- ✅ Работает в любом окружении
- ✅ Не требует браузера
- ✅ Простая настройка через env переменные
- ✅ Есть бесплатные провайдеры

**Недостатки:**
- ⚠️ Требует регистрацию у стороннего провайдера
- ⚠️ Лимиты могут быть меньше чем у Qwen OAuth

**Реализация:**
```bash
# 1. Получить API ключ от одного из провайдеров:
#    - OpenRouter (1000 req/day бесплатно)
#    - ModelScope (2000 req/day для Китая)
#    - Alibaba Cloud

# 2. Настроить переменные окружения
export OPENAI_API_KEY="your_key"
export OPENAI_BASE_URL="provider_url"
export OPENAI_MODEL="model_name"

# 3. Использовать qwen в non-interactive режиме
echo "your prompt" | qwen -p "process this"
```

#### Решение 2: Использовать альтернативу qwen-code

**Рассмотреть другие инструменты:**
- Использовать прямые API вызовы к Qwen API
- Использовать Python SDK для Qwen
- Кастомная реализация агента (как `QwenCodeAgent` в проекте)

#### Решение 3: Гибридный подход (текущая архитектура проекта)

**Что уже есть в проекте:**
```python
# src/agents/ содержит 3 типа агентов:
# 1. QwenCodeCLIAgent - использует qwen CLI (требует аутентификацию)
# 2. QwenCodeAgent - прямое использование Python API
# 3. StubAgent - базовая обработка без внешних зависимостей
```

**Рекомендация:**
- Использовать `QwenCodeAgent` вместо `QwenCodeCLIAgent` для remote окружений
- `QwenCodeAgent` не требует qwen CLI и может работать с API напрямую
- Настроить через `QWEN_API_KEY` или `OPENAI_API_KEY`

### Практические шаги для текущего проекта:

#### Вариант A: Использовать QwenCodeAgent (без CLI)

```yaml
# config.yaml
AGENT_TYPE: "qwen_code"  # вместо "qwen_code_cli"
AGENT_MODEL: "qwen-max"
```

```bash
# .env
QWEN_API_KEY=your_qwen_api_key
# или
OPENAI_API_KEY=your_openai_compatible_key
OPENAI_BASE_URL=https://provider.com/v1
```

#### Вариант B: Настроить OpenAI-совместимый API для qwen CLI

```yaml
# config.yaml
AGENT_TYPE: "qwen_code_cli"
AGENT_QWEN_CLI_PATH: "qwen"
```

```bash
# .env
OPENAI_API_KEY=your_key_from_openrouter_or_modelscope
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=qwen/qwen3-coder:free
```

#### Вариант C: Использовать StubAgent (для тестирования)

```yaml
# config.yaml
AGENT_TYPE: "stub"  # работает без внешних зависимостей
```

## Технические детали

### Архитектура qwen-code CLI:
- **Язык:** TypeScript/Node.js
- **Зависимости:** 490 npm пакетов
- **Основа:** Адаптация Google Gemini CLI
- **Оптимизация:** Специально для Qwen3-Coder моделей

### Возможности CLI:
- Code Understanding & Editing
- Workflow Automation  
- Vision Model Support
- TODO Planning
- Built-in tools: web search, git, github, shell

### Команды qwen CLI:
```bash
# Интерактивный режим (требует аутентификацию)
qwen

# Non-interactive режим
qwen -p "your prompt"
qwen -p "prompt" -y  # YOLO mode (auto-approve)

# Управление аутентификацией
qwen /auth  # переключить на OAuth (открывает браузер)

# Управление MCP серверами
qwen mcp
```

## Итоговые рекомендации

### Для headless/remote окружения (как текущее):

1. **НЕ использовать Qwen OAuth** - требует браузер, невозможно в headless
2. **НЕ пытаться передавать файлы credentials** - небезопасно и ненадежно
3. **Использовать один из рабочих методов:**
   
   **Приоритет 1:** OpenAI-совместимый API с бесплатным провайдером
   ```bash
   export OPENAI_API_KEY="openrouter_key"
   export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
   export OPENAI_MODEL="qwen/qwen3-coder:free"
   ```
   
   **Приоритет 2:** Использовать QwenCodeAgent вместо CLI
   ```yaml
   AGENT_TYPE: "qwen_code"
   ```
   
   **Приоритет 3:** StubAgent для базовой функциональности
   ```yaml
   AGENT_TYPE: "stub"
   ```

### Для локального development (с браузером):

1. **Использовать Qwen OAuth** - лучший бесплатный вариант
   ```bash
   qwen  # следовать инструкциям в браузере
   ```

2. **После аутентификации:**
   - Credentials сохраняются в `~/.qwen/config.json`
   - Автоматическое обновление токенов
   - 2000 запросов в день бесплатно

## Ссылки и ресурсы

- **GitHub:** https://github.com/QwenLM/qwen-code
- **Документация:** https://qwenlm.github.io/qwen-code-docs/
- **NPM:** https://www.npmjs.com/package/@qwen-code/qwen-code
- **Qwen.ai:** https://qwen.ai (для OAuth)
- **OpenRouter:** https://openrouter.ai (бесплатный tier)
- **ModelScope:** https://modelscope.cn (для Китая)

## Проверочный список для внедрения

- [ ] Решить какой метод аутентификации использовать
- [ ] Если OpenAI API: зарегистрироваться у провайдера и получить ключ
- [ ] Настроить переменные окружения (.env файл)
- [ ] Обновить config.yaml с правильным AGENT_TYPE
- [ ] Протестировать в non-interactive режиме
- [ ] Документировать процесс для команды
- [ ] Добавить инструкции в README проекта

## Заключение

**Основной вывод:** qwen-cli с Qwen OAuth **НЕ РАБОТАЕТ** в headless окружениях без браузера. 

**Решение:** Использовать OpenAI-совместимый API с бесплатными провайдерами (OpenRouter, ModelScope) или переключиться на `QwenCodeAgent` который не требует CLI.

Текущая архитектура проекта уже поддерживает оба варианта, нужно только правильно настроить конфигурацию.
