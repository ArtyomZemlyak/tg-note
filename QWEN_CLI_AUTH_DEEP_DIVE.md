# Глубокий анализ аутентификации qwen-code CLI

## Дата анализа
2025-10-02

## Резюме исследования

**Ключевой вывод:** Qwen OAuth **НЕВОЗМОЖНО** обойти в headless окружении через простое подстановление credentials файла. Система требует ВАЛИДНЫЕ токены от реального OAuth flow.

## 🔍 Детальный анализ исходного кода

### 1. Архитектура аутентификации

#### Файлы и их роли:

```
~/.qwen/
├── settings.json          # Настройки CLI (auth method)
├── oauth_creds.json       # OAuth credentials (access_token, refresh_token)
└── oauth_creds.lock       # Lock файл для синхронизации токенов
```

#### Основные компоненты:

**A. `qwenOAuth2.ts` - OAuth2 клиент**
- Реализует полный Device Flow согласно RFC 8628
- Использует PKCE (Proof Key for Code Exchange) для безопасности
- Endpoints:
  - Device code: `https://chat.qwen.ai/api/v1/oauth2/device/code`
  - Token: `https://chat.qwen.ai/api/v1/oauth2/token`
- Client ID: `f0304373b74a44d2b584a3fb70ca9e56` (hardcoded)

**B. `sharedTokenManager.ts` - Управление токенами**
- Singleton класс для cross-process синхронизации
- Файловый lock механизм для предотвращения race conditions
- Автоматический refresh токенов при истечении
- Валидация токенов перед использованием

**C. `auth.ts` - Валидация методов аутентификации**
```typescript
export enum AuthType {
  LOGIN_WITH_GOOGLE = 'oauth-personal',
  USE_GEMINI = 'gemini-api-key',
  USE_VERTEX_AI = 'vertex-ai',
  CLOUD_SHELL = 'cloud-shell',
  USE_OPENAI = 'openai',
  QWEN_OAUTH = 'qwen-oauth',
}
```

### 2. OAuth Device Flow (как это работает)

#### Шаг 1: Инициация Device Authorization
```typescript
// Генерация PKCE пары
const { code_verifier, code_challenge } = generatePKCEPair();

// Запрос device code
POST https://chat.qwen.ai/api/v1/oauth2/device/code
Body: {
  client_id: "f0304373b74a44d2b584a3fb70ca9e56",
  scope: "openid profile email model.completion",
  code_challenge: <SHA256 hash>,
  code_challenge_method: "S256"
}

Response: {
  device_code: "<unique_device_code>",
  user_code: "<короткий код для пользователя>",
  verification_uri: "https://chat.qwen.ai/device",
  verification_uri_complete: "<URL с кодом>",
  expires_in: <секунды>
}
```

#### Шаг 2: Открытие браузера
```typescript
// Попытка открыть браузер
await open(deviceAuth.verification_uri_complete);

// Если не удалось - показать URL пользователю
console.log('Visit this URL: ', verification_uri_complete);
```

**⚠️ КРИТИЧНО:** Именно здесь происходит **блокировка в headless окружении**

#### Шаг 3: Polling для токена
```typescript
// Опрос сервера каждые 2-10 секунд
while (attempt < maxAttempts) {
  const response = await pollDeviceToken({
    device_code,
    code_verifier
  });
  
  if (response.access_token) {
    // Успех! Сохраняем токены
    saveCredentials(response);
    break;
  }
  
  if (response.status === 'pending') {
    // Ожидание авторизации пользователем
    await sleep(pollInterval);
    continue;
  }
}
```

#### Шаг 4: Обмен device_code на токены
```typescript
POST https://chat.qwen.ai/api/v1/oauth2/token
Body: {
  grant_type: "urn:ietf:params:oauth:grant-type:device_code",
  client_id: "f0304373b74a44d2b584a3fb70ca9e56",
  device_code: "<from step 1>",
  code_verifier: "<from PKCE>"
}

Success Response: {
  access_token: "<JWT token>",
  refresh_token: "<refresh token>",
  token_type: "Bearer",
  expires_in: 3600,
  resource_url: "https://chat.qwen.ai"
}
```

### 3. Структура Credentials файла

