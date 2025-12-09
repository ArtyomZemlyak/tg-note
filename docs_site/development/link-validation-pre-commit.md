# Link Validation Before Git Commit

Automatic validation and fixing of links in markdown files before each git commit.

---

## Overview

Before every git commit the system automatically:
1. **Validates** image paths and internal markdown links
2. **Fixes** incorrect paths (computes correct `../` prefixes)
3. **Adds** `<!-- TODO -->` comments when auto-fix is impossible

This prevents broken links from landing in the knowledge base.

---

## What is validated

### 1. Image paths

```markdown
![Chart](media/chart.jpg)  <!-- ❌ wrong when used from topics/ -->
```

**Auto-fix →**

```markdown
![Chart](../media/chart.jpg)  <!-- ✅ fixed -->
```

### 2. Internal page links

```markdown
[Page 1](page1.md)  <!-- ❌ file is in another folder -->
```

**Auto-fix →**

```markdown
[Page 1](topics/page1.md)  <!-- ✅ fixed -->
```

### 3. TODO comments when unresolved

```markdown
![Missing](media/missing.jpg) <!-- TODO: Broken image path -->
[Link](nonexistent.md) <!-- TODO: Broken link -->
```

---

## How it works

### Automatically on commit

```
Agent creates/edits markdown
       ↓
Changes staged in git
       ↓
_auto_commit_and_push() is called
       ↓
📋 Link validation and auto-fix  ← HERE
       ↓
Git commit
       ↓
Git push
```

### Integration code

```python
# base_kb_service.py - line ~213
async def _auto_commit_and_push(...):
    # BEFORE commit:
    validation_result = await self._validate_and_fix_markdown_links(kb_path)

    if validation_result.has_changes():
        logger.info(f"Fixed {validation_result.images_fixed} images")

    # THEN commit
    git_ops.auto_commit_and_push(...)
```

---

## Auto-fix strategies

### 1. Calculating `../` levels

```python
# File: KB/topics/subfolder/note.md
# Image: KB/media/chart.jpg

# Need to go up 2 levels:
../../media/chart.jpg
```

The fixer computes the correct number of `../` segments automatically.

### 2. Search file by name

If the path is wrong but the file exists:

```markdown
<!-- Current path -->
![Chart](wrong/path/chart.jpg)

<!-- Fixer finds the file -->
KB/media/chart.jpg exists!

<!-- Computes correct path -->
![Chart](../media/chart.jpg)
```

### 3. TODO when not found

File does not exist → add TODO:

```markdown
![Chart](media/missing.jpg) <!-- TODO: Broken image path -->
```

---

## What is NOT validated

❌ HTTP/HTTPS URLs (external)  
❌ Anchors (#section) in the same page  
❌ `mailto:` links  
❌ Image content  
❌ Image sizes  

---

## Logging

### Successful fix

```
[INFO] Validating and fixing links in 3 changed markdown files...
[DEBUG] Fixed image: media/chart.jpg → ../media/chart.jpg
[INFO] ✓ Fixed links: Files fixed: 2, Images fixed: 3, Links fixed: 1
```

### Could not fix

```
[WARNING] Can't fix link: missing.md in note.md
[WARNING] ⚠️ Some links could not be fixed automatically.
           TODO comments added: 1 images, 2 links
```

### Telegram UX

User sees:

```
📤 Saving changes to git...
⚠️ Some links need manual fixing
```

---

## Performance

### Optimization: only changed files

```python
# Do NOT scan every markdown file in the KB
# Only check files reported by git status

changed_files = git_ops.repo.index.diff(None)  # Modified
+ git_ops.repo.untracked_files  # New files
```

**Result:** fast validation even for large KBs (1000+ files).

---

## Testing

### Run tests

```bash
# Markdown link validator tests
python3 -m pytest tests/test_markdown_link_fixer.py -v

# All 11 tests should pass:
# ✓ fix_incorrect_image_path
# ✓ fix_missing_image_add_todo
# ✓ fix_markdown_link_path
# ✓ fix_markdown_link_from_root_to_topics
# ✓ skip_http_urls
# ✓ multiple_fixes_in_one_file
# ✓ preserve_anchor_in_links
# ✓ dry_run_mode
# ✓ validate_kb_with_changed_files
# ✓ case_insensitive_extension
```

### Add new tests

1. Add cases to `tests/test_markdown_link_fixer.py`
2. Cover edge cases: nested folders, anchors, mixed images+links

---

## Edge cases and notes

- Relative paths are computed against the markdown file location.
- If multiple files have the same name, the fixer chooses the closest path (shortest `../`).
- If a file is missing, we add TODO instead of failing the commit.
- External URLs are ignored deliberately.
- Anchors within the same page are ignored; cross-page anchors are treated as links to the page only.

---

## Implementation references

- `src/knowledge_base/markdown_link_fixer.py`
- `tests/test_markdown_link_fixer.py`

---

## AICODE-NOTE
- Purpose: keep KB links healthy before commit.
- Auto-fix when possible; otherwise leave a clear TODO.
- Scope-limited to changed files to remain fast.
