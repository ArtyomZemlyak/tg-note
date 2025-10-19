# Agent Architecture

## Overview

The Agent system is the core AI component of tg-note responsible for analyzing content, generating structured notes, and executing autonomous tasks. The architecture supports multiple agent implementations with a common interface, allowing flexibility in choosing the right AI backend for your needs.

## Agent System Design

### Core Principles

1. **Pluggable Architecture**: Easy to add new agent types
2. **Common Interface**: All agents implement `BaseAgent`
3. **Tool Integration**: Rich tool ecosystem for extended capabilities
4. **Async-First**: Non-blocking operations
5. **User Isolation**: Per-user agent instances and context

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Service Layer                              │
│  (NoteCreationService, AgentTaskService, etc.)               │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    Agent Factory                              │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Creates agent instances based on configuration:    │      │
│  │  - AGENT_TYPE: stub | qwen_code_cli | autonomous  │      │
│  │  - Per-user instance caching                       │      │
│  │  - Tool configuration                              │      │
│  └────────────────────────┬───────────────────────────┘      │
└────────────────────────────┼──────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  StubAgent    │  │ QwenCodeCLI     │  │ Autonomous      │
│               │  │ Agent           │  │ Agent           │
│  - Testing    │  │                 │  │                 │
│  - MVP        │  │ - Subprocess    │  │ - Python API    │
│  - No AI      │  │ - Qwen Native   │  │ - OpenAI-compat │
│               │  │ - Free tier     │  │ - Full control  │
└───────┬───────┘  └────────┬────────┘  └────────┬────────┘
        │                   │                    │
        └───────────────────┼────────────────────┘
                            │
                            │ All implement BaseAgent
                            │
                            ▼
        ┌────────────────────────────────────────┐
        │          BaseAgent Interface            │
        │                                         │
        │  async def process(...)                 │
        │  async def execute_task(...)            │
        │  get_available_tools()                  │
        │  set_working_directory(...)             │
        └────────────────┬───────────────────────┘
                         │
                         │ Uses tools
                         │
                         ▼
        ┌────────────────────────────────────────┐
        │           Tool System                   │
        │                                         │
        │  - File Tools                           │
        │  - Folder Tools                         │
        │  - Git Tools                            │
        │  - GitHub Tools                         │
        │  - Web Search Tools                     │
        │  - KB Reading Tools                     │
        │  - Vector Search Tools                  │
        │  - MCP Tools (DynamicMCPTool)           │
        │  - Planning Tools                       │
        └─────────────────────────────────────────┘
