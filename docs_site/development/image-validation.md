# Image Path Validation in Markdown

Automated validation of image paths in agent-generated markdown files.

---

## Overview

When AI agents generate markdown files with image references, they may accidentally:
- Use incorrect relative paths
- Reference non-existent images
- Use poor alt text descriptions
- Create broken image links

The **Markdown Image Validator** automatically checks for these issues and provides suggestions for fixes.

---

## How It Works

### Automatic Validation

When agents create or edit markdown files via `file_create` or `file_edit` tools, the validator automatically:

1. **Detects markdown files** (`.md` extension)
2. **Scans for image references** using regex: `![alt](path)`
3. **Resolves relative paths** from markdown file location
4. **Checks if images exist** in the file system
5. **Validates alt text quality** (meaningful descriptions)
6. **Logs warnings/errors** if issues found

### Validation Levels

| Severity | Description | Example |
|----------|-------------|---------|
| **ERROR** | Image file not found | `![Photo](media/missing.jpg)` - file doesn't exist |
| **WARNING** | Image outside KB media/ directory | `![Logo](../assets/logo.png)` - not in KB structure |
| **INFO** | Poor alt text quality | `![image](photo.jpg)` - generic description |

---

## Integration Points

### 1. File Creation Tool

When agents create markdown files:

```python
# src/agents/tools/file_tools.py - FileCreateTool
result = await tool.execute({
    "path": "topics/example.md",
    "content": "# Example\n\n![Chart](../media/chart.jpg)"
})

# Result includes validation status:
{
    "success": True,
    "path": "topics/example.md",
    "validation_warnings": [],
    "validation_passed": True
}
```

If validation fails:

```python
{
    "success": True,  # File still created
    "path": "topics/example.md",
    "validation_warnings": [
        "Image path validation failed - some images may not display correctly"
    ],
    "validation_passed": False
}
```

### 2. File Edit Tool

Same validation runs when agents edit markdown files via `file_edit` tool.

---

## Manual Validation

### CLI Tool

Validate entire knowledge base:

```bash
# Validate KB with summary
python scripts/validate_kb_images.py /path/to/kb

# Verbose mode (includes alt text quality checks)
python scripts/validate_kb_images.py /path/to/kb --verbose

# Strict mode (exit code 1 on any issues)
python scripts/validate_kb_images.py /path/to/kb --strict
```

**Example Output:**

```
🔍 Validating knowledge base: /home/user/knowledge_base

================================================================================
MARKDOWN IMAGE VALIDATION REPORT
================================================================================

Found issues in 2 file(s):

📄 topics/api-docs.md
--------------------------------------------------------------------------------
  ❌ Line 15: Image file not found: media/api-diagram.png (resolved to: /home/user/knowledge_base/topics/media/api-diagram.png)
     Image path: media/api-diagram.png
     💡 Suggestion: ../media/api-diagram.png

📄 topics/tutorial.md
--------------------------------------------------------------------------------
  ⚠️  Line 8: Image is outside KB images directory: /home/user/pictures/screenshot.jpg
     Image path: ../../pictures/screenshot.jpg

================================================================================
SUMMARY
================================================================================
❌ Errors:   1
⚠️  Warnings: 1

❌ Validation failed with 1 error(s)
```

### Python API

Validate specific file:

```python
from pathlib import Path
from src.processor.markdown_media_validator import validate_agent_generated_markdown

kb_root = Path("/path/to/kb")
md_file = kb_root / "topics" / "example.md"

# Returns True if no errors, False otherwise
passed = validate_agent_generated_markdown(md_file, kb_root)
```

Validate entire KB:

```python
from src.processor.markdown_media_validator import validate_kb_media

kb_root = Path("/path/to/kb")

# Returns number of errors found
error_count = validate_kb_media(kb_root, verbose=True)

if error_count == 0:
    print("✅ Validation passed!")
else:
    print(f"❌ Found {error_count} errors")
```