**Файл:** `~/.qwen/oauth_creds.json`

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "v1.MQq...",
  "token_type": "Bearer",
  "expiry_date": 1727891234567,
  "resource_url": "https://chat.qwen.ai"
}
```

**Обязательные поля:**
```typescript
interface QwenCredentials {
  access_token: string;      // JWT токен для API вызовов
  refresh_token: string;     // Для обновления access_token
  token_type: string;        // Обычно "Bearer"
  expiry_date: number;       // Unix timestamp в миллисекундах
  resource_url?: string;     // API endpoint
}
```

**Валидация credentials:**
```typescript
function validateCredentials(data: unknown): QwenCredentials {
  const requiredFields = ['access_token', 'refresh_token', 'token_type'];
  
  for (const field of requiredFields) {
    if (!creds[field] || typeof creds[field] !== 'string') {
      throw new Error(`Invalid credentials: missing ${field}`);
    }
  }
  
  if (!creds.expiry_date || typeof creds.expiry_date !== 'number') {
    throw new Error('Invalid credentials: missing expiry_date');
  }
  
  return creds as QwenCredentials;
}
```

### 4. Token Refresh механизм

**Когда происходит refresh:**
- Токен истекает (в пределах 30 секунд до expiry_date)
- Force refresh запрошен
- При каждом API вызове проверяется валидность

**Процесс refresh:**
```typescript
async refreshAccessToken(): Promise<TokenRefreshResponse> {
  if (!this.credentials.refresh_token) {
    throw new Error('No refresh token available');
  }

  POST https://chat.qwen.ai/api/v1/oauth2/token
  Body: {
    grant_type: "refresh_token",
    refresh_token: this.credentials.refresh_token,
    client_id: "f0304373b74a44d2b584a3fb70ca9e56"
  }

  Response: {
    access_token: "<new access token>",
    token_type: "Bearer",
    expires_in: 3600,
    refresh_token: "<new refresh token>" // опционально
  }
}
```

**Обработка ошибок refresh:**
```typescript
if (response.status === 400) {
  // Refresh token истёк или невалиден
  await clearQwenCredentials();
  throw new CredentialsClearRequiredError(
    "Refresh token expired or invalid. Please use '/auth' to re-authenticate."
  );
}
```

### 5. Shared Token Manager (критическая деталь)

**Зачем нужен:**
- Синхронизация токенов между несколькими процессами qwen
- Предотвращение одновременных refresh запросов
- Кэширование валидных токенов в памяти

**Файловая блокировка:**
```typescript
// Lock файл: ~/.qwen/oauth_creds.lock
async acquireLock(lockPath: string): Promise<void> {
  const lockId = randomUUID();
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      // Атомарное создание lock файла
      await fs.writeFile(lockPath, lockId, { flag: 'wx' });
      return; // Лок получен
    } catch (error) {
      if (error.code === 'EEXIST') {
        // Файл существует, проверяем на stale lock
        const stats = await fs.stat(lockPath);
        if (Date.now() - stats.mtimeMs > LOCK_TIMEOUT_MS) {
          // Удаляем устаревший lock
          await fs.unlink(lockPath);
          continue;
        }
        // Ждём и повторяем
        await sleep(attemptInterval);
      }
    }
  }
  
  throw new TokenManagerError('Failed to acquire lock');
}
```

**Проверка и refresh:**
```typescript
async getValidCredentials(qwenClient): Promise<QwenCredentials> {
  // 1. Проверить файл на изменения (другой процесс мог обновить)
  await checkAndReloadIfNeeded(qwenClient);
  
  // 2. Если токен валиден - вернуть из кэша
  if (this.isTokenValid(this.memoryCache.credentials)) {
    return this.memoryCache.credentials;
  }
  
  // 3. Получить lock для refresh
  await acquireLock(lockPath);
  
  // 4. Double-check после получения lock
  await forceFileCheck(qwenClient);
  if (this.isTokenValid(this.memoryCache.credentials)) {
    return this.memoryCache.credentials;
  }
  
  // 5. Выполнить refresh
  const response = await qwenClient.refreshAccessToken();
  
  // 6. Сохранить новые credentials
  await saveCredentialsToFile(credentials);
  
  // 7. Освободить lock
  await releaseLock(lockPath);
  
  return credentials;
}
```

## 🧪 Эксперименты с обходом

### Попытка 1: Создание dummy credentials

**Что сделали:**
```bash
cat > ~/.qwen/oauth_creds.json << 'EOF'
{
  "access_token": "dummy_access_token",
  "refresh_token": "dummy_refresh_token",
  "token_type": "Bearer",
  "expiry_date": 9999999999999,
  "resource_url": "https://chat.qwen.ai"
}
EOF

