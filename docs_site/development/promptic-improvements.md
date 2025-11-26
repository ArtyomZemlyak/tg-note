# Promptic Library - Improvements for tg-note Integration

This document describes improvements that could enhance the promptic library for better integration with tg-note and similar projects.

## Current Usage in tg-note

The tg-note project uses promptic for unified prompt management:

```python
from src.prompts import prompt_service

# Complete note mode prompt in ONE LINE:
prompt = prompt_service.render(
    "note_mode_prompt",
    version="latest",
    vars={"text": "User content", "urls": ["https://example.com"]},
    export_to="output/prompt.md"  # optional
)

# Complete ask mode prompt in ONE LINE:
prompt = prompt_service.render(
    "ask_mode_prompt",
    version="latest",
    vars={"question": "What is GPT?", "kb_path": "/kb"}
)
```

## Missing Features for tg-note

### 1. Locale Support in File Naming

**Current Limitation:**
Promptic uses file naming convention like `name_v1.0.0.md`, but tg-note needs locale support:
- tg-note: `instruction.ru.v4.md` (includes locale)
- promptic: `task_v1.0.0.md` (no locale)

**Proposed Enhancement:**
Add locale support to file naming and resolution:

```python
# Proposed API
render("task", version="v1.0.0", locale="ru")

# Would look for files in order:
# 1. task_ru_v1.0.0.md
# 2. task_v1.0.0.ru.md
# 3. ru/task_v1.0.0.md (locale as directory)
# 4. task_v1.0.0.md (fallback)
```

### 2. Composite Prompt Support

**Current Limitation:**
Each render() call loads a single file. For complex prompts that combine multiple components (instruction + template + formatter), multiple calls are needed.

**Proposed Enhancement:**
Support composite prompts with automatic component resolution:

```yaml
# prompts/note_mode/main.yaml
type: composite
components:
  - instruction: qwen_code_cli/instruction
  - media: media/instruction
  - template: content_processing/template
  - formatter: response_formatter/instruction
variables:
  text: ""
  urls: []
```

```python
# Single call renders composite prompt
prompt = render("note_mode", vars={"text": "...", "urls": [...]})
```

### 3. Variable Validation

**Current Limitation:**
No validation of required variables - missing variables result in unreplaced `{placeholders}` in output.

**Proposed Enhancement:**
Add variable schema support:

```python
# In prompt file (YAML frontmatter):
---
variables:
  text:
    type: string
    required: true
  urls:
    type: array
    default: []
  locale:
    type: string
    enum: ["ru", "en"]
    default: "ru"
---

# API would validate:
render("task", vars={"text": "..."})  # OK
render("task", vars={})  # Raises ValidationError: 'text' is required
```

### 4. Async Support

**Current Limitation:**
All promptic operations are synchronous.

**Proposed Enhancement:**
Add async versions for better integration with async codebases:

```python
# Sync (current)
prompt = render("task", version="latest", vars={...})

# Async (proposed)
prompt = await arender("task", version="latest", vars={...})
```

### 5. Caching Layer

**Current Limitation:**
Files are read on every render() call.

**Proposed Enhancement:**
Add configurable caching:

```python
from promptic import render, configure_cache

# Configure caching
configure_cache(
    enabled=True,
    ttl=300,  # 5 minutes
    max_size=100,  # max cached prompts
)

# Subsequent calls use cache
prompt1 = render("task", version="v1")  # File read
prompt2 = render("task", version="v1")  # From cache
```

## General Improvements

### 1. Better Error Messages

**Current:**
```
FileNotFoundError: Prompt not found for key='task', version='v2'
```

**Proposed:**
```
PrompticError: Prompt 'task' version 'v2' not found.
Available versions: v1.0.0, v1.1.0
Searched paths:
  - prompts/task_v2.md
  - prompts/task_v2.0.0.md
Suggestion: Use version='latest' or specify one of: v1.0.0, v1.1.0
```

### 2. CLI Tool for Prompt Management

Add a CLI for common operations:

```bash
# List available prompts
promptic list --dir prompts/

# Show prompt info
promptic info prompts/task

# Render and preview
promptic render prompts/task --version=v1 --var text="Hello"

# Validate prompt structure
promptic validate prompts/

# Create new versioned prompt
promptic new prompts/task --version=v2.0.0 --from=v1.0.0
```

### 3. Prompt Testing Framework

Add testing utilities for prompts:

```python
from promptic.testing import PromptTestCase

class TestAgentPrompts(PromptTestCase):
    prompts_dir = "config/prompts"

    def test_note_mode_prompt_renders(self):
        prompt = self.render("note_mode", vars={"text": "Test"})
        self.assertContains(prompt, "# Инструкция")
        self.assertContains(prompt, "Test")
        self.assertNoUnresolvedVars(prompt)

    def test_all_versions_valid(self):
        for version in self.get_versions("task"):
            prompt = self.render("task", version=version)
            self.assertValidMarkdown(prompt)
```

### 4. Prompt Diff and Migration Tools

```bash
# Compare versions
promptic diff prompts/task v1.0.0 v2.0.0

# Generate migration guide
promptic migrate prompts/task v1.0.0 v2.0.0 --output=migration.md
```

### 5. Integration with LLM Frameworks

Add optional integrations with popular frameworks:

```python
# LangChain integration
from promptic.integrations import langchain_template
template = langchain_template("prompts/task", version="v1")

# LlamaIndex integration  
from promptic.integrations import llama_prompt_template
prompt = llama_prompt_template("prompts/task")
```

## Development Perspectives

### Short-term (1-3 months)

1. **Locale support** - Critical for international projects
2. **Variable validation** - Prevents runtime errors
3. **Better error messages** - Improves developer experience
4. **Caching layer** - Performance improvement

### Medium-term (3-6 months)

1. **CLI tool** - Improves workflow
2. **Async support** - Better framework integration
3. **Testing framework** - Quality assurance
4. **Composite prompts** - Complex use case support

### Long-term (6-12 months)

1. **LLM framework integrations** - Ecosystem growth
2. **Prompt analytics** - Usage tracking and optimization
3. **Version control integration** - Git-aware versioning
4. **Prompt marketplace** - Community sharing

## tg-note Specific Requirements

1. **Multiple locales**: Russian (primary), English
2. **Agent modes**: note, ask, agent
3. **Component reuse**: Media instruction, response formatter shared across modes
4. **Runtime configuration**: Version selection, locale override
5. **Export capability**: Save rendered prompts for debugging

## Conclusion

The promptic library provides a solid foundation for prompt management with its file-first architecture and versioning support. The improvements outlined above would enhance its utility for production applications like tg-note.

Key priorities for tg-note integration:
1. Locale support in file naming
2. Composite prompt support
3. Variable validation
4. Caching for performance

These enhancements would make promptic a comprehensive solution for prompt engineering in production LLM applications.