Advanced usage with validator class:

```python
from src.processor.markdown_media_validator import MarkdownMediaValidator

validator = MarkdownMediaValidator(kb_root)

# Validate single file
refs, issues = validator.validate_markdown_file(md_file, check_alt_text=True)

# Find unreferenced images
unreferenced = validator.find_unreferenced_images()
print(f"Found {len(unreferenced)} unused images")

# Generate report
issues_by_file = validator.validate_kb_directory(check_alt_text=True)
report = validator.generate_report(issues_by_file, verbose=True)
print(report)
```

---

## Common Issues and Fixes

### Issue 1: Incorrect Relative Path

**Problem:**
```markdown
<!-- File: topics/guide.md -->
![Chart](media/chart.jpg)
```

**Error:**
```
❌ Image file not found: media/chart.jpg
   💡 Suggestion: ../media/chart.jpg
```

**Fix:**
```markdown
<!-- File: topics/guide.md -->
![Chart](../media/chart.jpg)
```

**Explanation:** From `topics/` directory, need `../` to go up to KB root, then into `media/`.

---

### Issue 2: Image Outside KB

**Problem:**
```markdown
![External](../../Downloads/screenshot.png)
```

**Warning:**
```
⚠️  Image is outside KB images directory
```

**Fix:** Copy image to KB images directory:
```bash
cp ~/Downloads/screenshot.png knowledge_base/media/screenshot_20240115.png
```

Then update markdown:
```markdown
![Screenshot from 2024-01-15](../media/screenshot_20240115.png)
```

---

### Issue 3: Poor Alt Text

**Problem:**
```markdown
![image](../media/chart.jpg)
```

**Info:**
```
ℹ️  Generic alt text 'image' - consider more specific description
```

**Fix:**
```markdown
![Q4 2024 Revenue Growth Chart showing 45% increase](../media/chart.jpg)
```

---

## Agent Instructions

Agents are instructed via system prompts to:

### 1. Use Correct Relative Paths

```
From KB root:          ![alt](media/img.jpg)
From topics/:          ![alt](../media/img.jpg)
From topics/sub/:      ![alt](../../media/img.jpg)
```

See: `config/prompts/content_processing/template.ru.v2.md`

### 2. Add Meaningful Alt Text

```markdown
❌ Bad:  ![image](chart.jpg)
✅ Good: ![Revenue growth chart Q4 2024](chart.jpg)
```

### 3. Place Images Logically

- After relevant section headers
- Near text they illustrate
- Not at the very beginning (intro text first)

---

## Technical Details

### Image Detection Regex

```python
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
```

Matches:
- `![Alt text](path/to/image.jpg)` ✅
- `![](path.png)` ✅ (empty alt text)
- `![Complex [brackets]](path.jpg)` ❌ (not supported - use simpler alt text)

### Supported Image Formats

```python
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif",
    ".svg", ".webp", ".bmp", ".tiff"
}
```

### Path Resolution

For each image reference:

1. **Extract path** from markdown syntax
2. **Skip HTTP/HTTPS URLs** (external images)
3. **Resolve relative to markdown file**:
   ```python
   markdown_dir = Path("/kb/topics")
   img_path = "../media/photo.jpg"
   resolved = (markdown_dir / img_path).resolve()
   # Result: /kb/media/photo.jpg
   ```
4. **Check existence**: `resolved.exists()`
5. **Verify in KB**: Check if inside `kb_root/media/`

---

## Configuration

### Enable/Disable Validation

Validation is automatically enabled when agents use file tools. To disable:

```python
# In agent tool context
# (validation is currently always enabled for .md files)
```

### Adjust Validation Strictness

```python
# Check alt text quality
refs, issues = validator.validate_markdown_file(
    md_file,
    check_alt_text=True  # Set False to skip alt text checks
)
```

---

## Limitations

### What is NOT Validated

