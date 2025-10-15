#!/bin/bash
# Verification script for MCP refactoring
# This script checks that the refactoring was done correctly

# Note: Don't use set -e because grep commands may return non-zero when pattern not found

echo "======================================================================"
echo "MCP Refactoring Verification Script"
echo "======================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Checking syntax..."
echo "-------------------------------------------------------------------"

if python3 -m py_compile src/mcp/server_manager.py 2>/dev/null; then
    check_pass "server_manager.py syntax valid"
else
    check_fail "server_manager.py has syntax errors"
fi

if python3 -m py_compile src/mcp/mcp_hub_server.py 2>/dev/null; then
    check_pass "mcp_hub_server.py syntax valid"
else
    check_fail "mcp_hub_server.py has syntax errors"
fi

echo ""
echo "2. Checking removed code..."
echo "-------------------------------------------------------------------"

# Check that _create_qwen_config is removed from server_manager
if grep -q "def _create_qwen_config" src/mcp/server_manager.py; then
    check_fail "_create_qwen_config still exists in server_manager.py"
else
    check_pass "_create_qwen_config removed from server_manager.py"
fi

# Check that _setup_mcp_hub_connection is removed
if grep -q "def _setup_mcp_hub_connection" src/mcp/server_manager.py; then
    check_fail "_setup_mcp_hub_connection still exists in server_manager.py"
else
    check_pass "_setup_mcp_hub_connection removed from server_manager.py"
fi

# Check that config file creation is removed from _setup_memory_subprocess
if grep -q "json.dump.*mcp_hub_config_file" src/mcp/server_manager.py; then
    check_fail "_setup_memory_subprocess still creates config files"
else
    check_pass "_setup_memory_subprocess doesn't create config files"
fi

echo ""
echo "3. Checking new code..."
echo "-------------------------------------------------------------------"

# Check that _generate_client_configs exists in mcp_hub_server
if grep -q "def _generate_client_configs" src/mcp/mcp_hub_server.py; then
    check_pass "_generate_client_configs exists in mcp_hub_server.py"
else
    check_fail "_generate_client_configs missing from mcp_hub_server.py"
fi

# Check that config generation is called in main()
if grep "_generate_client_configs(" src/mcp/mcp_hub_server.py | grep -v "^def" | grep -q "_generate_client_configs"; then
    check_pass "_generate_client_configs is called in mcp_hub_server.py"
else
    check_fail "_generate_client_configs not called in mcp_hub_server.py"
fi

# Check for config API endpoint
if grep -q "/config/client" src/mcp/mcp_hub_server.py; then
    check_pass "Config API endpoint exists"
else
    check_fail "Config API endpoint missing"
fi

echo ""
echo "4. Checking documentation..."
echo "-------------------------------------------------------------------"

if [ -f "docs_site/architecture/mcp-architecture.md" ]; then
    check_pass "MCP architecture documentation exists"
else
    check_fail "MCP architecture documentation missing"
fi

if [ -f "REFACTORING_SUMMARY.md" ]; then
    check_pass "Refactoring summary exists"
else
    check_warn "Refactoring summary missing (optional)"
fi

echo ""
echo "5. Checking architecture correctness..."
echo "-------------------------------------------------------------------"

# Check that setup_default_servers doesn't call config generation
if grep -A 30 "def setup_default_servers" src/mcp/server_manager.py | grep -q "qwen_config\|universal_config"; then
    check_fail "setup_default_servers still references config generation"
else
    check_pass "setup_default_servers doesn't reference config generation"
fi

# Check for Docker mode detection
if grep -q "MCP_HUB_URL" src/mcp/server_manager.py; then
    check_pass "Docker mode detection (MCP_HUB_URL) present"
else
    check_fail "Docker mode detection missing"
fi

# Check that bot does nothing in Docker mode
if grep -A 10 "if mcp_hub_url:" src/mcp/server_manager.py | grep -q "Intentionally do nothing\|pure client"; then
    check_pass "Bot is pure client in Docker mode"
else
    check_warn "Docker mode comment could be clearer"
fi

echo ""
echo "======================================================================"
echo "Summary"
echo "======================================================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed! ✓${NC}"
    echo ""
    echo "The refactoring appears to be correct. Key changes:"
    echo "  • Config generation removed from bot (server_manager.py)"
    echo "  • Config generation added to MCP Hub (mcp_hub_server.py)"
    echo "  • Bot is now a pure client in Docker mode"
    echo "  • MCP Hub owns all MCP logic"
    echo ""
    echo "Next steps:"
    echo "  1. Test in Docker mode: docker-compose up"
    echo "  2. Test in standalone mode: python -m main"
    echo "  3. Verify no config logs from bot"
    echo "  4. Verify config logs from MCP Hub"
    exit 0
else
    echo -e "${RED}Some checks failed!${NC}"
    echo ""
    echo "Please review the failed checks above and fix them."
    echo "See REFACTORING_SUMMARY.md for details."
    exit 1
fi
