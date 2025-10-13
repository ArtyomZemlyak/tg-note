#!/bin/bash
# Скрипт для проверки подключения mem-agent в HTTP режиме
# Script for testing mem-agent HTTP connection

set -e

echo "========================================="
echo "Проверка mem-agent MCP сервера (HTTP)"
echo "Testing mem-agent MCP server (HTTP)"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "src/mcp/mcp_hub_server.py" ]; then
    echo -e "${RED}❌ Ошибка: Запустите скрипт из корня проекта (/workspace)${NC}"
    echo -e "${RED}❌ Error: Run script from project root (/workspace)${NC}"
    exit 1
fi

echo -e "${BLUE}=== 1. Проверка HTTP сервера / Checking HTTP server ===${NC}"
echo ""

# Check if MCP Hub server file exists
if [ -f "src/mcp/mcp_hub_server.py" ]; then
    echo -e "${GREEN}✅ MCP Hub сервер найден / MCP Hub server found${NC}"
    echo "   📄 src/agents/mcp/mcp_hub_server.py"
else
    echo -e "${RED}❌ MCP Hub сервер не найден / MCP Hub server not found${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}=== 2. Проверка конфигураций JSON MCP / Checking JSON MCP configs ===${NC}"
echo ""

# Find all settings.json files
FOUND_CONFIGS=0
HTTP_CONFIGS=0
STDIO_CONFIGS=0

# Check ~/.qwen/settings.json
if [ -f "$HOME/.qwen/settings.json" ]; then
    echo -e "${GREEN}✅ Найдена конфигурация / Found config: ~/.qwen/settings.json${NC}"
    FOUND_CONFIGS=$((FOUND_CONFIGS + 1))

    # Check if it contains HTTP format (url field)
    if grep -q '"url".*"http://127.0.0.1:8765/sse"' "$HOME/.qwen/settings.json"; then
        echo -e "${GREEN}   ✅ Формат: HTTP/SSE${NC}"
        echo -e "   📡 URL: http://127.0.0.1:8765/sse"
        HTTP_CONFIGS=$((HTTP_CONFIGS + 1))
    # Check if it contains stdio format (command field)
    elif grep -q '"command".*"python3"' "$HOME/.qwen/settings.json"; then
        echo -e "${YELLOW}   ⚠️  Формат: STDIO (устаревший)${NC}"
        echo -e "${YELLOW}   ⚠️  Format: STDIO (deprecated)${NC}"
        STDIO_CONFIGS=$((STDIO_CONFIGS + 1))
    else
        echo -e "${YELLOW}   ⚠️  Формат неизвестен / Unknown format${NC}"
    fi

    # Show mem-agent config snippet
    echo "   Содержимое mem-agent / mem-agent content:"
    python3 -c "import json; data = json.load(open('$HOME/.qwen/settings.json')); print('  ', json.dumps(data.get('mcpServers', {}).get('mem-agent', {}), indent=4, ensure_ascii=False))" 2>/dev/null || echo "   Failed to parse JSON"
    echo ""
fi

# Check for knowledge base configs
KB_CONFIGS=$(find knowledge_bases -name "settings.json" 2>/dev/null | head -5)
if [ -n "$KB_CONFIGS" ]; then
    while IFS= read -r config_file; do
        if [ -f "$config_file" ]; then
            echo -e "${GREEN}✅ Найдена конфигурация / Found config: $config_file${NC}"
            FOUND_CONFIGS=$((FOUND_CONFIGS + 1))

            # Check format
            if grep -q '"url".*"http://127.0.0.1:8765/sse"' "$config_file"; then
                echo -e "${GREEN}   ✅ Формат: HTTP/SSE${NC}"
                HTTP_CONFIGS=$((HTTP_CONFIGS + 1))
            elif grep -q '"command".*"python3"' "$config_file"; then
                echo -e "${YELLOW}   ⚠️  Формат: STDIO (устаревший)${NC}"
                STDIO_CONFIGS=$((STDIO_CONFIGS + 1))
            fi
            echo ""
        fi
    done <<< "$KB_CONFIGS"
fi

