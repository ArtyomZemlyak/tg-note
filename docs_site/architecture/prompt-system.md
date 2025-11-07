# Prompt System

This project uses a versioned, locale-aware prompt registry to manage system and template prompts for agents.

## Storage layout

- Base directory: `config/prompts/`
- Keys are dot-separated: e.g. `qwen_code_cli.instruction`
- Path resolution:
  - Directory path = all key segments except the last (e.g. `qwen_code_cli/`)
  - File name = `<last-segment>.<locale>.v<semver>.md`

Examples:
- `qwen_code_cli.instruction` (ru) -> `config/prompts/qwen_code_cli/instruction.ru.v1.md`
- `content_processing.template` (ru) -> `config/prompts/content_processing/template.ru.v1.md`

If no version is specified, the registry picks the highest available version.

## Access in code

Use accessors from `config/agent_prompts.py`:

```python
from config.agent_prompts import (
    get_qwen_code_cli_instruction,
    get_content_processing_template,
    get_kb_query_template,
)

instruction = get_qwen_code_cli_instruction(locale="ru")
template = get_content_processing_template(locale="ru")
kb_query = get_kb_query_template(locale="ru")
```

Backward-compatible constants are preserved for existing imports:
- `QWEN_CODE_CLI_AGENT_INSTRUCTION`
- `CONTENT_PROCESSING_PROMPT_TEMPLATE`
- `KB_QUERY_PROMPT_TEMPLATE`

## Rationale

- Avoids duplication of large multiline prompt strings in code
- Enables prompt versioning and easy experimentation
- Supports multiple locales
- Keeps tests stable via backward-compatible constants

## Adding/Updating a prompt

1. Create a new file with incremented version, e.g. `instruction.ru.v2.md`
2. Update code to pin a specific version if needed: `get_qwen_code_cli_instruction("ru", version="v2")`
3. Run tests

## Recent Updates

### v3/v4 - Source Citation Requirements (2025-11)

Added mandatory source citation instructions to agent prompts:

- **autonomous_agent.instruction** (ru/en v3) - Added detailed section on source citations
- **qwen_code_cli.instruction** (ru v4) - Added source citation requirements
- **AGENT_MODE_INSTRUCTION** - Updated with source citation rules

All agents now MUST include:
- Inline citations throughout the text
- "Sources" section at the end of every created document
- Preservation of all source URLs from original materials
