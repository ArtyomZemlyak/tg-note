# Проверка доступности Docling и сохранение MCP JSON файлов

## Обзор

Система проверки доступности Docling работает на нескольких уровнях и тесно связана с механизмом сохранения MCP JSON конфигураций. В Docker режиме используются дополнительные проверки для определения окружения.

## Механизм проверки доступности

### 1. Проверка на уровне настроек (`FileProcessor.is_available()`)

Метод `FileProcessor.is_available()` в `src/processor/file_processor.py` проверяет доступность Docling:

```python
def is_available(self) -> bool:
    """
    Check if Docling processing is available and enabled.
    """
    if not self.settings.is_media_processing_enabled():
        return False
    if not self.docling_config.enabled:
        return False

    if self.docling_config.use_mcp():
        return self._docling_server_spec is not None

    if self.docling_config.use_local():
        return self.converter is not None

    return False
```

**Важно:** Для MCP режима проверяется только наличие спецификации сервера в реестре (`_docling_server_spec is not None`), но **не** проверяется фактическое подключение к серверу. Подключение происходит лениво при первом использовании.

### 2. Определение URL в Docker режиме (`DoclingMCPSettings.resolve_url()`)

Метод `resolve_url()` в `config/settings.py` определяет URL для подключения к Docling MCP серверу:

```python
def resolve_url(self) -> Optional[str]:
    """Resolve the effective MCP URL for Docling based on configuration and environment."""
    if self.transport != "sse":
        return None

    if self.url:
        return self.url

    env_url = os.getenv("DOCLING_MCP_URL")
    if env_url:
        return env_url

    try:
        if Path("/.dockerenv").exists():
            return self.docker_url  # http://docling-mcp:8077/sse
    except Exception:
        pass

    return self.host_url  # http://127.0.0.1:8077/sse
```

**Проверка Docker окружения:**
- Проверяется наличие файла `/.dockerenv` для определения Docker контейнера
- В Docker используется `docker_url` (по умолчанию `http://docling-mcp:8077/sse`)
- На хосте используется `host_url` (по умолчанию `http://127.0.0.1:8077/sse`)

### 3. Фактическое подключение к серверу (`MCPClient.connect()`)

Подключение происходит при первом использовании через `_get_docling_client()`:

```python
async def _get_docling_client(self) -> Optional[MCPClient]:
    """Ensure MCP client for Docling is connected."""
    if not self._registry_client or not self._docling_server_spec:
        return None

    if self._docling_client and self._docling_client.is_connected:
        return self._docling_client

    client = await self._registry_client.connect_to_server(self._docling_server_spec)
    if client:
        self._docling_client = client
    return client
```

При подключении `MCPClient.connect()`:
1. Создает транспорт (SSE/HTTP или stdio) на основе конфигурации
2. Вызывает `fastmcp.Client.__aenter__()` для установления соединения
3. Проверяет `_client.is_connected()` для подтверждения подключения
4. Загружает список доступных инструментов через `list_tools()`

**Ошибки подключения** логируются, но не блокируют инициализацию `FileProcessor`.

## Сохранение MCP JSON файлов

### 1. Создание спецификации Docling (`ensure_docling_mcp_spec()`)

Функция `ensure_docling_mcp_spec()` в `src/mcp/docling_integration.py` создает/обновляет JSON файл со спецификацией Docling MCP сервера:

```python
def ensure_docling_mcp_spec(
    docling_settings: DoclingSettings, servers_dir: Optional[Path] = None
) -> Optional[Path]:
    """
    Ensure Docling MCP server specification file exists/updated.
    """
    spec = _build_docling_mcp_spec(docling_settings)
    if spec is None:
        return None

    if servers_dir is None:
        servers_dir = Path("data/mcp_servers")

    servers_dir.mkdir(parents=True, exist_ok=True)

    spec_path = servers_dir / f"{spec['name']}.json"
    _write_json_if_changed(spec_path, spec)
    return spec_path
```

