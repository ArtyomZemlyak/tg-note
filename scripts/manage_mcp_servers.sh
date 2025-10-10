#!/bin/bash
# ============================================================================
# MCP Servers Management Script
# ============================================================================
# Управление всеми MCP серверами с логированием
# Manage all MCP servers with logging
#
# Usage:
#   ./scripts/manage_mcp_servers.sh start [server_name]   - Start server(s)
#   ./scripts/manage_mcp_servers.sh stop [server_name]    - Stop server(s)
#   ./scripts/manage_mcp_servers.sh restart [server_name] - Restart server(s)
#   ./scripts/manage_mcp_servers.sh status                - Check status
#   ./scripts/manage_mcp_servers.sh logs [server_name]    - Show logs
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs/mcp_servers"
PID_DIR="$PROJECT_DIR/logs/mcp_servers/pids"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# ============================================================================
# Server Definitions
# ============================================================================

# Memory MCP Server (HTTP/SSE)
start_memory_server() {
    local PID_FILE="$PID_DIR/memory_mcp.pid"
    local LOG_FILE="$LOG_DIR/memory_mcp.log"
    
    if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        log_warn "Memory MCP server is already running (PID: $(cat "$PID_FILE"))"
        return 1
    fi
    
    log_info "Starting Memory MCP server..."
    
    nohup python3 -m src.agents.mcp.memory.memory_server_http \
        --host 127.0.0.1 \
        --port 8765 \
        --log-file "$LOG_FILE" \
        --log-level INFO \
        > "$LOG_DIR/memory_mcp_stdout.log" 2>&1 &
    
    echo $! > "$PID_FILE"
    sleep 2
    
    if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        log_info "Memory MCP server started (PID: $(cat "$PID_FILE"))"
        log_info "Log file: $LOG_FILE"
        log_info "URL: http://127.0.0.1:8765/sse"
        return 0
    else
        log_error "Memory MCP server failed to start"
        rm -f "$PID_FILE"
        log_error "Check logs: $LOG_FILE"
        return 1
    fi
}

stop_memory_server() {
    local PID_FILE="$PID_DIR/memory_mcp.pid"
    
    if [ ! -f "$PID_FILE" ]; then
        log_warn "Memory MCP server is not running"
        return 1
    fi
    
    local PID=$(cat "$PID_FILE")
    
    if ! ps -p $PID > /dev/null 2>&1; then
        log_warn "Memory MCP server (PID: $PID) is not running"
        rm -f "$PID_FILE"
        return 1
    fi
    
    log_info "Stopping Memory MCP server (PID: $PID)..."
    kill $PID
    
    # Wait for graceful shutdown (max 10 seconds)
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            log_info "Memory MCP server stopped"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        log_warn "Force killing Memory MCP server..."
        kill -9 $PID
        rm -f "$PID_FILE"
    fi
    
    log_info "Memory MCP server stopped"
    return 0
}

# ============================================================================
# Mem-Agent MCP Server
# ============================================================================

start_mem_agent_server() {
    local PID_FILE="$PID_DIR/mem_agent.pid"
    local LOG_FILE="$LOG_DIR/mem_agent.log"
    
    if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        log_warn "Mem-Agent MCP server is already running (PID: $(cat "$PID_FILE"))"
        return 1
    fi
    
    log_info "Starting Mem-Agent MCP server..."
    
    nohup python3 -m src.agents.mcp.memory.mem_agent_impl.mcp_server \
        --host 127.0.0.1 \
        --port 8766 \
        --log-file "$LOG_FILE" \
        --log-level INFO \
        > "$LOG_DIR/mem_agent_stdout.log" 2>&1 &
    
    echo $! > "$PID_FILE"
    sleep 2
    
    if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        log_info "Mem-Agent MCP server started (PID: $(cat "$PID_FILE"))"
        log_info "Log file: $LOG_FILE"
        log_info "URL: http://127.0.0.1:8766/sse"
        return 0
    else
        log_error "Mem-Agent MCP server failed to start"
        rm -f "$PID_FILE"
        log_error "Check logs: $LOG_FILE"
        return 1
    fi
}

