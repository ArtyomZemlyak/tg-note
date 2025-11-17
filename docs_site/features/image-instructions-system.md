# Media Instructions System

 Centralized media handling instructions (images/video/audio/docs) for all agent modes.

---

## Overview

Unified media-handling instructions (images, видео, аудио, документы) хранятся в одном файле и автоматически подмешиваются во все агентские промпты. Это гарантирует единые правила работы с папкой `media/` и упрощает обновление.

---

## Architecture

### File Structure

```
config/prompts/
├── media/
│   └── instruction.ru.v1.md        ← Centralized image instructions
├── ask_mode/
│   └── instruction.ru.v2.md        ← Contains {instruction_media}
├── qwen_code_cli/
│   └── instruction.ru.v4.md        ← Contains {instruction_media}
├── autonomous_agent/
│   └── instruction.ru.v3.md        ← Contains {instruction_media}
└── content_processing/
    └── template.ru.v2.md           ← Contains image instructions inline
```

### Loading Flow

```
┌─────────────────────────────────────┐
│  config/agent_prompts.py            │
│  get_media_instruction("ru")       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  config/prompts/media/              │
│  instruction.ru.v1.md                │
│  [Image handling instructions]       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Service Layer                       │
│  - question_answering_service.py     │
│  - agent_task_service.py             │
│  - qwen_code_cli_agent.py            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Formatted Prompt with Images        │
│  instruction_media → actual content │
└─────────────────────────────────────┘
```

---

## Implementation

### 1. Centralized Instructions File

**File:** `config/prompts/media/instruction.ru.v1.md`

Contains all instructions for working with images:
- Media file list format
- How to read `.md` metadata files
- Relative path rules
- Duplicate prevention
- GitHub rendering (dual descriptions)

### 2. Placeholder in Agent Prompts

All agent prompts now have:

```markdown
{instruction_media}
```

This placeholder gets replaced at runtime with the actual instructions.

**Files with placeholder:**
- `config/prompts/ask_mode/instruction.ru.v2.md`
- `config/prompts/qwen_code_cli/instruction.ru.v4.md`
- `config/prompts/autonomous_agent/instruction.ru.v3.md`

### 3. Loading Function

**File:** `config/agent_prompts.py`

```python
def get_media_instruction(locale: str = "ru", version: str | None = None) -> str:
    return prompt_registry.get("media.instruction", locale=locale, version=version)
```

### 4. Injection Points

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

The `content_processing/template.ru.v2.md` also contains image instructions, but **inline** (not via placeholder). This is because:

1. It's a different context (processing incoming messages)
2. Instructions are part of the template structure
3. Position matters (before "Входящая информация")

If you need to update image instructions for content processing, update the template directly.

---

## Benefits

### 1. Single Source of Truth

Update image instructions in **one file**:
```
config/prompts/media/instruction.ru.v1.md
```

All modes automatically get the update.

### 2. Consistency Across Modes

- `/note` mode (default)
- `/ask` mode (questions)
- `/agent` mode (autonomous tasks)

All use the same image handling instructions.

### 3. Easy Versioning

Create new versions:
```
config/prompts/media/
├── instruction.ru.v1.md   ← Current
└── instruction.ru.v2.md   ← Future improvements
```

Change version in code:
```python
get_media_instruction("ru", version="v2")
```

### 4. Testability

Easy to test different instruction sets without modifying agent code.

---

## Updating Instructions

### To update image instructions for all modes:

1. Edit the centralized file:
   ```bash
   vim config/prompts/media/instruction.ru.v1.md
   ```

2. Changes apply to:
   - Note mode (creating notes from messages)
   - Ask mode (answering questions)
   - Agent mode (autonomous tasks)

### To update for specific mode only:

Edit the mode's instruction file directly (but this breaks consistency):
```bash
vim config/prompts/ask_mode/instruction.ru.v2.md
```

**Not recommended** - defeats the purpose of centralization.

---

## Example: Full Prompt Generation

### Ask Mode

**Input:**
- User question: "Что такое GPT?"
- Media list:
  ```
  Медиафайлы:
  лежат в media/
img_123_example.jpg
  ```

**Prompt generation:**

1. Load ask instruction:
   ```python
   ask_instr = get_ask_mode_instruction("ru")
   # Contains: "{instruction_media}"
   ```

2. Load images instruction:
   ```python
   images_instr = get_media_instruction("ru")
   # Contains: "## Работа с изображениями..."
   ```

3. Format:
   ```python
   ask_instr = ask_instr.format(instruction_media=images_instr)
   # Result: Full prompt with image instructions embedded
   ```

4. Send to agent:
   ```python
   user_agent.set_instruction(ask_instr)
   ```

**Result:**
Agent receives complete instructions including:
- How to search KB
- How to work with images
- How to format response

---

## Migration Notes

### Before (Old System)

Each agent mode had its own image instructions (or none):
- Ask mode: No image instructions
- Agent mode: No image instructions
- Note mode: Image instructions in `content_processing/template.ru.v2.md`

**Problems:**
- Inconsistency
- Duplication
- Hard to maintain

### After (New System)

Centralized instructions + programmatic injection:
- All modes get same instructions
- Update in one place
- Consistent behavior

**Migration steps:**
1. ✅ Created `config/prompts/media/instruction.ru.v1.md`
2. ✅ Added `{instruction_media}` placeholders to agent prompts
3. ✅ Added `get_media_instruction()` function
4. ✅ Modified service layer to inject instructions
5. ✅ Tested all modes

---

## Testing

### Manual Test

1. Send image to bot in each mode
2. Check agent sees image instructions
3. Verify agent uses correct paths and descriptions

### Mode Test Matrix

| Mode | Receives Images? | Has Instructions? | Works? |
|------|------------------|-------------------|--------|
| `/note` | ✅ Yes | ✅ Yes | ✅ |
| `/ask` | ✅ Yes | ✅ Yes | ✅ |
| `/agent` | ✅ Yes | ✅ Yes | ✅ |

---

## Future Improvements

### 1. Multi-language Support

```python
get_media_instruction("en")  # English version
get_media_instruction("ru")  # Russian version
```

Create:
```
config/prompts/media/
├── instruction.en.v1.md
└── instruction.ru.v1.md
```

### 2. Context-Specific Instructions

```python
get_media_instruction("ru", context="ask")   # Shorter for Q&A
get_media_instruction("ru", context="note")  # Detailed for notes
```

### 3. Dynamic Instruction Generation

Based on:
- User's KB structure
- Image count
- Previous agent behavior

---

## See Also

- [Media Metadata System](media-metadata-system.md) - How `.md` files work
- [Image Prompt Format](image-prompt-format.md) - New compact format
- [Image Embedding](image-embedding.md) - Original system
