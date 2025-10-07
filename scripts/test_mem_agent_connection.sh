#!/bin/bash
# Скрипт для проверки подключения mem-agent

set -e

echo "========================================="
echo "Проверка mem-agent MCP сервера"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "src/agents/mcp/mem_agent_server.py" ]; then
    echo -e "${RED}❌ Ошибка: Запустите скрипт из корня проекта (/workspace)${NC}"
    exit 1
fi

echo -e "${YELLOW}1. Проверка конфигурации STDIO...${NC}"
if [ -f "$HOME/.qwen/settings.json" ]; then
    echo -e "${GREEN}✅ Конфигурация найдена: ~/.qwen/settings.json${NC}"
    echo "Содержимое:"
    cat ~/.qwen/settings.json | head -20
    echo ""
else
    echo -e "${RED}❌ Конфигурация не найдена${NC}"
    echo "Создайте конфигурацию с помощью:"
    echo "  cp ~/.qwen/settings.json ~/.qwen/settings.json"
    exit 1
fi

echo -e "${YELLOW}2. Проверка файлов сервера...${NC}"
if [ -f "src/agents/mcp/mem_agent_server.py" ]; then
    echo -e "${GREEN}✅ STDIO сервер найден${NC}"
else
    echo -e "${RED}❌ STDIO сервер не найден${NC}"
fi

if [ -f "src/agents/mcp/mem_agent_server_http.py" ]; then
    echo -e "${GREEN}✅ HTTP сервер найден${NC}"
else
    echo -e "${RED}❌ HTTP сервер не найден${NC}"
fi
echo ""

echo -e "${YELLOW}3. Проверка Python модулей...${NC}"
if python3 -c "from src.mem_agent.storage import MemoryStorage" 2>/dev/null; then
    echo -e "${GREEN}✅ MemoryStorage модуль загружается${NC}"
else
    echo -e "${RED}❌ Не удается загрузить MemoryStorage${NC}"
    echo "Возможно, не хватает зависимостей"
fi
echo ""

echo -e "${YELLOW}4. Проверка STDIO сервера...${NC}"
echo "Отправка тестового запроса..."

# Test stdio server with timeout
RESPONSE=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | timeout 3 python3 src/agents/mcp/mem_agent_server.py 2>/dev/null | head -1)

if [ -n "$RESPONSE" ]; then
    echo -e "${GREEN}✅ STDIO сервер отвечает${NC}"
    echo "Ответ: $RESPONSE"
else
    echo -e "${RED}❌ STDIO сервер не отвечает${NC}"
    echo "Попробуйте запустить вручную:"
    echo "  python3 src/agents/mcp/mem_agent_server.py"
fi
echo ""

echo -e "${YELLOW}5. Проверка HTTP сервера...${NC}"
# Check if HTTP server is running
if curl -s http://127.0.0.1:8765/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ HTTP сервер запущен и отвечает${NC}"
    echo "URL: http://127.0.0.1:8765/sse"
else
    echo -e "${YELLOW}⚠️  HTTP сервер не запущен${NC}"
    echo "Для запуска HTTP сервера:"
    echo "  python3 src/agents/mcp/mem_agent_server_http.py"
fi
echo ""

echo "========================================="
echo "Итоги проверки"
echo "========================================="
echo ""
echo "Текущий режим: STDIO (по умолчанию)"
echo "Конфигурация: ~/.qwen/settings.json"
echo ""
echo "Следующие шаги:"
echo "1. Перезапустите qwen-code-cli"
echo "2. Проверьте статус mem-agent (должно быть 'Connected' с 3 tools)"
echo ""
echo "Если не работает:"
echo "- См. документацию: docs/MEM_AGENT_TRANSPORT_OPTIONS.md"
echo "- Попробуйте HTTP режим: cp ~/.qwen/settings-http.json ~/.qwen/settings.json"
echo "- Или см. полное руководство: MEM_AGENT_CONNECTIVITY_FIX.md"
echo ""