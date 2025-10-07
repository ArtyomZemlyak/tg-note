# Agent Prompts Configuration

This directory contains versioned prompt configurations for all agents in YAML format.

## Structure

```
prompts/
├── README.md           # This file
├── v1/                 # Version 1 prompts
│   ├── config.yaml               # General configuration
│   ├── qwen_code_agent.yaml      # Qwen Code Agent prompt
│   ├── qwen_code_cli_agent.yaml  # Qwen Code CLI Agent prompt
│   ├── kb_query.yaml             # KB Query agent prompt
│   └── stub_agent.yaml           # Stub agent prompt
└── v2/                 # Version 2 prompts (future)
```

## Version History

### v1 (2025-10-07)
- Initial version with all agent prompts migrated from Python to YAML
- Support for English and Russian instructions
- Standardized result format
- Configuration for categories, stop words, and tool safety

## Using Prompts

### Loading Prompts

```python
from config.prompt_loader import PromptLoader

# Load default version (latest)
loader = PromptLoader()

# Load specific version
loader = PromptLoader(version="v1")

# Get agent instruction
instruction = loader.get_instruction("qwen_code_cli_agent")

# Get template
template = loader.get_template("qwen_code_agent", "content_processing")

# Get configuration
categories = loader.get_config("category_keywords")
stop_words = loader.get_config("stop_words")
```

### Creating New Versions

1. Copy the latest version directory (e.g., `v1/` → `v2/`)
2. Update version in all YAML files
3. Make your changes
4. Update this README with version notes

## YAML Format

### Agent Prompt File

```yaml
version: "1.0.0"
name: "agent_name"
description: "Agent description"
language: "en"  # or "ru"
created_at: "YYYY-MM-DD"

instruction: |
  Multi-line instruction text...

templates:
  template_name: |
    Template with {placeholders}...
```

### Configuration File

```yaml
version: "1.0.0"
description: "Configuration description"

category_keywords:
  category_name:
    - keyword1
    - keyword2

markdown:
  max_title_length: 60
  # ...other settings

tools:
  safe_git_commands:
    - status
  # ...other settings
```

## Benefits

1. **Versioning**: Easy to track changes and rollback if needed
2. **Flexibility**: Prompts can be updated without code changes
3. **Multi-language**: Support for different languages
4. **Testing**: Easy to A/B test different prompts
5. **Maintainability**: Clear structure and documentation
6. **Hot-reloading**: Can reload prompts without restarting

## Migration from Python

The old `config/agent_prompts.py` is deprecated but still available for backward compatibility. All new code should use the YAML-based system.

## Best Practices

1. Always increment version when making breaking changes
2. Document changes in this README
3. Test prompts thoroughly before deploying
4. Keep backward compatibility when possible
5. Use clear, descriptive names for templates
