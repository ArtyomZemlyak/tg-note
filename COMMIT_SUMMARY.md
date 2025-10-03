# Integrate loguru for agent step tracing

## Summary
Integrated loguru logging library with comprehensive DEBUG-level tracing for all agent operations, replacing standard Python logging throughout the codebase.

## Key Changes

### 1. Dependencies
- Added `loguru==0.7.2` to `pyproject.toml`

### 2. New Files
- `config/logging_config.py`: Centralized logging configuration with DEBUG tracing support

### 3. Updated Files (15 total)

#### Core Application
- `main.py`: Migrated to loguru with DEBUG tracing setup

#### Agents (with detailed step tracing)
- `src/agents/qwen_code_agent.py`: Added DEBUG logging for all 5 processing steps
- `src/agents/qwen_code_cli_agent.py`: Added DEBUG logging for all 5 CLI execution steps
- `src/agents/agent_factory.py`: Migrated to loguru

#### Bot Components
- `src/bot/telegram_bot.py`: Migrated to loguru
- `src/bot/handlers.py`: Migrated to loguru
- `src/bot/settings_handlers.py`: Migrated to loguru
- `src/bot/settings_manager.py`: Migrated to loguru

#### Processing & Storage
- `src/processor/message_aggregator.py`: Migrated to loguru
- `src/tracker/processing_tracker.py`: Migrated to loguru
- `src/knowledge_base/repository.py`: Migrated to loguru
- `src/knowledge_base/git_ops.py`: Migrated to loguru
- `src/knowledge_base/user_settings.py`: Migrated to loguru

## Features

### Agent Step Tracing
When `LOG_LEVEL=DEBUG`, every agent step is logged:

**QwenCodeAgent**:
- STEP 1: Creating TODO plan
- STEP 2: Executing TODO plan (with per-task details)
- STEP 3: Structuring content
- STEP 4: Generating markdown
- STEP 5: Determining KB structure

**QwenCodeCLIAgent**:
- STEP 1: Preparing prompt
- STEP 2: Executing qwen CLI
- STEP 3: Parsing result
- STEP 4: Extracting components
- STEP 5: Creating KB structure

### Logging Configuration
- Console output with color coding
- File output with rotation (10 MB), retention (7 days), compression
- Separate DEBUG log file (50 MB rotation, 3 days retention)
- Automatic backtrace and diagnosis for errors
- Rich formatting: `<timestamp> | <level> | <module>:<function>:<line> | <message>`

## Usage

```bash
# Enable DEBUG tracing
export LOG_LEVEL=DEBUG
python main.py

# Logs will be written to:
# - logs/app.log (all levels)
# - logs/app_debug.log (DEBUG only)
```

## Benefits
1. **Detailed tracing**: Every agent step logged with full context
2. **Better debugging**: Complete visibility into agent operations
3. **Production ready**: Automatic log rotation and cleanup
4. **No configuration needed**: Works out of the box
5. **Better error tracking**: Automatic backtrace on exceptions

## Testing
- All modules import successfully
- No remaining `import logging` statements
- All logger instances use loguru
- DEBUG tracing tested with agent processing

## Documentation
- `LOGURU_MIGRATION_SUMMARY.md`: Technical migration details
- `LOGURU_INTEGRATION_COMPLETE.md`: Complete integration guide (RU/EN)

## Breaking Changes
None - fully backward compatible. Standard logging replaced transparently.