cat > ~/.qwen/settings.json << 'EOF'
{
  "authMethod": "qwen-oauth",
  "security": {
    "auth": {
      "selectedType": "qwen-oauth"
    }
  }
}
EOF
```

**Результат:**
```
Error: Refresh token expired or invalid. Please use '/auth' to re-authenticate.
```

**Почему не сработало:**
1. CLI читает credentials файл ✅
2. Проверяет формат ✅
3. Пытается использовать токен для API запроса ❌
4. Сервер отвергает невалидный токен
5. CLI пытается сделать refresh ❌
6. Refresh тоже не работает (невалидный refresh_token)
7. CLI очищает credentials и требует re-auth

### Попытка 2: Получить реальные токены из другой машины

**Теоретический подход:**
```bash
# На машине с браузером:
qwen  # Пройти OAuth
cat ~/.qwen/oauth_creds.json > tokens.json

# На headless машине:
cat tokens.json > ~/.qwen/oauth_creds.json
```

**Почему это НЕБЕЗОПАСНО и НЕ РЕКОМЕНДУЕТСЯ:**

1. **Безопасность:**
   - Токены - это credentials, аналогичные паролям
   - Передача credentials между машинами нарушает безопасность
   - Refresh токены долгоживущие, могут быть скомпрометированы

2. **Технические проблемы:**
   - Токены могут быть привязаны к IP/fingerprint браузера
   - Concurrent использование одного refresh_token может вызвать инвалидацию
   - Race conditions при синхронизации между машинами

3. **Нарушение Terms of Service:**
   - OAuth токены предназначены для конкретного устройства/сессии
   - Sharing credentials между пользователями/устройствами запрещён

### Попытка 3: Реверс-инженеринг OAuth flow для headless

**Что нужно было бы сделать:**
1. Эмулировать браузер (Puppeteer/Selenium)
2. Автоматизировать вход на qwen.ai
3. Перехватить authorization code
4. Обменять на токены

**Проблемы:**
- Требуется логин/пароль пользователя (или captcha solving)
- Нарушение Terms of Service
- Хрупкое решение (изменения в UI ломают автоматизацию)
- Усложнение инфраструктуры

## ✅ Рабочие решения для headless окружения

### Решение 1: OpenAI-совместимый API (РЕКОМЕНДУЕТСЯ)

**Преимущества:**
- ✅ Работает без браузера
- ✅ Простая настройка через env переменные
- ✅ Есть бесплатные провайдеры

**Реализация:**

```bash
# Установка qwen-code
npm install -g @qwen-code/qwen-code@latest

# Настройка с OpenRouter (бесплатно 1000 req/day)
export OPENAI_API_KEY="sk-or-v1-..."
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_MODEL="qwen/qwen3-coder:free"

# Использование в non-interactive режиме
echo "your prompt" | qwen -p "process this"
```

**Настройка settings.json:**
```json
{
  "authMethod": "openai",
  "security": {
    "auth": {
      "selectedType": "openai"
    }
  }
}
```

**Бесплатные провайдеры:**

1. **OpenRouter** (международный):
   ```bash
   export OPENAI_API_KEY="sk-or-v1-YOUR_KEY"
   export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
   export OPENAI_MODEL="qwen/qwen3-coder:free"
   ```
   - 1000 запросов/день бесплатно
   - Регистрация: https://openrouter.ai/

2. **ModelScope** (Китай):
   ```bash
   export OPENAI_API_KEY="YOUR_MODELSCOPE_KEY"
   export OPENAI_BASE_URL="https://api-inference.modelscope.cn/v1"
   export OPENAI_MODEL="Qwen/Qwen3-Coder-480B-A35B-Instruct"
   ```
   - 2000 запросов/день бесплатно
   - Регистрация: https://modelscope.cn/

3. **Alibaba Cloud ModelStudio**:
   ```bash
   export OPENAI_API_KEY="YOUR_DASHSCOPE_KEY"
   export OPENAI_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
   export OPENAI_MODEL="qwen3-coder-plus"
   ```

### Решение 2: Использовать QwenCodeAgent вместо CLI

**В вашем проекте уже есть готовое решение:**

```yaml
# config.yaml
AGENT_TYPE: "qwen_code"  # Вместо "qwen_code_cli"
AGENT_MODEL: "qwen-max"
```

```bash
# .env
OPENAI_API_KEY=your_openai_compatible_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

**Преимущества:**
- ✅ Не требует qwen CLI
- ✅ Прямая работа с API
- ✅ Уже интегрировано в ваш проект
- ✅ Fallback на StubAgent при проблемах

### Решение 3: Gemini API Key

**Если у вас есть доступ к Gemini:**
```bash
export GEMINI_API_KEY="your_gemini_api_key"
```

```json
{
  "authMethod": "gemini-api-key",
  "security": {
    "auth": {
      "selectedType": "gemini-api-key"
    }
  }
}
```

## 📊 Сравнение методов аутентификации