1. **Image content** - validator doesn't check if image displays correctly
2. **Image dimensions** - no size validation
3. **Broken HTML img tags** - only validates markdown syntax
4. **Data URIs** - base64 encoded images not checked
5. **Complex alt text** - brackets in alt text may confuse parser

### Edge Cases

**Multiple images on same line:**
```markdown
![A](img1.jpg) and ![B](img2.jpg)  <!-- Both validated ✅ -->
```

**Images in code blocks:**
```markdown
\`\`\`markdown
![Example](path.jpg)  <!-- NOT validated (inside code block) ❌ -->
\`\`\`
```
*Note: Current implementation validates ALL matches - code blocks not excluded yet.*

**Escaped brackets:**
```markdown
![Alt with \[brackets\]](path.jpg)  <!-- May not parse correctly ⚠️ -->
```

---

## Future Enhancements

### Planned Features

- [ ] Auto-fix incorrect paths
- [ ] Compress/resize large images
- [ ] Check for duplicate images (same content, different names)
- [ ] Validate image dimensions (too large/small)
- [ ] Pre-commit hook integration
- [ ] VS Code extension for real-time validation
- [ ] Image optimization suggestions

### Contributing

To add new validation rules:

1. Add check to `MarkdownMediaValidator` class
2. Create corresponding `ValidationIssue` type
3. Add tests to `tests/test_markdown_media_validator.py`
4. Update documentation

---

## Troubleshooting

### Validator Not Running

**Check 1:** File extension
```python
# Only .md files are validated
assert file_path.suffix.lower() == ".md"
```

**Check 2:** Tool execution
```python
# Validation only runs in file_create/file_edit tools
# Check logs for: "[file_create] Image validation..."
```

### False Positives

**Case-sensitive filesystems:**
```markdown
![Photo](Images/photo.jpg)  <!-- Looks for: media/photo.jpg -->
```
Fix: Use lowercase `media/` directory name.

**Symlinks:**
Validator follows symlinks via `Path.resolve()`. If symlink broken, validation fails.

---

## Examples

### Example 1: Agent Creates Valid Markdown

```python
# Agent uses file_create tool
result = await file_create_tool.execute({
    "path": "topics/api-guide.md",
    "content": """# API Guide

![Authentication flow diagram](../media/auth_flow_20240115.png)

## Overview
...
"""
})

# Validation passes:
assert result["success"] == True
assert result["validation_passed"] == True
assert "validation_warnings" not in result
```

### Example 2: Agent Creates Invalid Markdown

```python
# Agent uses wrong path
result = await file_create_tool.execute({
    "path": "topics/tutorial.md",
    "content": """# Tutorial

![Screenshot](media/screen.jpg)  # Wrong: should be ../media/
"""
})

# Validation fails but file still created:
assert result["success"] == True
assert result["validation_passed"] == False
assert "validation_warnings" in result

# Agent can see warnings and self-correct:
# (In next iteration, agent edits file with correct path)
```

### Example 3: Batch Validation

```python
from src.processor.markdown_media_validator import MarkdownMediaValidator

validator = MarkdownMediaValidator(kb_root)

# Validate all markdown files
issues_by_file = validator.validate_kb_directory(check_alt_text=True)

# Generate and save report
report = validator.generate_report(issues_by_file, verbose=True)
report_file = kb_root / "validation_report.txt"
report_file.write_text(report)

# Find unused images for cleanup
unreferenced = validator.find_unreferenced_images()
if unreferenced:
    print(f"🗑️  Found {len(unreferenced)} unreferenced images:")
    for img in unreferenced:
        print(f"  - {img.relative_to(kb_root)}")
```

---

## See Also

- [Image Embedding](../features/image-embedding.md) - How agents embed images in notes
- [Agent Tools](../agents/tools.md) - File management tools reference
- [Knowledge Base Structure](../getting-started/kb-structure.md) - KB organization guidelines
