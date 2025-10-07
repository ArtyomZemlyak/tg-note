# Prompt Refactoring Guide

## Overview

Agent prompts have been refactored from hardcoded Python constants to flexible YAML files with versioning support. This provides:

- **Versioning**: Track changes, A/B test prompts, rollback if needed
- **Flexibility**: Update prompts without code changes
- **Multi-language**: Support for different languages
- **Hot-reloading**: Reload prompts without restarting
- **Maintainability**: Clear structure and documentation

## Architecture

### Before (Deprecated)

```python
# config/agent_prompts.py
QWEN_CODE_CLI_AGENT_INSTRUCTION = """Long hardcoded prompt..."""
CATEGORY_KEYWORDS = {"ai": [...], ...}
MAX_TITLE_LENGTH = 60
```

### After (Current)

```
config/
├── prompts/
│   ├── v1/                          # Version 1
│   │   ├── config.yaml              # Configuration
│   │   ├── qwen_code_agent.yaml     # Agent prompts
│   │   ├── qwen_code_cli_agent.yaml
│   │   ├── kb_query.yaml
│   │   └── stub_agent.yaml
│   └── v2/                          # Version 2 (future)
├── prompt_loader.py                 # Loader class
└── agent_prompts.py                 # Backward compatibility
```

## Migration Path

### For Existing Code (No Changes Required)

The old API still works via `config/agent_prompts.py`:

```python
# This still works!
from config.agent_prompts import (
    QWEN_CODE_CLI_AGENT_INSTRUCTION,
    CATEGORY_KEYWORDS,
    MAX_TITLE_LENGTH
)
```

### For New Code (Recommended)

Use the new PromptLoader:

```python
from config.prompt_loader import PromptLoader

# Load latest version
loader = PromptLoader()

# Get instruction
instruction = loader.get_instruction("qwen_code_cli_agent")

# Get configuration
categories = loader.get_category_keywords()
max_title = loader.get_config("markdown.max_title_length")
```

## Usage Examples

### 1. Basic Usage

```python
from config.prompt_loader import PromptLoader

loader = PromptLoader()

# Get agent instruction
instruction = loader.get_instruction("qwen_code_cli_agent")

# Get template
template = loader.get_template("qwen_code_agent", "content_processing")

# Format template with variables
formatted = loader.format_template(
    "qwen_code_agent",
    "content_processing",
    instruction=instruction,
    text="Content to process",
    urls_section=""
)
```

### 2. Using Specific Version

```python
# Load specific version
loader = PromptLoader(version="v1")

# Check version
print(f"Using version: {loader.version}")

# Get metadata
metadata = loader.get_metadata("qwen_code_cli_agent")
print(f"Prompt version: {metadata['version']}")
print(f"Language: {metadata['language']}")
```

### 3. Configuration Access

```python
loader = PromptLoader()

# Get category keywords
categories = loader.get_category_keywords()
ai_keywords = categories.get("ai", [])

# Get markdown config
markdown_config = loader.get_markdown_config()
max_title = markdown_config.get("max_title_length")

# Nested config access
max_title = loader.get_config("markdown.max_title_length", default=60)

# Get stop words
stop_words = loader.get_stop_words()

# Get tool safety config
safe_commands = loader.get_config("tools.safe_git_commands")
```

### 4. Hot Reloading

```python
loader = PromptLoader()

# Get instruction
instruction = loader.get_instruction("qwen_code_agent")

# ... edit YAML file ...

# Reload from files
loader.reload()

# Get updated instruction
updated_instruction = loader.get_instruction("qwen_code_agent")
```

### 5. Agent Integration

```python
from config.prompt_loader import PromptLoader

class MyAgent:
    def __init__(self, prompt_version="v1"):
        self.loader = PromptLoader(version=prompt_version)
        self.instruction = self.loader.get_instruction("qwen_code_agent")
        
    def process(self, content):
        # Use loaded instruction
        prompt = self.loader.format_template(
            "qwen_code_agent",
            "content_processing",
            instruction=self.instruction,
            text=content["text"],
            urls_section=""
        )
        # ... process with prompt ...
```

## YAML Format

### Agent Prompt File

```yaml
version: "1.0.0"
name: "agent_name"
description: "Agent description"
language: "en"  # or "ru"
created_at: "2025-10-07"

instruction: |
  Multi-line instruction text...
  Can include {placeholders} if needed.

templates:
  template_name: |
    Template content with {variable1} and {variable2}
  
  another_template: |
    Another template...
```