if [ $FOUND_CONFIGS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Конфигурации не найдены / No configs found${NC}"
    echo "   Создайте конфигурацию / Create config with:"
    echo "   python3 -m src.mcp.qwen_config_generator --http"
    echo ""
fi

echo "   📊 Статистика / Statistics:"
echo "      Всего конфигураций / Total configs: $FOUND_CONFIGS"
echo "      HTTP формат / HTTP format: $HTTP_CONFIGS"
echo "      STDIO формат / STDIO format: $STDIO_CONFIGS"
echo ""

if [ $STDIO_CONFIGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Обнаружены конфигурации в STDIO формате!${NC}"
    echo -e "${YELLOW}⚠️  STDIO configs detected!${NC}"
    echo "   Рекомендуется обновить на HTTP формат / Recommended to update to HTTP:"
    echo "   python3 -m src.mcp.qwen_config_generator --http"
    echo ""
fi

echo -e "${BLUE}=== 3. Проверка запуска MCP Hub / Testing MCP Hub startup ===${NC}"
echo ""

# Check Python dependencies
echo -e "${YELLOW}Проверка зависимостей / Checking dependencies...${NC}"
if python3 -c "from src.agents.mcp.memory.memory_storage import MemoryStorage" 2>/dev/null; then
    echo -e "${GREEN}✅ MemoryStorage модуль найден / MemoryStorage module found${NC}"
else
    echo -e "${RED}❌ MemoryStorage модуль не найден / MemoryStorage module not found${NC}"
    echo "   Установите зависимости / Install dependencies:"
    echo "   pip install -r requirements.txt"
fi

if python3 -c "import fastmcp" 2>/dev/null; then
    echo -e "${GREEN}✅ fastmcp модуль найден / fastmcp module found${NC}"
else
    echo -e "${RED}❌ fastmcp модуль не найден / fastmcp module not found${NC}"
    echo "   Установите / Install: pip install fastmcp"
fi
echo ""

echo -e "${BLUE}=== 4. Проверка HTTP подключения / Testing HTTP connection ===${NC}"
echo ""

# Check if HTTP server is running
if curl -s --connect-timeout 2 http://127.0.0.1:8765/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ HTTP сервер запущен и отвечает / HTTP server is running and responding${NC}"
    echo "   📡 URL: http://127.0.0.1:8765"
    echo "   🔌 SSE endpoint: http://127.0.0.1:8765/sse"

    # Try to get server info
    HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8765/health 2>/dev/null)
    if [ -n "$HEALTH_RESPONSE" ]; then
        echo "   ❤️  Health check: $HEALTH_RESPONSE"
    fi
    echo ""
else
    echo -e "${YELLOW}⚠️  MCP Hub сервер не запущен / MCP Hub is not running${NC}"
    echo ""
    echo "   Для запуска MCP Hub / To start MCP Hub:"
    echo "   ${GREEN}python3 -m src.mcp.mcp_hub_server${NC}"
    echo ""
    echo "   Или с параметрами / Or with parameters:"
    echo "   ${GREEN}python3 -m src.mcp.mcp_hub_server --port 8765 --host 127.0.0.1${NC}"
    echo ""
    echo "   В фоновом режиме / In background:"
    echo "   ${GREEN}nohup python3 -m src.mcp.mcp_hub_server > mcp_hub.log 2>&1 &${NC}"
    echo ""
fi

echo "========================================="
echo "Итоги проверки / Summary"
echo "========================================="
echo ""

if [ $HTTP_CONFIGS -gt 0 ]; then
    echo -e "${GREEN}✅ Найдены HTTP конфигурации: $HTTP_CONFIGS${NC}"
    echo -e "${GREEN}✅ HTTP configs found: $HTTP_CONFIGS${NC}"
else
    echo -e "${YELLOW}⚠️  HTTP конфигурации не найдены${NC}"
    echo -e "${YELLOW}⚠️  No HTTP configs found${NC}"
fi

if [ $STDIO_CONFIGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Устаревшие STDIO конфигурации: $STDIO_CONFIGS${NC}"
    echo -e "${YELLOW}⚠️  Deprecated STDIO configs: $STDIO_CONFIGS${NC}"
fi
echo ""

echo "📚 Документация / Documentation:"
echo "   • MCP Server Setup: docs_site/agents/mem-agent-setup.md"
echo "   • MCP Tools: docs_site/agents/mcp-tools.md"
echo "   • MCP Hub: src/mcp/mcp_hub_server.py"
echo "   • Config Generator: src/mcp/qwen_config_generator.py"
echo ""

echo "🔗 Полезные ссылки / Useful links:"
echo "   • MCP Protocol: https://modelcontextprotocol.io/"
echo "   • FastMCP: https://github.com/jlowin/fastmcp"
echo "   • SSE (Server-Sent Events): https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events"
echo ""

echo "📝 Следующие шаги / Next steps:"
if ! curl -s --connect-timeout 2 http://127.0.0.1:8765/health >/dev/null 2>&1; then
    echo "   1. Запустите MCP Hub / Start MCP Hub:"
    echo "      ${GREEN}python3 -m src.agents.mcp.mcp_hub_server${NC}"
fi
if [ $STDIO_CONFIGS -gt 0 ]; then
    echo "   2. Обновите конфигурации на HTTP / Update configs to HTTP:"
    echo "      ${GREEN}python3 -m src.mcp.qwen_config_generator --http${NC}"
fi
echo "   3. Перезапустите qwen-code-cli / Restart qwen-code-cli"
echo "   4. Проверьте статус mem-agent (должно быть 'Connected' с 3 tools)"
echo "      Check mem-agent status (should be 'Connected' with 3 tools)"
echo ""
