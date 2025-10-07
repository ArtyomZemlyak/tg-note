# MCP Tools Discovery for Agents

## Overview

This document describes how agents discover and learn about available MCP (Model Context Protocol) tools.

## Problem Statement

Previously, while the system could dynamically discover and register MCP tools at runtime, the LLM itself didn't know about these tools. This meant:

- **AutonomousAgent**: The LLM didn't receive information about available MCP tools in its system prompt
- **QwenCodeCLIAgent**: The qwen CLI didn't receive information about MCP tools at all

## Solution

We've implemented a comprehensive solution that ensures all agents know about available MCP tools:

### 1. MCP Tools Description Generator

**File**: `src/agents/mcp/tools_description.py`

This module provides functions to generate human-readable descriptions of available MCP servers and their tools:

- `get_mcp_tools_description(user_id, servers_dir)`: Discovers MCP servers, connects to them, and generates a formatted description
- `format_mcp_tools_for_prompt(tools_description, include_in_system)`: Formats the description for inclusion in LLM prompts

**Features**:
- Discovers both shared and per-user MCP servers
- Connects to enabled servers
- Queries each server for available tools
- Generates detailed descriptions including:
  - Tool names (in agent format: `mcp_server_tool`)
  - Tool descriptions
  - Parameter schemas
  - Required vs optional parameters

### 2. AutonomousAgent Integration

**File**: `src/agents/autonomous_agent.py`

**Changes**:
- Added `_mcp_tools_description` cache attribute
- Added `get_mcp_tools_description()` method that:
  - Returns cached description if available
  - Only generates if MCP is enabled
  - Caches result for performance
- Modified `_make_decision_llm()` to include MCP tools info in system prompt

**How it works**:
```python
# Get MCP tools description
mcp_description = await self.get_mcp_tools_description()

# Add to system prompt
system_content = self.instruction
if mcp_description:
    system_content = f"{self.instruction}\n\n{mcp_description}"
```

### 3. QwenCodeCLIAgent Integration

**File**: `src/agents/qwen_code_cli_agent.py`

**Changes**:
- Added MCP support attributes: `enable_mcp`, `user_id`, `_mcp_tools_description`
- Added `get_mcp_tools_description()` method (similar to AutonomousAgent)
- Added `_prepare_prompt_async()` method that includes MCP tools in prompt
- Modified `process()` to use async prompt preparation

**How it works**:
```python
# Prepare base prompt
base_prompt = CONTENT_PROCESSING_PROMPT_TEMPLATE.format(...)

# Add MCP tools description
mcp_description = await self.get_mcp_tools_description()
if mcp_description:
    return f"{base_prompt}{mcp_description}"
```

## Usage

### For AutonomousAgent

When `AGENT_ENABLE_MCP=true`, the agent's LLM will automatically receive:

```
## MCP Tools Available

You have access to additional tools via MCP (Model Context Protocol):

# Available MCP Tools

The following MCP (Model Context Protocol) servers are available with their tools:

## MCP Server: mem-agent

### mcp_mem_agent_store_memory
- **Original name**: `store_memory`
- **Description**: Store information in memory
- **Parameters**:
  - `content` (string) (required): Content to store
  - `category` (string) (optional): Memory category

...

Use these tools when appropriate for the task.
```

### For QwenCodeCLIAgent

When `AGENT_ENABLE_MCP=true`, the qwen CLI will receive the same information in its input prompt (formatted for user context rather than system).

## Configuration

Enable MCP tools discovery by setting in `.env` or config:

```bash
# Enable MCP support
AGENT_ENABLE_MCP=true
```

The system will:
1. Discover MCP servers from `data/mcp_servers/` (shared) and `data/mcp_servers/user_{user_id}/` (per-user)
2. Connect to enabled servers
3. Query available tools
4. Generate descriptions
5. Include in agent prompts

## Benefits

✅ **LLMs know about MCP tools**: Tools are described in prompts  
✅ **Automatic discovery**: No manual configuration needed  
✅ **Per-user support**: Different users can have different MCP tools  
✅ **Performance**: Descriptions are cached  
✅ **Detailed information**: Tools include parameter schemas  
✅ **Works for all agents**: Both AutonomousAgent and QwenCodeCLIAgent  

## Testing

Tests are provided in `tests/test_mcp_tools_description.py`:

- `TestMCPToolsDescription`: Tests description generation
- `TestAutonomousAgentMCPIntegration`: Tests AutonomousAgent integration
- `TestQwenCodeCLIAgentMCPIntegration`: Tests QwenCodeCLIAgent integration

Run tests:
```bash
pytest tests/test_mcp_tools_description.py -v
```

## Implementation Details

### Caching

Both agents cache MCP tools descriptions to avoid repeated discovery:
- First call: Discovers servers, connects, generates description
- Subsequent calls: Returns cached description
- Cache is per-agent instance

### Async Support

All MCP operations are async:
- `get_mcp_tools_description()` is async
- `_prepare_prompt_async()` is async for QwenCodeCLIAgent
- Compatible with agent's async architecture

### Error Handling

- If MCP discovery fails, returns empty string (graceful degradation)
- Errors are logged but don't break agent execution
- If MCP is disabled, immediately returns empty string

## Example Output

When an agent has MCP tools enabled, the LLM receives:

```markdown
# Available MCP Tools

The following MCP (Model Context Protocol) servers are available with their tools:

## MCP Server: filesystem

### mcp_filesystem_read_file
- **Original name**: `read_file`
- **Description**: Read contents of a file
- **Parameters**:
  - `path` (string) (required): Path to the file to read

### mcp_filesystem_write_file
- **Original name**: `write_file`
- **Description**: Write contents to a file
- **Parameters**:
  - `path` (string) (required): Path to the file to write
  - `content` (string) (required): Content to write

---

**Total MCP tools available**: 2 from 1 server(s)

**Usage**: Call these tools using their agent tool name (e.g., `mcp_filesystem_read_file`)
```

## Future Improvements

Potential enhancements:

1. **Tool filtering**: Allow agents to specify which MCP tools they want
2. **Dynamic refresh**: Refresh MCP tools description when servers change
3. **Richer descriptions**: Include usage examples in tool descriptions
4. **Tool categories**: Group tools by category or server type
5. **Permission system**: Control which users can access which MCP tools