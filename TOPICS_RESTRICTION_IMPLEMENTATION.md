# Topics Folder Restriction Implementation

## Summary

Implemented restriction for all agents to work only within the `topics/` folder of the knowledge base. This prevents agents from modifying meta files like `index.md`, `README.md`, and other files in the knowledge base root.

## Changes Made

### 1. Configuration Setting (`config/settings.py`)

Added new configuration parameter:

```python
KB_TOPICS_ONLY: bool = Field(
    default=True,
    description="Restrict agents to work only in topics/ folder"
)
```

**Default Value**: `True` (agents are restricted by default)

### 2. Configuration Example (`config.example.yaml`)

Added documentation for the new setting:

```yaml
# KB_TOPICS_ONLY: Restrict agents to work only in topics/ folder
# - true: Agents can only create/edit/read files in KB_PATH/topics/ directory
#         This prevents agents from modifying index.md, README.md, and other meta files
#         in the knowledge base root. Recommended for production use.
# - false: Agents have full access to entire knowledge base directory
#          Useful for testing or if you need agents to manage meta files
KB_TOPICS_ONLY: true
```

### 3. Agent Factory (`src/agents/agent_factory.py`)

#### For Autonomous Agent:
Modified `_create_autonomous_agent()` to adjust the `kb_root_path`:

```python
# Determine kb_root_path based on kb_topics_only setting
kb_path = Path(config.get("kb_path", "./knowledge_base"))
kb_topics_only = config.get("kb_topics_only", True)

if kb_topics_only:
    kb_root_path = kb_path / "topics"
    logger.info(f"Restricting agent to topics folder: {kb_root_path}")
else:
    kb_root_path = kb_path
    logger.info(f"Agent has full access to knowledge base: {kb_root_path}")
```

#### For Qwen CLI Agent:
Modified `_create_qwen_cli_agent()` to adjust the `working_directory`:

```python
# Determine working_directory based on kb_topics_only setting
working_directory = config.get("working_directory")
if not working_directory:
    kb_path = Path(config.get("kb_path", "./knowledge_base"))
    kb_topics_only = config.get("kb_topics_only", True)
    
    if kb_topics_only:
        working_directory = str(kb_path / "topics")
        logger.info(f"Restricting Qwen CLI agent to topics folder: {working_directory}")
    else:
        working_directory = str(kb_path)
        logger.info(f"Qwen CLI agent has full access to knowledge base: {working_directory}")
```

## How It Works

### Path Validation

All file and folder tools use `_validate_safe_path()` which:
1. Validates that paths are within the `kb_root_path`
2. Prevents path traversal attacks (`..` is not allowed)
3. Returns error if path is outside the allowed directory

### Tool Context

The `ToolContext` is created with the adjusted `kb_root_path`:
- **Before**: `kb_root_path = ./knowledge_base`
- **After (with KB_TOPICS_ONLY=true)**: `kb_root_path = ./knowledge_base/topics`

This means all tools automatically operate within the restricted directory.

### Affected Tools

All file and folder management tools are automatically restricted:
- `file_create` - Create files
- `file_edit` - Edit files
- `file_delete` - Delete files
- `file_move` - Move/rename files
- `folder_create` - Create folders
- `folder_delete` - Delete folders
- `folder_move` - Move/rename folders
- `kb_read_file` - Read files
- `kb_list_directory` - List directory contents
- `kb_search_files` - Search for files
- `kb_search_content` - Search in file contents

## Protected Files

With `KB_TOPICS_ONLY=true`, the following files in the KB root are protected from agent modification:
- `README.md` - Knowledge base documentation
- `index.md` - Index of all documents
- `.gitignore` - Git ignore rules
- Any other meta files in the root directory

## Directory Structure

```
knowledge_base/
├── README.md           ← PROTECTED (agents cannot modify)
├── index.md            ← PROTECTED (agents cannot modify)
├── .gitignore          ← PROTECTED (agents cannot modify)
└── topics/             ← AGENTS WORK HERE
    ├── general/
    ├── ai/
    │   ├── machine-learning/
    │   ├── nlp/
    │   └── ...
    ├── tech/
    │   ├── programming/
    │   ├── web-development/
    │   └── ...
    └── ...
```

## Testing

To test the restriction:

1. Set `KB_TOPICS_ONLY=true` in `config.yaml`
2. Ask an agent to create a file in the root: `"Create a file test.md in the root"`
3. The agent will only be able to create files in `topics/` subfolder

To disable restriction:

1. Set `KB_TOPICS_ONLY=false` in `config.yaml`
2. Agents will have full access to the entire knowledge base

## Backward Compatibility

- **Default behavior**: Agents are restricted to `topics/` (safe by default)
- **Legacy behavior**: Set `KB_TOPICS_ONLY=false` to restore full access
- All existing code continues to work without modification

## Security Benefits

1. **Prevents accidental damage**: Agents cannot accidentally delete or modify important meta files
2. **Clear separation**: Content files are in `topics/`, meta files are in root
3. **Safe by default**: New installations have restriction enabled automatically
4. **Explicit override**: Must explicitly set `KB_TOPICS_ONLY=false` to disable

## Implementation Date

2025-10-07
