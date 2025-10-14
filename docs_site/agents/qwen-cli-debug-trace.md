# Qwen CLI Agent - DEBUG tracing

## Overview

QwenCodeCLIAgent supports detailed DEBUG logging for troubleshooting and monitoring qwen-code CLI execution. You get a full execution trace including:

- CLI commands and arguments
- Input (prompt)
- Output (result)
- Environment variables
- Timing
- Errors and warnings

## Quick start

### 1. Configure logging

```python
from pathlib import Path
from config.logging_config import setup_logging

# Enable DEBUG logging
setup_logging(
    log_level="DEBUG",
    log_file=Path("logs/qwen_debug.log"),
    enable_debug_trace=True
)
```

### 2. Use the agent

```python
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

# Create agent
agent = QwenCodeCLIAgent(
    enable_web_search=True,
    enable_git=True,
    timeout=300
)

# Process content
content = {
    "text": "Your text for processing",
    "urls": ["https://example.com"]
}

result = await agent.process(content)
```

### 3. Check logs

Logs will be written to:

- `logs/qwen_debug.log` — main log (all levels)
- `logs/qwen_debug_debug.log` — DEBUG-only messages

## What gets logged

### Agent initialization

```
[DEBUG] [QwenCodeCLIAgent._check_cli_available] Checking qwen CLI availability...
[DEBUG] [QwenCodeCLIAgent._check_cli_available] CLI path: qwen
[DEBUG] [QwenCodeCLIAgent._check_cli_available] Running command: qwen --version
[DEBUG] [QwenCodeCLIAgent._check_cli_available] Return code: 0
[DEBUG] [QwenCodeCLIAgent._check_cli_available] STDOUT: qwen version 1.0.0
[DEBUG] [QwenCodeCLIAgent._check_cli_available] STDERR:
```

### CLI execution

```
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === CLI EXECUTION TRACE START ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Command: qwen
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Working dir: /workspace
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Environment variables:
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli]   OPENAI_API_KEY=sk-xxxxx...
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli]   OPENAI_BASE_URL=https://api.openai.com

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === STDIN (PROMPT) ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Prompt length: 1234 characters
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Prompt preview (first 500 chars):
You are an autonomous content processing agent...

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === FULL PROMPT ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli]
<full prompt text>
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === END FULL PROMPT ===

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Starting subprocess at 1234567890.123
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Process created with PID: 12345
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Sending prompt to stdin...

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Process completed in 15.42s
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Process return code: 0

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === STDERR OUTPUT ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] STDERR length: 0 characters
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] STDERR is empty
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === END STDERR OUTPUT ===

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === STDOUT OUTPUT ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] STDOUT length: 5678 characters
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] STDOUT preview (first 500 chars):
# Machine Learning Article
...

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === FULL STDOUT ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli]
<full result text>
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === END FULL STDOUT ===

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === CLI EXECUTION TRACE END ===
```

### Result processing

```
[DEBUG] [QwenCodeCLIAgent] STEP 1: Preparing prompt for qwen-code
[DEBUG] [QwenCodeCLIAgent] Prepared prompt length: 1234 characters

[DEBUG] [QwenCodeCLIAgent] STEP 2: Executing qwen-code CLI
[DEBUG] [QwenCodeCLIAgent] Received result length: 5678 characters

[DEBUG] [QwenCodeCLIAgent] STEP 3: Parsing agent response with standard parser
[DEBUG] [QwenCodeCLIAgent] Result text preview (first 500 chars): ...
[DEBUG] [QwenCodeCLIAgent] Files created: ['path/to/file.md']
[DEBUG] [QwenCodeCLIAgent] Folders created: ['path/to/folder']

[INFO] [QwenCodeCLIAgent] Successfully processed content: title='Machine Learning'
```

## Log levels

### DEBUG

- Use in development
- Full CLI execution details

### INFO

- Use in production
- Key events only

### WARNING

- Minimal logging, warnings only

### ERROR

- Critical errors only

## Examples

### Example 1: Debugging CLI issues