| Метод | Headless | Бесплатно | Лимиты/день | Настройка |
|-------|----------|-----------|-------------|-----------|
| **Qwen OAuth** | ❌ | ✅ | 2000 req | Браузер требуется |
| **OpenAI API** | ✅ | ⚠️ | Зависит | Env vars |
| **OpenRouter** | ✅ | ✅ | 1000 req | Env vars |
| **ModelScope** | ✅ | ✅ | 2000 req | Env vars |
| **Gemini API** | ✅ | ⚠️ | Varies | Env vars |

## 🔐 Безопасность credentials

### Permissions на файлы:
```bash
chmod 700 ~/.qwen                    # Только владелец
chmod 600 ~/.qwen/oauth_creds.json  # Только владелец, чтение/запись
```

### Что НЕ делать:
- ❌ НЕ коммитить credentials в git
- ❌ НЕ передавать токены между машинами
- ❌ НЕ хранить в plaintext (qwen хранит, но файл защищён permissions)
- ❌ НЕ шарить refresh_token между процессами на разных машинах

### Best practices:
- ✅ Использовать environment variables для API ключей
- ✅ Использовать .env файлы (не коммитить в git)
- ✅ Регулярно ротировать API ключи
- ✅ Использовать отдельные ключи для dev/prod

## 🎯 Рекомендации для вашего проекта

### Краткосрочное решение (сейчас):

```yaml
# config.yaml
AGENT_TYPE: "qwen_code"  # Использовать Python агент вместо CLI
AGENT_MODEL: "qwen-max"
```

```bash
# .env
OPENAI_API_KEY=sk-or-v1-YOUR_OPENROUTER_KEY
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=qwen/qwen3-coder:free
```

**Шаги:**
1. Зарегистрироваться на OpenRouter: https://openrouter.ai/
2. Получить API ключ
3. Добавить в `.env`
4. Изменить `AGENT_TYPE` в config.yaml
5. Протестировать

### Долгосрочное решение:

**Опция A: Гибридный подход**
- Development (с браузером): использовать Qwen OAuth для лучшего DX
- Production/CI (headless): использовать OpenAI-compatible API

```python
# Автоматический выбор на основе окружения
import os

if os.environ.get('DISPLAY') or os.environ.get('BROWSER'):
    # Локальная разработка - можно использовать qwen_code_cli
    agent_type = "qwen_code_cli"
else:
    # Headless окружение - использовать qwen_code
    agent_type = "qwen_code"
```

**Опция B: Всегда использовать API**
- Проще в поддержке
- Единый подход для всех окружений
- Минимум зависимостей

## 📝 Выводы

### Что узнали:

1. **OAuth Device Flow требует браузер** - это не обходится простыми хаками
2. **Credentials файл можно создать вручную**, но нужны ВАЛИДНЫЕ токены
3. **Refresh mechanism** требует валидный refresh_token от настоящего OAuth flow
4. **SharedTokenManager** делает невозможным простое мошенничество с токенами
5. **OpenAI-compatible API** - единственное надёжное решение для headless

### Итоговая рекомендация:

**🎯 Использовать OpenRouter + QwenCodeAgent для headless окружений**

```bash
# Setup (один раз)
npm install -g @qwen-code/qwen-code@latest  # Если нужен CLI
# Зарегистрироваться на https://openrouter.ai/

# В проекте (.env)
OPENAI_API_KEY=sk-or-v1-YOUR_KEY
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=qwen/qwen3-coder:free

# В config.yaml
AGENT_TYPE=qwen_code  # Не qwen_code_cli!
```

**Преимущества этого подхода:**
- ✅ Работает в любом окружении
- ✅ Бесплатный tier доступен
- ✅ Простая настройка
- ✅ Надёжно и безопасно
- ✅ Уже поддерживается вашим кодом

## 🔗 Полезные ссылки

- **qwen-code GitHub:** https://github.com/QwenLM/qwen-code
- **OpenRouter:** https://openrouter.ai/
- **ModelScope:** https://modelscope.cn/
- **OAuth 2.0 Device Flow (RFC 8628):** https://tools.ietf.org/html/rfc8628
- **PKCE (RFC 7636):** https://tools.ietf.org/html/rfc7636

## 📋 Checklist для внедрения

- [ ] Выбрать провайдера API (OpenRouter рекомендуется)
- [ ] Зарегистрироваться и получить API ключ
- [ ] Добавить credentials в `.env` (не коммитить!)
- [ ] Обновить `config.yaml` (AGENT_TYPE: "qwen_code")
- [ ] Протестировать в headless окружении
- [ ] Документировать процесс для команды
- [ ] Настроить мониторинг использования API
- [ ] Настроить алерты на превышение лимитов

---

**Дата:** 2025-10-02  
**Исследователь:** AI Assistant  
**Статус:** ✅ Завершено
