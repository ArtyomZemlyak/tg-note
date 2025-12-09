# Media Instructions System

Centralized media-handling instructions (images/video/audio/docs) for all agent modes.

---

## Overview

Unified media-handling instructions (images, video, audio, documents) are stored in a single file and injected into every agent prompt. This guarantees consistent rules for the `media/` folder and simplifies updates.

---

## Architecture

### File structure

```
config/prompts/
├── media/
│   └── instruction.ru.v1.md        ← Centralized media instructions
├── ask_mode/
│   └── instruction.ru.v2.md        ← Contains {instruction_media}
├── qwen_code_cli/
│   └── instruction.ru.v4.md        ← Contains {instruction_media}
├── autonomous_agent/
│   └── instruction.ru.v3.md        ← Contains {instruction_media}
└── content_processing/
    └── template.ru.v2.md           ← Contains media instructions inline
```

### Loading flow

```
┌─────────────────────────────────────┐
│  config/agent_prompts.py            │
│  get_media_instruction("ru")        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  config/prompts/media/              │
│  instruction.ru.v1.md               │
│  [Media handling instructions]      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Service Layer                      │
│  - question_answering_service.py    │
│  - agent_task_service.py            │
│  - qwen_code_cli_agent.py           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Formatted prompt with media        │
│  instruction_media → actual text    │
└─────────────────────────────────────┘
```

---

## Implementation

### 1. Centralized instructions file

**File:** `config/prompts/media/instruction.ru.v1.md`

Holds all rules for media handling:
- Media file list format
- How to read `.md` metadata files
- Relative path rules
- Duplicate prevention
- GitHub rendering (image + description)

### 2. Placeholder in agent prompts

All agent prompts include:

```markdown
{instruction_media}
```

This placeholder is replaced at runtime with the actual instructions.

**Files with the placeholder:**
- `config/prompts/ask_mode/instruction.ru.v2.md`
- `config/prompts/qwen_code_cli/instruction.ru.v4.md`
- `config/prompts/autonomous_agent/instruction.ru.v3.md`

### 3. Loading function

**File:** `config/agent_prompts.py`

```python
def get_media_instruction(locale: str = "ru", version: str | None = None) -> str:
    return prompt_registry.get("media.instruction", locale=locale, version=version)
```

### 4. Injection points

#### A. Ask Mode (`question_answering_service.py`)

```python
from config.agent_prompts import get_ask_mode_instruction, get_media_instruction

ask_instr = get_ask_mode_instruction("ru")
media_instr = get_media_instruction("ru")
ask_instr = ask_instr.format(instruction_media=media_instr)

user_agent.set_instruction(ask_instr)
```

#### B. Agent Mode (`agent_task_service.py`)

```python
from config.agent_prompts import get_qwen_code_agent_instruction, get_media_instruction

instr = get_qwen_code_agent_instruction("ru")
media_instr = get_media_instruction("ru")
response_formatter_prompt = response_formatter.generate_prompt_text()

instr = instr.format(
    instruction_media=media_instr,
    response_format=response_formatter_prompt
)

user_agent.set_instruction(instr)
```

#### C. Note Mode (`qwen_code_cli_agent.py`)

```python
from config.agent_prompts import get_media_instruction, get_qwen_code_cli_instruction

media_instr = get_media_instruction("ru")
response_formatter_prompt = response_formatter.generate_prompt_text()

default_instruction_with_formatter = self.DEFAULT_INSTRUCTION.format(
    instruction_media=media_instr,
    response_format=response_formatter_prompt
)

self.instruction = instruction or default_instruction_with_formatter
```

---

## Content Processing Template

`content_processing/template.ru.v2.md` also embeds media instructions, but **inline** (not via placeholder) because:
1. Different context (processing incoming messages)
2. Instructions are part of the template structure
3. Position matters (before "Incoming information")

If you need to update media instructions for content processing, edit the template directly.

---

## Benefits

### 1. Single source of truth

Update media instructions in **one file**:
```
config/prompts/media/instruction.ru.v1.md
```
All modes pick up the change automatically.

### 2. Consistency across modes

- `/note` mode (default)
- `/ask` mode (questions)
- `/agent` mode (autonomous tasks)

All use the same media instructions.

### 3. Easy versioning

Create new versions:
```
config/prompts/media/
├── instruction.ru.v1.md   ← current
└── instruction.ru.v2.md   ← future improvements
```

Switch version in code:
```python
get_media_instruction("ru", version="v2")
```

### 4. Testability

Easy to test different instruction sets without changing agent code.

---

## Updating instructions

1. Edit `config/prompts/media/instruction.ru.v1.md`
2. If using a new version, add `instruction.ru.v2.md` and switch version in `get_media_instruction`
3. Run regression tests for prompt rendering (ask/note/agent modes)

---

## Notes on locales

- Current files use the `ru` locale suffix; add `instruction.en.v1.md` if you maintain an English-only prompt set.
- `get_media_instruction(locale="en")` will load the English file when present.

---

## AICODE-NOTE
- Centralize media rules once, reuse everywhere.
- Placeholder-based injection keeps prompts short and consistent.
- Inline instructions remain only where template structure requires fixed positioning.