stop_mem_agent_server() {
    local PID_FILE="$PID_DIR/mem_agent.pid"
    
    if [ ! -f "$PID_FILE" ]; then
        log_warn "Mem-Agent MCP server is not running"
        return 1
    fi
    
    local PID=$(cat "$PID_FILE")
    
    if ! ps -p $PID > /dev/null 2>&1; then
        log_warn "Mem-Agent MCP server (PID: $PID) is not running"
        rm -f "$PID_FILE"
        return 1
    fi
    
    log_info "Stopping Mem-Agent MCP server (PID: $PID)..."
    kill $PID
    
    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            log_info "Mem-Agent MCP server stopped"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        log_warn "Force killing Mem-Agent MCP server..."
        kill -9 $PID
        rm -f "$PID_FILE"
    fi
    
    log_info "Mem-Agent MCP server stopped"
    return 0
}

# ============================================================================
# vLLM Server for Mem-Agent
# ============================================================================

start_vllm_server() {
    local PID_FILE="$PID_DIR/vllm_server.pid"
    local LOG_FILE="$LOG_DIR/vllm_server.log"
    
    if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        log_warn "vLLM server is already running (PID: $(cat "$PID_FILE"))"
        return 1
    fi
    
    log_info "Starting vLLM server..."
    log_warn "Note: This requires GPU and vLLM installed"
    
    nohup python3 "$SCRIPT_DIR/start_vllm_server.py" \
        --model driaforall/mem-agent \
        --host 127.0.0.1 \
        --port 8001 \
        --log-dir "$LOG_DIR" \
        > "$LOG_DIR/vllm_server_wrapper.log" 2>&1 &
    
    echo $! > "$PID_FILE"
    sleep 3
    
    if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        log_info "vLLM server started (PID: $(cat "$PID_FILE"))"
        log_info "Check logs: $LOG_DIR/vllm_server_latest.log"
        log_info "URL: http://127.0.0.1:8001"
        return 0
    else
        log_error "vLLM server failed to start"
        rm -f "$PID_FILE"
        log_error "Check logs: $LOG_FILE"
        return 1
    fi
}

stop_vllm_server() {
    local PID_FILE="$PID_DIR/vllm_server.pid"
    
    if [ ! -f "$PID_FILE" ]; then
        log_warn "vLLM server is not running"
        return 1
    fi
    
    local PID=$(cat "$PID_FILE")
    
    if ! ps -p $PID > /dev/null 2>&1; then
        log_warn "vLLM server (PID: $PID) is not running"
        rm -f "$PID_FILE"
        return 1
    fi
    
    log_info "Stopping vLLM server (PID: $PID)..."
    kill $PID
    
    # Wait for graceful shutdown
    for i in {1..30}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            log_info "vLLM server stopped"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        log_warn "Force killing vLLM server..."
        kill -9 $PID
        rm -f "$PID_FILE"
    fi
    
    log_info "vLLM server stopped"
    return 0
}

# ============================================================================
# Status Check
# ============================================================================

check_status() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "MCP Servers Status"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    # Memory MCP Server
    local MEMORY_PID_FILE="$PID_DIR/memory_mcp.pid"
    if [ -f "$MEMORY_PID_FILE" ] && ps -p $(cat "$MEMORY_PID_FILE") > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Memory MCP Server: Running (PID: $(cat "$MEMORY_PID_FILE"))"
        echo "  URL: http://127.0.0.1:8765/sse"
        echo "  Log: $LOG_DIR/memory_mcp.log"
    else
        echo -e "${RED}✗${NC} Memory MCP Server: Not running"
    fi
    echo ""
    
    # Mem-Agent MCP Server
    local MEM_AGENT_PID_FILE="$PID_DIR/mem_agent.pid"
    if [ -f "$MEM_AGENT_PID_FILE" ] && ps -p $(cat "$MEM_AGENT_PID_FILE") > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Mem-Agent MCP Server: Running (PID: $(cat "$MEM_AGENT_PID_FILE"))"
        echo "  URL: http://127.0.0.1:8766/sse"
        echo "  Log: $LOG_DIR/mem_agent.log"
    else
        echo -e "${RED}✗${NC} Mem-Agent MCP Server: Not running"
    fi
    echo ""
    
    # vLLM Server
    local VLLM_PID_FILE="$PID_DIR/vllm_server.pid"
    if [ -f "$VLLM_PID_FILE" ] && ps -p $(cat "$VLLM_PID_FILE") > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} vLLM Server: Running (PID: $(cat "$VLLM_PID_FILE"))"
        echo "  URL: http://127.0.0.1:8001"
        echo "  Log: $LOG_DIR/vllm_server_latest.log"
    else
        echo -e "${RED}✗${NC} vLLM Server: Not running"
    fi
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
}

