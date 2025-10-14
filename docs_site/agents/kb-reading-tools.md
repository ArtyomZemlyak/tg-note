# Knowledge Base Reading Tools

The autonomous agent provides tools to read and search content in your knowledge base. These tools let the agent inspect existing data before creating new content.

## Available Tools

### 1. `kb_read_file` — Read files

Reads one or more files from the knowledge base.

Parameters:
- `paths` (array of strings, required) — List of relative file paths

Example:
```json
{
  "paths": ["topics/ai/neural-networks.md", "topics/tech/python.md"]
}
```

Returns:
```json
{
  "success": true,
  "files_read": 2,
  "results": [
    {
      "path": "topics/ai/neural-networks.md",
      "full_path": "/path/to/kb/topics/ai/neural-networks.md",
      "content": "# Neural Networks\n\n...",
      "size": 1234
    }
  ],
  "errors": null
}
```

Notes:
- Reads multiple files in a single call
- Validates paths to prevent path traversal
- Returns content and metadata
- Handles per-file errors

---

### 2. `kb_list_directory` — List directory contents

Lists files and folders at a given path.

Parameters:
- `path` (string, required) — Relative directory path; empty for root
- `recursive` (boolean, optional) — Recursively list subdirectories (default false)

Example:
```json
{
  "path": "topics/ai",
  "recursive": false
}
```

Returns:
```json
{
  "success": true,
  "path": "topics/ai",
  "recursive": false,
  "files": [
    { "path": "topics/ai/neural-networks.md", "name": "neural-networks.md", "size": 1234 }
  ],
  "directories": [
    { "path": "topics/ai/machine-learning", "name": "machine-learning" }
  ],
  "file_count": 1,
  "directory_count": 1
}
```

---

### 3. `kb_search_files` — Search files by name

Searches files and folders by name or glob pattern.

Parameters:
- `pattern` (string, required) — Glob pattern (`*`, `?`, `[]`)
- `case_sensitive` (boolean, optional) — Case-sensitive search (default false)

Examples:
- `*.md` — all markdown files
- `ai/**/*.md` — all markdown files under `ai` recursively
- `*neural*` — names containing "neural"

Example:
```json
{ "pattern": "*neural*.md", "case_sensitive": false }
```

Returns:
```json
{
  "success": true,
  "pattern": "*neural*.md",
  "case_sensitive": false,
  "files": [
    { "path": "topics/ai/neural-networks.md", "name": "neural-networks.md", "size": 1234 }
  ],
  "directories": [],
  "file_count": 1,
  "directory_count": 0
}
```

---

### 4. `kb_search_content` — Full-text search

Searches text inside files.

Parameters:
- `query` (string, required)
- `case_sensitive` (boolean, optional) — default false
- `file_pattern` (string, optional) — glob to filter files (default `*.md`)

Example:
```json
{ "query": "machine learning", "case_sensitive": false, "file_pattern": "*.md" }
```

Returns:
```json
{
  "success": true,
  "query": "machine learning",
  "case_sensitive": false,
  "file_pattern": "*.md",
  "matches": [
    {
      "path": "topics/ai/neural-networks.md",
      "name": "neural-networks.md",
      "occurrences": 3,
      "matches": [
        {
          "line_number": 5,
          "line": "Machine learning is a subset of AI",
          "context": "# Introduction\n\nMachine learning is a subset of AI\nthat focuses on..."
        }
      ]
    }
  ],
  "files_found": 1
}
```

Security:
- Validates paths to prevent traversal
- Access is limited to `kb_root_path`

## Usage examples

### Scenario 1: Check existing content before creating
```python
# Search existing files
result = await agent._execute_tool({
    "tool_name": "kb_search_files",
    "tool_params": {"pattern": "*neural*.md"}
})

# If found, read them
if result["file_count"] > 0:
    read_result = await agent._execute_tool({
        "tool_name": "kb_read_file",
        "tool_params": {"paths": [f["path"] for f in result["files"]]}
    })
    # Analyze to avoid duplication
```

### Scenario 2: Structured KB exploration
```python
# List all categories
dirs = await agent._execute_tool({
    "tool_name": "kb_list_directory",
    "tool_params": {"path": "topics", "recursive": False}
})

# For each category, get stats
for category in dirs["directories"]:
    files = await agent._execute_tool({
        "tool_name": "kb_list_directory",
        "tool_params": {"path": category["path"], "recursive": True}
    })
```

### Scenario 3: Find related topics
```python
# Find all mentions of "Python"
python_refs = await agent._execute_tool({
    "tool_name": "kb_search_content",
    "tool_params": {"query": "Python", "file_pattern": "*.md"}
})
```

## Integration with agent loop

These tools are available in the agent toolset and can be called via function calling.

```python
agent = AutonomousAgent(
    llm_connector=openai_connector,
    kb_root_path=Path("./my_knowledge_base")
)

result = await agent.process({
    "text": "Find and summarize all articles about machine learning"
})
```

LLM decides:
1. Which tools to use
2. In what order
3. How to combine results

## Performance

Recommendations:
- Read a handful of files at once (10–20 max)
- Avoid recursive listings unless needed
- Use specific glob patterns rather than `*`
- Provide `file_pattern` for content searches

Limits:
- `kb_search_content` returns up to 5 matches per file
- Recursive listing can be slow on large KBs
