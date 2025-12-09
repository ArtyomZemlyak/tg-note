# Image Embedding in Markdown

Automatic image storage and embedding in knowledge base notes.

---

## Overview

When you send images to the tg-note bot, they are:
1. **Saved permanently** to your knowledge base (`media/` folder)
2. **Processed via OCR** to extract text content
3. **Referenced by the AI agent** when creating markdown notes

Your notes include the actual images, not just text descriptions.

---

## How it works

### 1. Send image to bot

```
You: [Send screenshot of API docs]
Bot: 🔄 Processing message...
```

### 2. Image processing pipeline

```
┌──────────────────┐
│  Telegram Image  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ FileProcessor                            │
│ • Generate unique name                   │
│ • Save to: KB/media/img_1705334567.jpg   │
│ • Extract text via Docling OCR           │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ ContentParser                            │
│ • Merge OCR text with message            │
│ • Include image path in prompt           │
│ • Format: "saved as: media/..."          │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ AI Agent (Qwen CLI)                      │
│ • Reads: text + image path info          │
│ • Creates markdown note                  │
│ • Embeds: ![description](path/to/img)    │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│ Knowledge Base                           │
│ • Note saved with image reference        │
│ • Image file persisted in media/         │
└──────────────────────────────────────────┘
```

### 3. Result in knowledge base

**File structure:**
```
knowledge_bases/my-notes/
├── media/
│   └── img_1705334567_abc123.jpg    ← your image
└── topics/
    └── api-docs-screenshot.md       ← note with reference
```

**Generated markdown (`api-docs-screenshot.md`):**
```markdown
# API Documentation Screenshot - 2024-01-15

Screenshot of the authentication section from our API docs.

![API Authentication Documentation](../media/img_1705334567_abc123.jpg)

## Key Information Extracted

- OAuth2 flow diagram
- Token endpoint: `/api/v1/auth/token`
- Refresh token validity: 30 days

## Notes

The screenshot clearly shows the step-by-step authentication process...
```

---

## Agent intelligence

The AI agent is instructed to:

### 1. Detect saved images

When processing content, the agent sees:
```
--- File content: image.jpg (saved as: media/img_1705334567_abc123_error_traceback.jpg) ---
[OCR extracted text here]
```

### 2. Use relative paths correctly

| Note location            | Image reference                         |
|--------------------------|-----------------------------------------|
| `KB/index.md`            | `![alt](media/img_xxx_slug.jpg)`        |
| `KB/topics/note.md`      | `![alt](../media/img_xxx_slug.jpg)`     |
| `KB/topics/sub/note.md`  | `![alt](../../media/img_xxx_slug.jpg)`  |

### 3. Add meaningful descriptions

**Bad:**
```markdown
![image](media/img_123_example.jpg)
```

**Good:**
```markdown
![API authentication flow diagram](media/img_123_example.jpg)
```

**Excellent:**
```markdown
![OAuth2 authentication flow showing 3 steps: 1) Request token 2) Validate credentials 3) Return JWT](media/img_123_example.jpg)
```

### 4. Place images logically

- After relevant section headers
- Near the text they illustrate
- Not at the very beginning (intro text first)

---

## Filename format

Images are saved with unique, traceable names.

### Format
```
img_{timestamp}_{stable-id}_{ocr-slug}{extension}
```

### Example
```
img_1705334567_agacagia_error_traceback.jpg
```

### Components

| Part               | Source                               | Purpose                      |
|--------------------|--------------------------------------|------------------------------|
| `img_`             | Fixed prefix                         | Identifies bot-saved image   |
| `1705334567`       | Unix timestamp                       | When message received        |
| `agacagia`         | Telegram `file_unique_id` (sanitized)| Stable identifier            |
| `error_traceback`  | OCR-derived slug (first keywords)    | Human-readable context       |
| `.jpg`             | Original extension                   | Preserves format             |

### Benefits
1. **Chronological sorting**: filename starts with timestamp
2. **Collision-free**: timestamp + file_id ensures uniqueness
3. **Traceable**: you can identify when/from which message
4. **Format-preserving**: original extension kept

---

## Multiple images

Send multiple images in one message or quickly in sequence.

### Example: architecture diagram series

```
You: [Send 3 screenshots: diagram1.png, diagram2.png, diagram3.png]
     Caption: "System architecture diagrams"
```

**Agent creates:**
```markdown
# System Architecture Documentation - 2024-01-15

Complete architecture overview from multiple diagrams.

## Overview Diagram

![System architecture overview showing 5 main components](../media/img_1705334567_abc123.png)

## Data Flow Diagram

![Data flow with API Gateway, services, and DB](../media/img_1705334570_def456.png)

## Deployment Diagram

![Kubernetes deployment with dev/stage/prod namespaces](../media/img_1705334572_ghi789.png)
```

---

## FAQ

### Do images bloat the repo?

Images are stored under `media/`. For large volumes, consider Git LFS or periodic cleanup/archival. The bot does not downscale images automatically.

### How are captions chosen?

Captions are derived from OCR + message context. Improve quality by adding a brief caption in Telegram when sending the image.

### What about PDFs or DOCX with images?

Docling extracts text and embeds references for attached media where applicable.

### Can I disable image embedding?

Not yet; current flow always stores images. You can manually remove media files and references if needed.

---

## AICODE-NOTE
- Images are saved with unique, timestamped filenames and OCR-derived slugs.
- Metadata lives alongside images (see Media Metadata System).
- Agents embed images with meaningful alt text and proper relative paths.