# ============================================================================
# Show Logs
# ============================================================================

show_logs() {
    local SERVER=$1
    local LINES=${2:-50}
    
    case $SERVER in
        memory)
            tail -n "$LINES" -f "$LOG_DIR/memory_mcp.log"
            ;;
        mem-agent)
            tail -n "$LINES" -f "$LOG_DIR/mem_agent.log"
            ;;
        vllm)
            tail -n "$LINES" -f "$LOG_DIR/vllm_server_latest.log"
            ;;
        *)
            log_error "Unknown server: $SERVER"
            echo "Available servers: memory, mem-agent, vllm"
            return 1
            ;;
    esac
}

# ============================================================================
# Main Commands
# ============================================================================

case "${1:-}" in
    start)
        case "${2:-all}" in
            memory)
                start_memory_server
                ;;
            mem-agent)
                start_mem_agent_server
                ;;
            vllm)
                start_vllm_server
                ;;
            all)
                start_memory_server
                start_mem_agent_server
                # Note: vLLM is optional, uncomment if needed
                # start_vllm_server
                ;;
            *)
                log_error "Unknown server: $2"
                echo "Available servers: memory, mem-agent, vllm, all"
                exit 1
                ;;
        esac
        ;;
    
    stop)
        case "${2:-all}" in
            memory)
                stop_memory_server
                ;;
            mem-agent)
                stop_mem_agent_server
                ;;
            vllm)
                stop_vllm_server
                ;;
            all)
                stop_memory_server
                stop_mem_agent_server
                stop_vllm_server
                ;;
            *)
                log_error "Unknown server: $2"
                echo "Available servers: memory, mem-agent, vllm, all"
                exit 1
                ;;
        esac
        ;;
    
    restart)
        case "${2:-all}" in
            memory)
                stop_memory_server || true
                sleep 1
                start_memory_server
                ;;
            mem-agent)
                stop_mem_agent_server || true
                sleep 1
                start_mem_agent_server
                ;;
            vllm)
                stop_vllm_server || true
                sleep 1
                start_vllm_server
                ;;
            all)
                stop_memory_server || true
                stop_mem_agent_server || true
                stop_vllm_server || true
                sleep 2
                start_memory_server
                start_mem_agent_server
                # start_vllm_server
                ;;
            *)
                log_error "Unknown server: $2"
                echo "Available servers: memory, mem-agent, vllm, all"
                exit 1
                ;;
        esac
        ;;
    
    status)
        check_status
        ;;
    
    logs)
        if [ -z "${2:-}" ]; then
            log_error "Please specify server: memory, mem-agent, or vllm"
            exit 1
        fi
        show_logs "$2" "${3:-50}"
        ;;
    
    *)
        echo "MCP Servers Management"
        echo ""
        echo "Usage:"
        echo "  $0 start [server]     - Start server(s)"
        echo "  $0 stop [server]      - Stop server(s)"
        echo "  $0 restart [server]   - Restart server(s)"
        echo "  $0 status             - Check server status"
        echo "  $0 logs <server> [n]  - Show last n lines of logs (default: 50)"
        echo ""
        echo "Available servers:"
        echo "  memory      - Memory MCP Server (HTTP/SSE)"
        echo "  mem-agent   - Mem-Agent MCP Server (LLM-based)"
        echo "  vllm        - vLLM Server for Mem-Agent"
        echo "  all         - All servers (default)"
        echo ""
        echo "Examples:"
        echo "  $0 start memory           # Start Memory MCP server"
        echo "  $0 stop all               # Stop all servers"
        echo "  $0 restart mem-agent      # Restart Mem-Agent server"
        echo "  $0 status                 # Check all servers status"
        echo "  $0 logs memory 100        # Show last 100 log lines"
        echo ""
        exit 1
        ;;
esac
