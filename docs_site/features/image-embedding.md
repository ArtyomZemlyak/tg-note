# Image Embedding in Markdown

Automatic image storage and embedding in knowledge base notes.

---

## Overview

When you send images to the tg-note bot, they are:
1. **Saved permanently** to your knowledge base (`images/` folder)
2. **Processed via OCR** to extract text content
3. **Referenced by the AI agent** when creating markdown notes

This means your notes can include the actual images, not just text descriptions!

---

## How It Works

### 1. Send Image to Bot

```
You: [Send screenshot of API docs]
Bot: 🔄 Processing message...
```

### 2. Image Processing Pipeline

```
┌──────────────────┐
│  Telegram Image  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ FileProcessor                            │
│ • Generate unique name                   │
│ • Save to: KB/images/img_1705334567.jpg  │
│ • Extract text via Docling OCR          │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ ContentParser                            │
│ • Merge OCR text with message            │
│ • Include image path in prompt           │
│ • Format: "сохранено как: images/..."   │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ AI Agent (Qwen CLI)                      │
│ • Reads: text + image path info          │
│ • Creates markdown note                  │
│ • Embeds: ![description](path/to/img)   │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ Knowledge Base                           │
│ • Note saved with image reference        │
│ • Image file persisted in images/        │
└──────────────────────────────────────────┘
```

### 3. Result in Knowledge Base

**File structure:**
```
knowledge_bases/my-notes/
├── images/
│   └── img_1705334567_abc123.jpg    ← Your image
└── topics/
    └── api-docs-screenshot.md       ← Note with reference
```

**Generated markdown (`api-docs-screenshot.md`):**
```markdown
# API Documentation Screenshot - 2024-01-15

Screenshot of the authentication section from our API docs.

![API Authentication Documentation](../images/img_1705334567_abc123.jpg)

## Key Information Extracted

- OAuth2 flow diagram
- Token endpoint: `/api/v1/auth/token`
- Refresh token validity: 30 days

## Notes

The screenshot clearly shows the step-by-step authentication process...
```

---

## Agent Intelligence

The AI agent is specially instructed to:

### 1. Detect Saved Images

When processing content, the agent sees:
```
--- Содержимое файла: image.jpg (сохранено как: images/img_1705334567_abc123.jpg) ---
[OCR extracted text here]
```

### 2. Use Relative Paths Correctly

The agent knows markdown file structure:

| Note Location | Image Reference |
|--------------|-----------------|
| `KB/index.md` | `![alt](images/img_xxx.jpg)` |
| `KB/topics/note.md` | `![alt](../images/img_xxx.jpg)` |
| `KB/topics/sub/note.md` | `![alt](../../images/img_xxx.jpg)` |

### 3. Add Meaningful Descriptions

**Bad:**
```markdown
![image](images/img_123.jpg)
```

**Good:**
```markdown
![API authentication flow diagram](images/img_123.jpg)
```

**Excellent:**
```markdown
![OAuth2 authentication flow showing 3 steps: 1) Request token 2) Validate credentials 3) Return JWT](images/img_123.jpg)
```

### 4. Place Images Logically

The agent places images:
- After relevant section headers
- Near text they illustrate
- Not at the very beginning (intro text first)

---

## Filename Format

Images are saved with unique, traceable names:

### Format
```
img_{timestamp}_{file_id}{extension}
```

### Example
```
img_1705334567_abc12345.jpg
```

### Components

| Part | Source | Purpose |
|------|--------|---------|
| `img_` | Fixed prefix | Identifies as bot-saved image |
| `1705334567` | Unix timestamp | When message received |
| `abc12345` | Telegram file_id (first 8 chars) | Unique identifier |
| `.jpg` | Original extension | Preserves format |

### Benefits

1. **Chronological sorting**: Filename starts with timestamp
2. **Collision-free**: Timestamp + file_id ensures uniqueness
3. **Traceable**: Can identify when/from which message
4. **Format-preserving**: Original extension maintained

---

## Multiple Images

Send multiple images in one message or quickly in sequence:

### Example: Architecture Diagram Series

```
You: [Send 3 screenshots: diagram1.png, diagram2.png, diagram3.png]
     Caption: "System architecture diagrams"
```

**Agent creates:**
```markdown
# System Architecture Documentation - 2024-01-15

Complete architecture overview from multiple diagrams.

## Overview Diagram

![System architecture overview showing 5 main components](../images/img_1705334567_abc123.png)

## Data Flow Diagram

![Data flow between frontend, API, and database layers](../images/img_1705334580_def456.png)

## Deployment Diagram

![Kubernetes cluster deployment structure with 3 environments](../images/img_1705334592_ghi789.png)

## Analysis

The architecture follows a microservices pattern...
```

---

## OCR Text Integration

Images with text are processed via OCR:

### What Agent Receives

**From image:**
```
API_KEY=your_key_here
BASE_URL=https://api.example.com
TIMEOUT=30
```

**Agent combines:**
1. Your message text: "Here's the config file screenshot"
2. OCR extracted text: "API_KEY=..., BASE_URL=..., ..."
3. Image path: "images/img_xxx.jpg"

**Agent creates:**
```markdown
# Configuration File Screenshot

Screenshot of production configuration.

![Production config.env file](../images/img_1705334567_abc123.jpg)

## Configuration Values

From the screenshot:
```env
API_KEY=your_key_here
BASE_URL=https://api.example.com
TIMEOUT=30
```

## Notes
- Update API_KEY before deploying
- Timeout increased to 30s for large requests
```

---

## Storage Management

