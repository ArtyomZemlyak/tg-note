# Image Prompt Format

How images are presented to the agent in the prompt.

---

## New format (simplified)

### Before (old, verbose)

```
User: Here are the architecture diagrams

--- Image: image.jpg (saved as: ../media/img_1234567890_abc12345_coconut_chain.jpg) ---
Description: Diagram showing three main components: Frontend (React), API (FastAPI), and Database (PostgreSQL). The frontend communicates with the API via REST endpoints. The API connects to the database using SQLAlchemy ORM. There's also a Redis cache layer between the API and database for performance optimization. The architecture follows microservices pattern with...
Full description: ../media/img_1234567890_abc12345_coconut_chain.md

--- Image: image2.jpg (saved as: ../media/img_1234567891_def67890_kubernetes.jpg) ---
Description: Deployment diagram showing Kubernetes cluster with three environments: development, staging, and production. Each environment has separate namespaces. The production namespace contains 5 replicas of the API service, 3 replicas of the worker service, and...
Full description: ../media/img_1234567891_def67890_kubernetes.md
```

**Problems:**
- Very long prompt (hundreds of chars per image)
- Duplicate descriptions (OCR + summary)
- Agent might ignore the `.md` files

### After (new, clean)

```
User: Here are the architecture diagrams

Media files:
located in media/
img_1234567890_abc12345_coconut_chain.jpg
img_1234567891_def67890_kubernetes.jpg
```

**Benefits:**
- Minimal prompt size (just filenames)
- Agent MUST read `.md` files to understand images
- No duplicates in the prompt
- Clean and simple

---

## How the agent uses images

### Step 1: See media list

Agent receives:
```
Media files:
located in media/
img_1234567890_abc12345_coconut_chain.jpg
img_1234567891_def67890_kubernetes.jpg
```

### Step 2: Read metadata files

Agent can read descriptions:

```python
# Read first image description
read_file("KB/media/img_1234567890_abc12345_coconut_chain.md")
```

Returns:
```markdown
# Image Description

**File:** img_1234567890_abc12345_coconut_chain.jpg
**Original:** system_architecture.png
**Received:** 1234567890

## Extracted Text (OCR)

Frontend (React)
↓
API Gateway
↓
Microservices:
- Auth Service
- User Service
- Payment Service
↓
PostgreSQL Database
...

## Usage Instructions

When referencing this image in markdown:
1. Use relative path based on file location
2. Add descriptive alt text based on OCR content above
3. Add text description BELOW the image for GitHub rendering

Example:
```markdown
![System architecture diagram](../media/img_1234567890_abc12345_coconut_chain.jpg)

**Description:** Diagram shows microservices architecture with...
```
```

### Step 3: Insert into markdown

Agent creates a note:

```markdown
# System Architecture - 2024-01-15

Our new architecture consists of three main layers.

![Microservices architecture with API Gateway and multiple services](../media/img_1234567890_abc12345_coconut_chain.jpg)

**Description:** The diagram illustrates a microservices architecture where:
- Frontend communicates through API Gateway
- Three core services: Auth, User, and Payment
- PostgreSQL handles persistent storage
- Redis provides caching

## Deployment Strategy

The deployment uses Kubernetes for orchestration.

![Kubernetes deployment diagram with three environments](../media/img_1234567891_def67890_kubernetes.jpg)

**Description:** Deployment structure showing:
- Separate namespaces for dev/staging/prod
- Production runs 5 API replicas
- Automatic scaling based on CPU usage
```

---

## Prompt size comparison

### Example: 3 images with OCR text

**Old format:**
```
Image 1: 500 chars description
Image 2: 450 chars description
Image 3: 600 chars description
Total: ~1550 chars
```

**New format:**
```
Media files:
located in media/
img_001.jpg
img_002.jpg
img_003.jpg
Total: ~60 chars
```

**Savings: ~96% reduction in prompt size.**

---

## Agent instructions

From `template.ru.v2.md` (now interpreted in English):

```markdown
## Image list format

If the "Incoming information" section contains "Media files:",
it means images are attached to the message:

Media files:
located in media/
img_1234567890_abc12345_coconut_chain.jpg

**What to do:**
1. For each image (e.g., `img_123_slug.jpg`) there is a description file `img_123_slug.md` in the same `media/` folder.
2. Read that file to understand the image (OCR text is there).
3. Use the images in generated markdown files.
```

---

## Implementation details

### ContentParser changes

```python
# Old approach
for file_data in file_contents:
    if "saved_filename" in file_data:
        summary = MediaMetadata.get_image_description_summary(...)
        file_texts.append(f"Description: {summary}\n...")

# New approach
image_filenames = []
for file_data in file_contents:
    if "saved_filename" in file_data:
        image_filenames.append(file_data["saved_filename"])

# Add short block if images exist
if image_filenames:
    file_texts.append("""
Media files:
stored in media/
{joined_filenames}
""")
```

### Why keep a short filename block?

The prompt includes only a minimal filename list (`Media files: stored in media/ ...`). If you change the wording, keep it concise so the agent always reads the accompanying `.md` files for details.

---

## AICODE-NOTE
- Goal: minimize prompt size and force the agent to read `.md` descriptions for images.
- Only filenames go into the prompt; full OCR/summary lives in the `.md` files.
- Works with existing media processing pipeline and markdown generation.