```

## Component Details

### BaseAgent (Abstract Interface)

**Location**: `src/agents/base_agent.py`

**Purpose**: Defines the contract that all agents must implement

**Key Methods**:

```python
class BaseAgent(ABC):
    @abstractmethod
    async def process(
        self,
        messages: List[Dict[str, str]],
        user_id: int,
        kb_path: Path,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process messages and generate structured note"""
        pass

    @abstractmethod
    async def execute_task(
        self,
        task: str,
        user_id: int,
        kb_path: Path,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute autonomous task (agent mode)"""
        pass

    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        pass

    def set_working_directory(self, directory: Path) -> None:
        """Set agent working directory (optional)"""
        pass
```

**Response Format**:

```python
{
    "content": str,              # Generated markdown content
    "category": str,             # Topic category (ai, biology, physics, etc.)
    "files_created": List[str],  # Paths of created files
    "files_edited": List[str],   # Paths of edited files
    "files_deleted": List[str],  # Paths of deleted files
    "folders_created": List[str],# Paths of created folders
    "links": List[Dict],         # Relations to other notes
    "metadata": Dict[str, Any]   # Additional metadata
}
```

### AgentFactory

**Location**: `src/agents/agent_factory.py`

**Purpose**: Creates and caches agent instances based on configuration

**Key Features**:

- **Type-based instantiation**: Reads `AGENT_TYPE` from settings
- **Per-user caching**: One agent instance per user (stateful conversations)
- **Tool configuration**: Enables/disables tools based on settings
- **MCP integration**: Automatically connects MCP tools if enabled

**Usage**:

```python
from src.agents.agent_factory import AgentFactory

factory = AgentFactory(settings, mcp_client_factory)

# Get or create agent for user
agent = await factory.get_agent(user_id=123)

# Process content
result = await agent.process(
    messages=[{"role": "user", "content": "Important article about AI"}],
    user_id=123,
    kb_path=Path("/path/to/kb")
)
```

**Agent Selection Logic**:

```python
if AGENT_TYPE == "stub":
    return StubAgent()
elif AGENT_TYPE == "qwen_code_cli":
    return QwenCodeCLIAgent(settings)
elif AGENT_TYPE == "autonomous":
    return AutonomousAgent(settings, tools)
else:
    raise ValueError(f"Unknown agent type: {AGENT_TYPE}")
```

## Agent Implementations

### 1. StubAgent

**Location**: `src/agents/stub_agent.py`

**Purpose**: Simple testing agent without AI dependencies

**Characteristics**:

- ✅ Fast and lightweight
- ✅ No external API calls
- ✅ Predictable output
- ❌ No real AI analysis
- ❌ Basic categorization (random)

**Use Cases**:

- Unit testing
- MVP development
- CI/CD pipelines
- Development without API keys

**Example Response**:

```python
{
    "content": "# Processed Note\n\n[User content here]",
    "category": "general",
    "files_created": [],
    "files_edited": [],
    "files_deleted": [],
    "folders_created": [],
    "links": [],
    "metadata": {"agent": "stub", "processing_time": 0.1}
}
```

**Configuration**:

```yaml
AGENT_TYPE: "stub"
```

### 2. QwenCodeCLIAgent

**Location**: `src/agents/qwen_code_cli_agent.py`

**Purpose**: Integration with Qwen Code CLI (subprocess)

**Characteristics**:

- ✅ Uses Qwen3-Coder models
- ✅ Free tier: 2000 requests/day
- ✅ Built-in tools (web, git, github, shell)
- ✅ TODO planning
- ✅ Vision model support
- ✅ Native MCP support (via `.qwen/settings.json`)
- ⚠️ Subprocess overhead
- ⚠️ Node.js dependency

**How It Works**:

```
┌──────────────────────┐
│  QwenCodeCLIAgent    │
│  (Python)            │
└──────────┬───────────┘
           │
           │ subprocess.Popen()
           │
           ▼
┌──────────────────────┐
│  qwen CLI            │
│  (Node.js)           │
│                      │
│  - Qwen3 Model       │
│  - Built-in tools    │
│  - MCP client        │
└──────────────────────┘
```

**Tool Configuration**:

```yaml
AGENT_TYPE: "qwen_code_cli"
AGENT_QWEN_CLI_PATH: "qwen"
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false  # Security: disabled by default
AGENT_ENABLE_MCP: true      # Enable MCP support
```

**MCP Configuration** (optional, `.qwen/settings.json`):

```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "MCP Hub with memory tools"
    }
  },
  "allowMCPServers": ["mcp-hub"]
}
```

**Prompt Engineering**:

The agent uses specialized prompts for different tasks:

- **Note creation**: "Analyze the following messages and create a structured markdown note..."
- **Question answering**: "Answer the following question based on the KB content..."
- **Task execution**: "Execute the following task in the knowledge base..."

**Response Parsing**:

The agent parses qwen CLI output to extract:

- Markdown content
- File operations (created, edited, deleted)
- Folder operations
- Category detection
- Links/relations

**Debugging**:

```bash
# Enable debug logs
LOG_LEVEL: DEBUG

# Run qwen CLI manually for testing
qwen --work-dir /path/to/kb --prompt "Test prompt"
```

### 3. AutonomousAgent

**Location**: `src/agents/autonomous_agent.py`

**Purpose**: Python-based agent with OpenAI-compatible API

**Characteristics**:

- ✅ Full Python integration
- ✅ OpenAI-compatible API (OpenAI, Azure, custom endpoints)
- ✅ Function calling support
- ✅ Rich tool ecosystem (Python-native)
- ✅ MCP tools via Python client
- ✅ Autonomous planning and execution
- ⚠️ Requires API key
- ⚠️ API costs (provider-dependent)

**How It Works**:

```
┌──────────────────────┐
│  AutonomousAgent     │
│  (Python)            │
│                      │
│  ┌────────────────┐  │
│  │ LLM Connector  │──┼───► OpenAI API
│  │ (OpenAI/Azure) │  │     (or compatible)
│  └────────────────┘  │
│                      │
│  ┌────────────────┐  │
│  │ Tool Registry  │  │
│  │  - File tools  │  │
│  │  - Git tools   │  │
│  │  - Web tools   │  │
│  │  - MCP tools   │  │
│  └────────────────┘  │
└──────────────────────┘
```

**Tool Integration**:

```python
# Tools are registered and passed to LLM as function definitions
tools = [
    FileTool(),
    GitTool(),
    WebSearchTool(),
    DynamicMCPTool(mcp_client),  # MCP integration
    VectorSearchTool(),
]