### Disk Space

Images accumulate over time:
- **Average screenshot**: 50-500 KB
- **1000 images**: ~200 MB
- **Monitor**: Check `images/` folder size

### Cleanup Options

#### Option 1: Manual Cleanup
```bash
# List all images sorted by date
ls -lt knowledge_bases/my-notes/images/

# Remove specific image
rm knowledge_bases/my-notes/images/img_1705334567_abc123.jpg

# Remove images older than 30 days
find knowledge_bases/my-notes/images/ -name "img_*.jpg" -mtime +30 -delete
```

#### Option 2: Exclude from Git

Add to KB `.gitignore`:
```gitignore
# Don't commit images to git
images/
```

Or keep git but track only specific formats:
```gitignore
# Exclude large images
images/*.png
images/*.tiff

# Keep small JPEGs
!images/*.jpg
```

#### Option 3: Automatic Cleanup (Future)

Future feature ideas:
- Auto-delete images not referenced in any markdown
- Compress old images automatically
- Archive to external storage

---

## Advanced Use Cases

### 1. Diagram Collections

Create diagram libraries:
```markdown
# Architecture Diagrams

## Component Diagram
![](../images/img_comp_2024.png)

## Sequence Diagram
![](../images/img_seq_2024.png)

## Deployment Diagram
![](../images/img_deploy_2024.png)
```

### 2. Meeting Whiteboards

Capture whiteboard photos:
```
You: [Photo of whiteboard with meeting notes]
     "Team brainstorming session 2024-01-15"
Bot: ✅ Saved successfully!
```

**Result:**
```markdown
# Team Brainstorming - 2024-01-15

![Whiteboard photo from team meeting](../images/img_1705334567_abc123.jpg)

## Ideas Discussed
[OCR extracted key points]
...
```

### 3. Document Scanning

Archive paper documents:
```
You: [Photo of signed contract]
     "Client agreement signed 2024-01-15"
```

### 4. Social Media Content

Save infographics, posts:
```
You: [Screenshot of competitor's product page]
     "Competitor analysis - new features"
```

---

## Best Practices

### ✅ DO

1. **Add context in captions**: Help agent understand image purpose
2. **Use good lighting**: Better OCR extraction
3. **Crop relevant parts**: Focus on important content
4. **Send related images together**: Agent can group logically

### ❌ DON'T

1. **Send personal/sensitive images**: KB may be synced to git
2. **Send extremely large images**: >5MB not optimal
3. **Send too many at once**: Bot processes sequentially
4. **Forget about storage**: Monitor disk space

### 💡 TIPS

1. **Describe image content**: "Dashboard screenshot showing metrics spike"
2. **Send in context**: Pair with explanatory text
3. **Review generated notes**: Check if image placement makes sense
4. **Use `.gitignore`**: If images shouldn't be in git

---

## Configuration

Image saving is automatic when:

```yaml
# config.yaml
MEDIA_PROCESSING_ENABLED: true
MEDIA_PROCESSING_DOCLING:
  enabled: true
  image_ocr_enabled: true
  formats:
    - jpg
    - jpeg
    - png
    - tiff
```

---

## Troubleshooting

### Images not saved?

**Check:**
1. Media processing enabled? `MEDIA_PROCESSING_ENABLED: true`
2. Image formats enabled? Check `formats` list
3. KB path accessible? Verify write permissions
4. Logs show errors? Set `LOG_LEVEL: DEBUG`

### Agent doesn't embed images?

**Check:**
1. Using qwen-cli agent? (Other agents may not have this feature yet)
2. Prompt template version: Should be v2 (`template.ru.v2.md`)
3. Content parser passing kb_path? Check service logs

### Images not displaying?

**Check:**
1. Relative path correct? `../images/` from `topics/`
2. Image file exists? Verify in `images/` folder
3. Filename matches? Check exact name in markdown

---

## Examples

### Example 1: Code Screenshot

**You send:**
```
[Screenshot of Python code]
"FastAPI async endpoint implementation"
```

**Agent creates:**
```markdown
# FastAPI Async Endpoint Implementation

![FastAPI async function showing database query pattern](../images/img_1705334567_abc123.jpg)

## Code Analysis

The screenshot shows an async endpoint using SQLAlchemy async session...

## Key Points
- Proper async/await usage
- Transaction management
- Error handling pattern
```

### Example 2: Chart/Graph

**You send:**
```
[Graph screenshot]
"Q4 2024 revenue growth"
```

**Agent creates:**
```markdown
# Q4 2024 Revenue Analysis

![Line graph showing 45% revenue increase in Q4 2024](../images/img_1705334567_abc123.jpg)

## Insights

- Strong growth: +45% compared to Q3
- Peak in December (holiday season)
- Consistent upward trend
```

### Example 3: Error Message

**You send:**
```
[Screenshot of error]
"Production error - need to investigate"
```

**Agent creates:**
```markdown
# Production Error Investigation - 2024-01-15

![Error traceback showing ConnectionTimeout in Redis client](../images/img_1705334567_abc123.jpg)

## Error Details

```
ConnectionTimeout: Could not connect to Redis at redis:6379
  at redis.client.connect()
  at app.services.cache.init()
```

## Next Steps

- Check Redis container status
- Verify network connectivity
- Review connection timeout settings
```

---

## See Also

- [File Format Recognition](file-format-recognition.md) - Full file processing documentation
- [Qwen CLI Agent](../agents/qwen-code-cli.md) - Agent configuration and prompts
- [Knowledge Base Structure](../getting-started/kb-structure.md) - KB organization