```python
import asyncio
from pathlib import Path
from config.logging_config import setup_logging
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

async def debug_cli_issue():
    # Enable detailed logging
    setup_logging(
        log_level="DEBUG",
        log_file=Path("logs/debug.log"),
        enable_debug_trace=True
    )

    agent = QwenCodeCLIAgent(timeout=60)

    try:
        result = await agent.process({"text": "Test content", "urls": []})
        print(f"Success: {result['title']}")
    except Exception as e:
        print(f"Error: {e}")
        print("Check logs/debug.log and logs/debug_debug.log for details")

asyncio.run(debug_cli_issue())
```

### Example 2: Production monitoring

```python
import asyncio
from pathlib import Path
from config.logging_config import setup_logging
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

async def production_monitoring():
    # Moderate logging for production
    setup_logging(
        log_level="INFO",
        log_file=Path("logs/production.log"),
        enable_debug_trace=False
    )

    agent = QwenCodeCLIAgent()
    result = await agent.process(content)

    # Logs contain only important events (start/end, title/category, errors)

asyncio.run(production_monitoring())
```

### Example 3: Performance analysis

```python
import asyncio
import time
from pathlib import Path
from config.logging_config import setup_logging
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

async def performance_analysis():
    # DEBUG for timing analysis
    setup_logging(
        log_level="DEBUG",
        log_file=Path("logs/performance.log"),
        enable_debug_trace=True
    )

    agent = QwenCodeCLIAgent()

    start = time.time()
    result = await agent.process(content)
    end = time.time()

    print(f"Total time: {end - start:.2f}s")
    # Logs include detailed timing for each step

asyncio.run(performance_analysis())
```

## Reading logs

### Log file structure

1. Main log (`logs/qwen_debug.log`): All levels, rotation 10 MB, retention 7 days, ZIP compression
2. Debug-only log (`logs/qwen_debug_debug.log`): DEBUG only, rotation 50 MB, retention 3 days, ZIP compression

### Entry format

```
2024-10-03 15:30:45.123 | DEBUG    | qwen_code_cli_agent:_execute_qwen_cli:270 | [QwenCodeCLIAgent._execute_qwen_cli] Executing qwen-code CLI...
│                         │           │                      │                    │
│                         │           │                      │                    └─ Message
│                         │           │                      └─ Line number
│                         │           └─ Function
│                         └─ Level
└─ Timestamp
```

### Searching logs

```bash
# Find all CLI executions
grep "CLI EXECUTION TRACE" logs/qwen_debug.log

# Find errors
grep "ERROR" logs/qwen_debug.log

# Find timing
grep "Process completed in" logs/qwen_debug.log

# Only prompts
grep -A 20 "FULL PROMPT" logs/qwen_debug_debug.log

# Only results
grep -A 50 "FULL STDOUT" logs/qwen_debug_debug.log
```

## Security

### Masking sensitive data

API keys and tokens are masked in logs:

```python
# Environment variables:
OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef

# In logs:
OPENAI_API_KEY=sk-12345...
```

### Protected variables

Masked variables include those containing:

- `KEY`
- `TOKEN`
- `SECRET`
- `PASSWORD`

## Performance

### Overhead

| Level | Overhead | Log size | Recommendation |
|-------|----------|----------|----------------|
| DEBUG | ~5-10%   | Large    | Development    |
| INFO  | ~1-2%    | Medium   | Production     |
| WARNING | <1%    | Small    | Production     |
| ERROR | <0.5%    | Minimal  | Production     |

### Recommendations

- Development/Testing: DEBUG + enable_debug_trace
- Staging: INFO or DEBUG as needed; disable debug trace unless required
- Production: INFO/WARNING; enable DEBUG temporarily for incident analysis

## Troubleshooting

### Problem: No logs created
**Solution:** Ensure log directory exists and call setup_logging with DEBUG level.

### Problem: Too many logs
**Solution:** Reduce log level to INFO or WARNING; disable debug trace.

### Problem: No detailed CLI trace
**Solution:** Use DEBUG level and enable_debug_trace=True.

### Problem: Logs too large
**Solution:** Adjust rotation/retention settings for log files.
