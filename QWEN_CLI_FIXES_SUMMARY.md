# Qwen CLI Agent Fixes and Improvements

**Date:** 2025-10-06  
**Branch:** cursor/configure-qwen-coder-cli-approval-and-project-root-3db7

## Summary

Fixed critical issues with qwen-code-cli agent integration that caused:
1. Files being created in the wrong directory (project root instead of user's knowledge base)
2. Lack of documentation about required approval mode configuration

## Issues Fixed

### Issue 1: Files Created in Wrong Location

**Problem:**
- qwen-code-cli was creating files relative to the bot's working directory (project root)
- Files were ending up in paths like `ai/models/granite-4.0.md` instead of `knowledge_bases/my-note/ai/models/granite-4.0.md`
- This happened because the CLI's working directory was not set to the user's knowledge base path

**Root Cause:**
- The `QwenCodeCLIAgent` was initialized with `working_directory=os.getcwd()` by default
- This working directory was set once at agent creation and never changed
- Each user might have a different KB path, and the same user might switch between KBs
- The agent is cached per user, so the working directory couldn't be set at initialization time

**Solution:**
1. Added `set_working_directory()` and `get_working_directory()` methods to `QwenCodeCLIAgent`
2. Modified `NoteCreationService` to dynamically set the working directory to the user's KB path before processing
3. Now the CLI runs inside the correct knowledge base directory, ensuring files are created in the right location

**Files Changed:**
- `src/agents/qwen_code_cli_agent.py`: Added setter/getter methods for working_directory
- `src/services/note_creation_service.py`: Added call to `set_working_directory()` before agent processing
- `tests/test_qwen_code_cli_agent.py`: Added tests for working directory functionality

### Issue 2: Missing Approval Mode Documentation

**Problem:**
- qwen-code-cli requires manual approval for each action by default (interactive mode)
- The bot cannot interact with CLI in interactive mode, causing it to hang
- Users were not aware they needed to configure `/approval-mode yolo`

**Solution:**
- Added comprehensive documentation about `/approval-mode` requirement in installation steps
- Explained why `yolo` mode is necessary (bot runs autonomously without user interaction)
- Added warnings about security implications of `yolo` mode
- Documented all available approval modes and their use cases
- Referenced official qwen-code-cli documentation

**Files Changed:**
- `docs_site/agents/qwen-code-cli.md`: Added installation step 5 with approval mode configuration
- `docs_site/agents/qwen-code-cli.md`: Added troubleshooting section

## Code Changes

### 1. `src/agents/qwen_code_cli_agent.py`

Added methods to dynamically update working directory:

```python
def set_working_directory(self, working_directory: str) -> None:
    """Update working directory for qwen CLI execution"""
    self.working_directory = working_directory
    logger.info(f"Working directory updated to: {self.working_directory}")

def get_working_directory(self) -> str:
    """Get current working directory"""
    return self.working_directory
```

### 2. `src/services/note_creation_service.py`

Added working directory update before processing:

```python
user_agent = self.user_context_manager.get_or_create_agent(user_id)

# Set working directory to user's KB path for qwen-code-cli agent
# This ensures files created by the CLI are in the correct location
if hasattr(user_agent, 'set_working_directory'):
    user_agent.set_working_directory(str(kb_path))
    self.logger.debug(f"Set agent working directory to: {kb_path}")

processed_content = await user_agent.process(content)
```

### 3. `tests/test_qwen_code_cli_agent.py`

Added tests for working directory functionality:

```python
def test_set_working_directory(self, agent):
    """Test setting working directory dynamically"""
    # ...

def test_working_directory_persistence(self, mock_cli_check):
    """Test that working directory persists across method calls"""
    # ...
```

## Documentation Updates

### 1. Installation Instructions

Added critical step for approval mode configuration:

```markdown
### 5. Configure Approval Mode (IMPORTANT!)

**⚠️ КРИТИЧЕСКИ ВАЖНО:** Для корректной работы CLI с ботом необходимо настроить режим одобрения инструментов:

\`\`\`bash
qwen
/approval-mode yolo --project
\`\`\`
```

### 2. How It Works Section

Updated workflow to explain working directory handling:

```markdown
1. Message received
2. Agent prepares prompt
3. CLI working directory set to user's knowledge base path
4. Calls `qwen` CLI in KB directory
5. Qwen creates TODO plan
6. Executes plan with tools (files created in correct KB location)
7. Returns structured markdown
8. Saved to KB
```

### 3. Troubleshooting Section

Added comprehensive troubleshooting guide covering:
- Files created in wrong location
- CLI requires manual approval
- Authentication issues
- CLI not found errors

## Testing

### Test Coverage

1. **Unit Tests:**
   - `test_set_working_directory`: Verifies working directory can be changed dynamically
   - `test_working_directory_persistence`: Ensures working directory persists correctly

2. **Manual Testing Checklist:**
   - [ ] Create note with qwen-cli agent
   - [ ] Verify files are created in `knowledge_bases/<kb-name>/` directory
   - [ ] Verify file structure matches expected KB structure
   - [ ] Test with multiple users and different KB paths
   - [ ] Verify agent caching still works correctly

## Impact

### Before Fix
- Files created in: `/workspace/ai/models/granite-4.0.md`
- Required manual intervention for every CLI action
- Users confused about setup requirements

### After Fix
- Files created in: `/workspace/knowledge_bases/my-note/ai/models/granite-4.0.md`
- CLI runs autonomously with proper configuration
- Clear documentation guides users through setup

## Migration Notes

**For existing users:**

1. Update to latest version
2. Configure approval mode:
   ```bash
   qwen
   /approval-mode yolo --project
   ```
3. No code changes needed - working directory is now set automatically

**Backward Compatibility:**
- ✅ Fully backward compatible
- The `set_working_directory()` method is only called if the agent supports it (using `hasattr` check)
- Existing agents without this method will continue to work (though with the old behavior)

## Security Considerations

**Approval Mode:**
- Using `yolo` mode gives the agent full access to file operations and commands
- Users should be aware of the security implications
- Documentation includes clear warnings and references to official docs
- Users can limit access by:
  - Using project-scoped approval (`--project`)
  - Running bot in isolated environment
  - Reviewing agent prompts and configurations

## Future Improvements

1. Consider adding configuration option to restrict which directories the CLI can access
2. Add logging of all file operations performed by the CLI
3. Consider implementing a whitelist of allowed file paths
4. Add metrics/monitoring for CLI operations

## References

- Issue reported by user on 2025-10-06
- qwen-code-cli documentation: https://github.com/QwenLM/qwen-code
- Related discussion in: `docs_site/agents/qwen-cli-debug-trace.md`

## Checklist

- [x] Code changes implemented
- [x] Tests added
- [x] Documentation updated
- [x] Security warnings added
- [x] Backward compatibility maintained
- [x] User migration path documented
