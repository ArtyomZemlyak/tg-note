# Быстрый старт: qwen-cli в headless окружении

## ⚡ TL;DR

**Проблема:** `qwen` CLI требует браузер для OAuth аутентификации → не работает в headless/remote окружениях.

**Решение:** Использовать OpenAI-совместимый API вместо Qwen OAuth.

## 🚀 Решение за 5 минут

### Вариант 1: С OpenRouter (бесплатно, рекомендуется)

```bash
# 1. Зарегистрироваться на https://openrouter.ai/
# 2. Получить API ключ

# 3. Установить qwen-code CLI (если ещё не установлен)
npm install -g @qwen-code/qwen-code@latest

# 4. Настроить переменные окружения
export OPENAI_API_KEY="sk-or-v1-YOUR_OPENROUTER_KEY"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_MODEL="qwen/qwen3-coder:free"

# 5. Протестировать
echo "Hello world" | qwen -p "Translate to Russian"
```

### Вариант 2: Использовать QwenCodeAgent (для Python проекта)

```yaml
# config.yaml
AGENT_TYPE: "qwen_code"  # НЕ "qwen_code_cli"!
AGENT_MODEL: "qwen-max"
```

```bash
# .env
OPENAI_API_KEY=sk-or-v1-YOUR_OPENROUTER_KEY
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

```bash
# Запустить
python main.py
```

## 📋 Бесплатные провайдеры

| Провайдер | Лимит/день | Регистрация | Регион |
|-----------|-----------|-------------|---------|
| **OpenRouter** | 1000 req | https://openrouter.ai/ | 🌍 Все |
| **ModelScope** | 2000 req | https://modelscope.cn/ | 🇨🇳 Китай |
| **Alibaba Cloud** | Varies | https://dashscope.aliyuncs.com/ | 🇨🇳 Китай |

## ❌ Что НЕ работает

- ❌ Просто создать credentials файл с dummy данными
- ❌ Скопировать OAuth токены с другой машины (небезопасно, ненадёжно)
- ❌ Запустить браузер через X11 forwarding (сложно, хрупко)

## ✅ Что работает

- ✅ OpenAI-совместимый API (любой провайдер)
- ✅ Python агент вместо CLI (уже в проекте)
- ✅ Gemini API Key (если есть доступ)

## 🔧 Полная документация

- **Общий обзор:** [QWEN_CLI_LOGIN_INVESTIGATION.md](./QWEN_CLI_LOGIN_INVESTIGATION.md)
- **Технический deep dive:** [QWEN_CLI_AUTH_DEEP_DIVE.md](./QWEN_CLI_AUTH_DEEP_DIVE.md)

## 🆘 Troubleshooting

### Ошибка: "Please set an Auth method"
```bash
# Решение: настроить env переменные
export OPENAI_API_KEY="your_key"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
```

### Ошибка: "Refresh token expired or invalid"
```bash
# Решение: переключиться на OpenAI API метод
export OPENAI_API_KEY="your_key"
# Удалить старые credentials
rm ~/.qwen/oauth_creds.json
```

### qwen CLI вообще не запускается
```bash
# Проверить установку
which qwen
qwen --version

# Переустановить
npm uninstall -g @qwen-code/qwen-code
npm install -g @qwen-code/qwen-code@latest
```

## 💡 Best Practice

**Для локальной разработки (с браузером):**
```bash
qwen  # Использовать Qwen OAuth - удобнее
```

**Для headless/CI/remote:**
```bash
# .env
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Использовать через env vars
```

---

**Дата:** 2025-10-02  
**Статус:** ✅ Проверено и работает
