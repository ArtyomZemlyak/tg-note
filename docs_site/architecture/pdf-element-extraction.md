# PDF Element Extraction Architecture

## Overview

This document explains how PDF element extraction (images, tables) works in tg-note.

## Current Implementation Status

⚠️ **IMPORTANT**: The current implementation supports **two methods** for extracting images and tables:

1. ✅ **From markdown (base64 embedded images)** - **IMPLEMENTED**
   - If Docling embeds images as base64 in markdown (when `keep_images=True`)
   - Extracts images and their captions (alt text) from markdown
   - Parses JSON code blocks for table data

2. ⏳ **From resource URIs** - **PARTIALLY IMPLEMENTED**
   - Assumes Docling returns resource URIs (needs verification)
   - Currently searches for resource URIs in MCP response

3. ⏳ **From document key** - **PLACEHOLDER**
   - Searches for resource export tools (needs Docling API verification)

## How It Should Work

### Step 1: PDF Processing

1. User sends PDF to bot via Telegram
2. Bot downloads PDF and encodes it as base64
3. Bot calls Docling MCP tool `convert_document_from_content` with base64 content
4. Docling processes PDF and returns:
   - `document_key` - unique identifier for the converted document
   - Optionally: `markdown` text if `export_format="markdown"` was requested

### Step 2: Element Extraction

The current implementation attempts to extract elements in two ways:

#### Method 1: From Resource URIs (Currently Implemented)

```python
# In _extract_text_from_mcp_result():
resource_uris: List[str] = []

for item in content:
    if item_type == "resource":
        uri = resource.get("uri")
        if uri:
            resource_uris.append(uri)

# Then extract from resources
if kb_images_dir and resource_uris:
    extracted_elements = await self._extract_elements_from_resources(
        client, resource_uris, kb_images_dir, source_filename
    )
```

**How `_extract_elements_from_resources()` works:**

1. For each resource URI, calls `client.read_resource(uri)`
2. Checks MIME type of each entry:
   - `image/*` → Decodes base64, saves as image file
   - `application/json` → Checks if it's table data, saves as JSON
3. Returns metadata about extracted elements

#### Method 2: From Document Key (Placeholder)

```python
# In _extract_elements_from_document():
# This is currently a placeholder
# Needs to be implemented based on Docling's actual API
```

**What needs to be done:**

- Check if Docling MCP exposes tools to list/export document resources
- Or check if markdown export includes image references that can be extracted
- Or check if there's a way to access document's internal structure

### Step 3: Markdown Export

Docling can export to markdown in two ways:

1. **Direct export** (if `export_format="markdown"` in tool call):
   ```python
   result = {
       "document_key": "...",
       "markdown": "# Document\n\n![Figure 1](data:image/png;base64,...)\n..."
   }
   ```

2. **Separate export** (via `export_docling_document_to_markdown` tool):
   ```python
   export_result = await client.call_tool(
       "export_docling_document_to_markdown", 
       {"document_key": document_key}
   )
   ```

### Step 4: Image Extraction from Markdown

**✅ IMPLEMENTED**: The code now extracts images and tables from markdown if Docling embeds them.

**How it works:**

1. **Parse markdown for embedded base64 images:**
   ```python
   # Pattern: ![alt_text](data:image/png;base64,...)
   image_pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
   
   for match in re.finditer(image_pattern, markdown_text):
       alt_text = match.group(1)  # Caption/subtitle!
       image_type = match.group(2)  # png, jpeg, etc.
       base64_data = match.group(3)
       
       # Decode and save
       image_bytes = base64.b64decode(base64_data)
       # Save to KB/images/ with caption metadata
   ```

2. **Extract table data from markdown:**
   - Parses JSON code blocks: ````json\n{table_data}\n````
   - Checks if JSON contains table structure (rows, cells)
   - Saves to `tables/` directory

**Important**: This only works if Docling's `export_to_markdown()` embeds images as base64 (requires `keep_images=True` in Docling config).

### Step 5: Table Extraction

Tables can be extracted in two ways:

1. **From JSON resources** (if Docling provides them):
   ```python
   if mime == "application/json":
       table_data = json.loads(json_data)
       if "table" in str(table_data).lower() or "rows" in table_data:
           # Save as JSON file
   ```

2. **From markdown tables:**
   - Parse markdown table syntax
   - Convert to structured JSON
   - Save to `tables/` directory

## Current Code Flow

```
User sends PDF
    ↓
download_and_process_telegram_file()
    ↓
process_file(file_path, kb_images_dir=kb_images_dir)
    ↓
_process_with_mcp(file_path, file_format, kb_images_dir)
    ↓
client.call_tool("convert_document_from_content", {...})
    ↓
_extract_text_from_mcp_result(client, result, kb_images_dir, source_filename)
    ↓
[Check for resource URIs in result]
    ↓
_extract_elements_from_resources(client, resource_uris, kb_images_dir, source_filename)
    ↓
[For each URI: read_resource(uri) → check MIME → save if image/table]
    ↓
[Return metadata with extracted_elements]
    ↓
ContentParser adds info to agent prompt
    ↓
Agent uses extracted elements in markdown
```

## What's Missing

1. **Actual Docling API investigation:**
   - Does Docling return resource URIs for images/tables?
   - Or does it embed images as base64 in markdown?
   - How are tables represented?

2. **Markdown parsing:**
   - Need to extract base64 images from markdown if that's how Docling provides them
   - Need to extract table data from markdown

3. **Document structure access:**
   - Check if Docling document object has methods to access images/tables directly
   - Check if there are MCP tools to export document resources

## Testing Needed

1. **Send a test PDF with images and tables**
2. **Check what Docling actually returns:**
   - Log the full response structure
   - Check if there are resource URIs
   - Check if markdown contains base64 images
   - Check if tables are in markdown or separate resources

3. **Implement based on actual API:**
   - If resources: current implementation should work
   - If base64 in markdown: need to parse markdown
   - If separate tools: need to call them

## Next Steps

1. ✅ Foundation code is in place
2. ⏳ Test with actual PDF to see what Docling returns
3. ⏳ Implement markdown parsing if needed
4. ⏳ Complete `_extract_elements_from_document()` based on actual API
5. ⏳ Add tests