**Когда вызывается:**
1. При старте MCP Hub (`src/mcp/mcp_hub_server.py:311`)
2. При изменении настроек Docling через Telegram бота (`src/bot/settings_handlers.py:43`)
3. При инициализации `FileProcessor` (`src/processor/file_processor.py:59`)

### 2. Формат JSON файла (`data/mcp_servers/docling.json`)

Пример конфигурации для Docker режима:

```json
{
  "name": "docling",
  "description": "Docling document processing MCP server",
  "transport": "sse",
  "enabled": true,
  "url": "http://docling-mcp:8077/sse",
  "timeout": null
}
```

Для stdio режима:

```json
{
  "name": "docling",
  "description": "Docling document processing MCP server",
  "transport": "stdio",
  "enabled": true,
  "command": "python3",
  "args": ["-m", "docling_mcp.servers.mcp_server"],
  "env": null,
  "working_dir": null,
  "timeout": null
}
```

### 3. Генерация конфигурации для Qwen (`QwenMCPConfigGenerator`)

Для Qwen CLI генерируется отдельный файл `~/.qwen/settings.json`:

```python
def _generate_docling_config(self) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Generate configuration for Docling MCP server when available/enabled."""
    # ...
    spec = build_docling_mcp_spec(docling_settings)
    if spec is None or not spec.get("enabled", True):
        return None
    # ...
```

**Формат для Qwen:**

```json
{
  "mcpServers": {
    "docling": {
      "url": "http://docling-mcp:8077/sse",
      "timeout": 99999,
      "trust": true,
      "description": "Docling document processing MCP server"
    }
  },
  "allowMCPServers": ["mcp-hub", "docling"]
}
```

## Связь между проверкой доступности и сохранением JSON

### Последовательность инициализации

1. **Старт приложения:**
   - `ensure_docling_mcp_spec()` создает `data/mcp_servers/docling.json`
   - `MCPServerRegistry.discover_servers()` загружает все JSON файлы из `data/mcp_servers/`
   - `FileProcessor._setup_docling_mcp()` инициализирует реестр и находит спецификацию

2. **Проверка доступности:**
   - `FileProcessor.is_available()` проверяет наличие `_docling_server_spec`
   - Фактическое подключение происходит лениво при первом использовании

3. **Генерация для Qwen:**
   - `QwenMCPConfigGenerator._generate_docling_config()` читает настройки
   - Использует `build_docling_mcp_spec()` для получения спецификации
   - Сохраняет в `~/.qwen/settings.json`

### Особенности Docker режима

**Определение Docker окружения:**
- Проверка `/.dockerenv` в `resolve_url()`
- Использование Docker URL (`http://docling-mcp:8077/sse`)

**Проверка доступности сервера:**
- В Docker режиме сервер может быть недоступен при старте бота
- `is_available()` возвращает `True`, если спецификация найдена в реестре
- Фактическая проверка подключения происходит при первом использовании
- Ошибки подключения логируются, но не блокируют работу

**Синхронизация конфигураций:**
- `data/mcp_servers/docling.json` используется MCP Hub и ботом
- `~/.qwen/settings.json` используется Qwen CLI
- Оба файла обновляются при изменении настроек Docling

## Рекомендации

1. **Проверка доступности сервера:**
   - Используйте `FileProcessor.is_available()` для проверки конфигурации
   - Для проверки фактического подключения используйте `await client.connect()`
   - Обрабатывайте ошибки подключения при обработке файлов

2. **Docker режим:**
   - Убедитесь, что контейнер `docling-mcp` запущен
   - Проверьте логи: `docker-compose logs docling-mcp`
   - Проверьте доступность: `curl http://docling-mcp:8077/sse`

3. **Отладка:**
   - Проверьте наличие `data/mcp_servers/docling.json`
   - Проверьте содержимое файла (URL, transport, enabled)
   - Проверьте логи MCP Hub и бота на наличие ошибок подключения