# LLM receives tool definitions
functions = [tool.to_openai_function() for tool in tools]

# LLM calls tools via function calling
response = await openai_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    functions=functions,
    function_call="auto"
)
```

**MCP Integration**:

```python
from src.mcp.dynamic_mcp_tools import DynamicMCPTool

# Create MCP tool that wraps all MCP server tools
mcp_tool = DynamicMCPTool(mcp_client_factory, user_id)

# MCP tool provides access to:
# - Built-in memory tools (store_memory, retrieve_memory)
# - External MCP servers (from registry)
# - All tools appear as native Python functions to the agent
```

**Configuration**:

```yaml
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"
AGENT_MAX_ITERATIONS: 10
AGENT_TIMEOUT: 300
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_FILE_MANAGEMENT: true
AGENT_ENABLE_FOLDER_MANAGEMENT: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false
AGENT_ENABLE_MCP: true
```

**Environment Variables**:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional, for custom endpoints
```

**Autonomous Loop**:

```python
for iteration in range(max_iterations):
    # 1. Get LLM response
    response = await llm.chat(messages, functions)

    # 2. Check if function call requested
    if response.function_call:
        tool_name = response.function_call.name
        tool_args = json.loads(response.function_call.arguments)

        # 3. Execute tool
        result = await tools[tool_name].execute(**tool_args)

        # 4. Add result to messages
        messages.append({
            "role": "function",
            "name": tool_name,
            "content": json.dumps(result)
        })
    else:
        # 5. Final answer received
        break
```

**Prompt System**:

The agent uses system prompts to guide behavior:

```python
SYSTEM_PROMPT = """
You are an AI assistant helping to organize a knowledge base.

Your task is to:
1. Analyze the provided content
2. Extract key information
3. Create a well-structured markdown note
4. Categorize content by topic
5. Create links to related notes

Available tools: {tool_list}

Knowledge base structure:
- topics/ai/ - AI and machine learning
- topics/biology/ - Biology and life sciences
- topics/physics/ - Physics and chemistry
- topics/tech/ - Technology and engineering
- ...
"""
```

## Tool System

### Tool Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Tool Registry                           │
│  (src/agents/tools/registry.py)                            │
└────────────────────────────┬───────────────────────────────┘
                             │
        ┌────────────────────┼─────────────────────┐
        │                    │                     │
        ▼                    ▼                     ▼
┌───────────────┐  ┌──────────────────┐  ┌────────────────┐
│  File Tools   │  │  Git Tools       │  │  Web Tools     │
│               │  │                  │  │                │
│  - create     │  │  - commit        │  │  - search      │
│  - read       │  │  - push          │  │  - fetch       │
│  - update     │  │  - branch        │  │                │
│  - delete     │  │  - status        │  │                │
└───────────────┘  └──────────────────┘  └────────────────┘

┌───────────────┐  ┌──────────────────┐  ┌────────────────┐
│ Folder Tools  │  │ GitHub Tools     │  │ KB Reading     │
│               │  │                  │  │ Tools          │
│  - create     │  │  - create_issue  │  │                │
│  - list       │  │  - create_pr     │  │  - search_kb   │
│  - delete     │  │  - comment       │  │  - list_files  │
└───────────────┘  └──────────────────┘  └────────────────┘

