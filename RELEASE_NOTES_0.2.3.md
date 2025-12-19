# Release 0.2.3

## 🎉 New Features

### Real-time Log Streaming
- **Streaming logs from qwen-code-cli**: Added real-time log streaming that displays the last 1000 characters of logs from `qwen-code-cli` execution in Telegram every 30 seconds
- **Separate error messages**: Errors from stderr are now displayed in a separate third message, keeping logs clean
- **Smart message updates**: Messages are only updated when content actually changes, reducing unnecessary API calls
- **Works in all modes**: Log streaming is enabled by default in all service modes (note creation, agent tasks, question answering)

### Enhanced Progress Tracking
- **Improved progress bar hierarchy**: Better display of folder paths in progress messages
- **Thread-safe progress monitoring**: Fixed thread safety issues in progress monitoring system
- **Explicit checkbox reminders**: Added explicit reminders in agent prompts to update checkboxes

## 🐛 Bug Fixes

- **SettingsManager fix**: Fixed `SettingsManager.get_setting()` call with invalid argument
- **Thread safety**: Fixed thread safety issues in progress monitoring
- **Checkbox format**: Fixed checkbox format in agent prompts
- **Log spam reduction**: Removed excessive DEBUG logging for chunk reading to reduce log spam
- **Error separation**: Fixed issue where errors were appearing in log messages instead of error messages

## 📚 Documentation

- **Progress tracking documentation**: Updated progress tracking documentation with best practices
- **Progress bar formatting**: Documented progress bar formatting improvements

## 🔧 Technical Improvements

- **Code quality**: Improved code formatting and structure
- **Error handling**: Better error handling and separation of stdout/stderr streams
- **Performance**: Reduced unnecessary message updates by checking if content changed
- **Logging**: Optimized logging to reduce spam while maintaining useful debug information

## 📝 Commit History

- Fix SettingsManager.get_setting() call with invalid argument
- Fix thread safety in progress monitoring
- Add explicit checkbox update reminders to agent prompts
- Update progress tracking documentation with best practices
- Improve progress bar formatting for better readability
- Document progress bar formatting improvements
- Fix checkbox format in agent prompts
- Improve progress bar hierarchy display with folder paths
- Add real-time log streaming from qwen-code-cli
- Separate error messages into dedicated Telegram message
- Optimize log updates to prevent unnecessary API calls