### Configuration File

```yaml
version: "1.0.0"
description: "Configuration description"

category_keywords:
  category_name:
    - keyword1
    - keyword2

stop_words:
  - word1
  - word2

markdown:
  max_title_length: 60
  max_summary_length: 200
  max_keyword_count: 10

tools:
  safe_git_commands:
    - status
    - log
  dangerous_shell_patterns:
    - "rm -rf"
```

## Creating New Versions

1. Copy the latest version directory:
   ```bash
   cp -r config/prompts/v1 config/prompts/v2
   ```

2. Update version in all YAML files:
   ```yaml
   version: "2.0.0"
   ```

3. Make your changes to prompts/config

4. Test with specific version:
   ```python
   loader = PromptLoader(version="v2")
   ```

5. Update `config/prompts/README.md` with version notes

## Testing

### Test Prompt Loading

```python
from config.prompt_loader import PromptLoader

loader = PromptLoader()

# List agents
agents = loader.list_agents()
assert "qwen_code_cli_agent" in agents

# List versions
versions = loader.list_versions()
assert "v1" in versions

# Load instruction
instruction = loader.get_instruction("qwen_code_cli_agent")
assert len(instruction) > 0

# Load configuration
categories = loader.get_category_keywords()
assert "ai" in categories
```

### Test Backward Compatibility

```python
# Old API should still work
from config.agent_prompts import (
    QWEN_CODE_CLI_AGENT_INSTRUCTION,
    CATEGORY_KEYWORDS,
    MAX_TITLE_LENGTH
)

assert len(QWEN_CODE_CLI_AGENT_INSTRUCTION) > 0
assert "ai" in CATEGORY_KEYWORDS
assert MAX_TITLE_LENGTH == 60
```

## Benefits

1. **Version Control**: Easy to track changes in git
2. **A/B Testing**: Test different prompts by switching versions
3. **Rollback**: Quick rollback to previous version if needed
4. **Hot Reload**: Update prompts without restarting in development
5. **Multi-language**: Support for different languages
6. **Documentation**: Clear structure with metadata
7. **Maintainability**: Easier to edit and review
8. **Testing**: Easy to test different prompts
9. **Separation**: Prompts separated from code logic

## Best Practices

1. **Versioning**: Increment version for breaking changes
2. **Documentation**: Document changes in `config/prompts/README.md`
3. **Testing**: Test prompts thoroughly before deployment
4. **Backward Compatibility**: Keep old API working for existing code
5. **Clear Names**: Use descriptive names for agents and templates
6. **Metadata**: Include version, description, and language in YAML
7. **Comments**: Add comments in YAML for complex sections
8. **Validation**: Validate YAML syntax before committing

## Troubleshooting

### FileNotFoundError: Prompt file not found

```python
# Make sure the agent name matches the YAML filename
loader.get_instruction("qwen_code_cli_agent")  # ✓ Correct
loader.get_instruction("qwen_cli_agent")        # ✗ Wrong
```

### ValueError: Prompt version not found

```python
# Check available versions
loader = PromptLoader()
print(loader.list_versions())  # ['v1', 'v2']

# Use existing version
loader = PromptLoader(version="v1")  # ✓ Correct
```

### KeyError: Missing template variable

```python
# Make sure all required variables are provided
loader.format_template(
    "qwen_code_agent",
    "content_processing",
    instruction="...",  # Required
    text="...",         # Required
    urls_section=""     # Required
)
```

## Migration Checklist

- [x] Create `config/prompts/` directory structure
- [x] Create YAML files for all agent prompts
- [x] Create configuration YAML file
- [x] Implement PromptLoader class
- [x] Update `agent_prompts.py` for backward compatibility
- [x] Create example usage file
- [x] Create migration guide (this file)
- [x] Update documentation
- [ ] Update tests to use new system
- [ ] Test backward compatibility
- [ ] Deploy to production

## Support

For questions or issues:
1. Check `config/prompts/README.md`
2. Review `examples/prompt_loader_example.py`
3. Check this migration guide
4. Review existing agent implementations

## Future Enhancements

Possible future improvements:
- Prompt validation schemas
- Automatic prompt testing
- Prompt performance metrics
- Dynamic prompt selection based on context
- Prompt templates inheritance
- Support for external prompt repositories