┌───────────────┐  ┌──────────────────┐
│ Vector Search │  │  MCP Tools       │
│ Tools         │  │  (Dynamic)       │
│               │  │                  │
│  - semantic   │  │  - memory        │
│  - similarity │  │  - custom        │
└───────────────┘  └──────────────────┘
```

### Tool Categories

#### 1. File Tools (`src/agents/tools/file_tools.py`)

**Purpose**: File system operations

**Available Tools**:

- `create_file(path, content)`: Create new file
- `read_file(path)`: Read file contents
- `update_file(path, content)`: Update file
- `delete_file(path)`: Delete file
- `list_files(directory)`: List files in directory

**Safety Features**:

- Path validation (prevent path traversal)
- Working directory restriction
- Backup before overwrite
- Atomic operations

#### 2. Folder Tools (`src/agents/tools/folder_tools.py`)

**Purpose**: Directory management

**Available Tools**:

- `create_folder(path)`: Create directory
- `delete_folder(path)`: Delete directory (recursive)
- `list_folders(directory)`: List subdirectories

#### 3. Git Tools (`src/agents/tools/git_tools.py`)

**Purpose**: Git operations

**Available Tools**:

- `git_commit(message)`: Commit changes
- `git_push()`: Push to remote
- `git_status()`: Check repository status
- `git_branch()`: Manage branches
- `git_pull()`: Pull from remote

**Integration**: Uses `GitOperations` from KB layer

#### 4. GitHub Tools (`src/agents/tools/github_tools.py`)

**Purpose**: GitHub API operations

**Available Tools**:

- `create_github_issue(title, body)`: Create issue
- `create_github_pr(title, body, branch)`: Create pull request
- `comment_on_issue(issue_number, comment)`: Add comment

**Requires**: `GITHUB_TOKEN` environment variable

#### 5. Web Tools (`src/agents/tools/web_tools.py`)

**Purpose**: Web search and fetching

**Available Tools**:

- `web_search(query)`: Search the web
- `fetch_url(url)`: Fetch webpage content

**Backends**:

- DuckDuckGo (default, no API key)
- Google Custom Search (requires API key)

#### 6. KB Reading Tools (`src/agents/tools/kb_reading_tools.py`)

**Purpose**: Knowledge base search and reading

**Available Tools**:

- `search_kb(query)`: Search KB content
- `list_kb_files(path)`: List files in KB
- `get_kb_structure()`: Get KB directory structure

**Integration**: Direct access to KB file system

#### 7. Vector Search Tools (`src/agents/tools/vector_search_tools.py`)

**Purpose**: Semantic search in KB

**Available Tools**:

- `vector_search(query, top_k)`: Semantic search
- `similarity_search(text, threshold)`: Find similar content

**Backends**:

- FAISS (local)
- Qdrant (server-based)

#### 8. MCP Tools (Dynamic)

**Purpose**: Access to MCP protocol tools

**Available Tools**: Dynamic, based on connected MCP servers

**Built-in (via MCP Hub)**:

- `store_memory(content, category, user_id)`: Store memory
- `retrieve_memory(query, user_id, category)`: Retrieve memory
- `list_categories(user_id)`: List memory categories

**External**: Any tools from registered MCP servers

**See Also**: [MCP Architecture](mcp-architecture.md), [MCP Tools](../agents/mcp-tools.md)

### Tool Configuration

Tools are enabled/disabled via settings:

```yaml
# File/Folder tools
AGENT_ENABLE_FILE_MANAGEMENT: true
AGENT_ENABLE_FOLDER_MANAGEMENT: true

# Git tools
AGENT_ENABLE_GIT: true

# GitHub tools
AGENT_ENABLE_GITHUB: true

# Shell tools (security risk - disabled by default)
AGENT_ENABLE_SHELL: false

# Web tools
AGENT_ENABLE_WEB_SEARCH: true

# MCP tools
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true

# Vector search
AGENT_ENABLE_VECTOR_SEARCH: true
```

## Agent Lifecycle

### 1. Initialization

```python
# Create agent via factory
agent = await agent_factory.get_agent(user_id=123)

# Configure working directory (if needed)
agent.set_working_directory(kb_path)

# Agent is now ready to process requests
```

### 2. Processing

```python
# Process content (note mode)
result = await agent.process(
    messages=[
        {"role": "user", "content": "Important article about quantum computing"}
    ],
    user_id=123,
    kb_path=Path("/path/to/kb"),
    context={"previous_messages": [...]}
)
```

### 3. Task Execution

```python
# Execute task (agent mode)
result = await agent.execute_task(
    task="Find all notes about AI and create a summary document",
    user_id=123,
    kb_path=Path("/path/to/kb"),
    context={"previous_tasks": [...]}
)
```

### 4. Cleanup

```python
# Agent instances are cached per user
# No explicit cleanup needed (managed by factory)
```

## Agent Context

### User Context

Each user has isolated context:

```python
{
    "user_id": 123,
    "kb_path": Path("/path/to/kb"),
    "previous_messages": [...],  # Conversation history
    "working_directory": Path("/path/to/kb/topics"),
    "preferences": {...}  # User settings
}
```

### Conversation Context

Maintained by `UserContextManager`:

```python
from src.services.user_context_manager import UserContextManager

context_manager = UserContextManager()

# Add message to context
context_manager.add_message(
    user_id=123,
    role="user",
    content="Tell me about AI"
)

# Get context for agent
context = context_manager.get_context(user_id=123, max_messages=10)
```

## Agent Selection Guide

### Use StubAgent When:

- ✅ Testing without API keys
- ✅ CI/CD pipelines
- ✅ MVP development
- ✅ Quick prototyping

### Use QwenCodeCLIAgent When:

- ✅ You want free tier (2000/day)
- ✅ You need vision model
- ✅ You prefer official Qwen integration
- ✅ Subprocess overhead is acceptable
- ✅ Node.js is available

### Use AutonomousAgent When:

- ✅ You need MCP tools (Python native)
- ✅ You have OpenAI-compatible API
- ✅ You need custom tool development
- ✅ You want full Python control
- ✅ Function calling is important

## Performance Considerations

### Response Time

- **StubAgent**: < 100ms (no API calls)
- **QwenCodeCLIAgent**: 2-10s (subprocess + API)
- **AutonomousAgent**: 3-15s (API + function calls)

### Memory Usage

- **StubAgent**: ~10 MB
- **QwenCodeCLIAgent**: ~50 MB (subprocess)
- **AutonomousAgent**: ~30 MB (Python only)

### Concurrency

- Agents are cached per user
- Multiple users = multiple agent instances
- Async operations allow concurrent processing
- Rate limiting prevents API abuse

## Error Handling

### Agent Failures

```python
try:
    result = await agent.process(messages, user_id, kb_path)
except AgentTimeoutError:
    # Agent took too long
    notify_user("Processing timed out. Please try again.")
except AgentAPIError as e:
    # API error (rate limit, auth, etc.)
    notify_user(f"AI service error: {e.message}")
except Exception as e:
    # Unexpected error
    log_error(e)
    notify_user("An error occurred. Please try again.")
```

### Graceful Degradation

- If agent fails, system continues running
- User receives error notification
- Logs contain detailed error information
- System state remains consistent

## Testing Agents

### Unit Testing

```python
import pytest
from src.agents.stub_agent import StubAgent

@pytest.mark.asyncio
async def test_stub_agent_process():
    agent = StubAgent()

    result = await agent.process(
        messages=[{"role": "user", "content": "Test"}],
        user_id=123,
        kb_path=Path("/tmp/test_kb")
    )

    assert "content" in result
    assert "category" in result
    assert result["category"] in ["ai", "biology", "physics", "tech", "general"]
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_autonomous_agent_with_tools():
    agent = AutonomousAgent(settings, tools=[FileTool(), GitTool()])

    result = await agent.execute_task(
        task="Create a file named test.md with content 'Hello'",
        user_id=123,
        kb_path=Path("/tmp/test_kb")
    )

    assert Path("/tmp/test_kb/test.md").exists()
    assert Path("/tmp/test_kb/test.md").read_text() == "Hello"
```

### Mocking

```python
from unittest.mock import AsyncMock, MagicMock

# Mock OpenAI client
mock_openai = AsyncMock()
mock_openai.chat.completions.create.return_value = MagicMock(
    choices=[MagicMock(message=MagicMock(content="Generated content"))]
)

# Test agent with mock
agent = AutonomousAgent(settings, llm_client=mock_openai)
```

## Related Documentation

- [Agent Overview](../agents/overview.md) - User-facing agent documentation
- [Autonomous Agent](../agents/autonomous-agent.md) - Autonomous agent setup
- [Qwen Code CLI](../agents/qwen-code-cli.md) - Qwen CLI integration
- [Stub Agent](../agents/stub-agent.md) - Testing agent
- [MCP Tools](../agents/mcp-tools.md) - MCP tool integration
- [KB Reading Tools](../agents/kb-reading-tools.md) - KB search tools
- [Architecture Overview](overview.md) - System-wide architecture
- [Data Flow](data-flow.md) - Data flow through agents
