"""
File Format Processor
Handles various file formats using Docling via MCP or local converter.
"""

import base64
import hashlib
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from config.settings import DoclingSettings, settings
from src.mcp.client import MCPClient
from src.mcp.docling_integration import ensure_docling_mcp_spec
from src.mcp.registry.registry import MCPServerSpec
from src.mcp.registry_client import MCPRegistryClient
from src.processor.image_path_validator import validate_image_path


class FileProcessor:
    """Process various file formats and extract content using Docling."""

    DOCLING_TOOL_CANDIDATES: Tuple[str, ...] = (
        "convert_document_from_content",
        "convert_document",
        "process_document",
        "process_file",
        "docling_process",
    )

    def __init__(self) -> None:
        """Initialize file processor."""
        self.logger = logger
        self.settings = settings

        # MCP-related attributes
        self._registry_client: Optional[MCPRegistryClient] = None
        self._docling_server_spec: Optional[MCPServerSpec] = None
        self._docling_client: Optional[MCPClient] = None
        self._docling_tool_schema: Optional[Dict[str, Any]] = None
        self._docling_tool_name: Optional[str] = None

        # Local converter (fallback/backend option)
        self.converter = None

        if self.docling_config.use_mcp():
            self._setup_docling_mcp()
        elif self.docling_config.use_local():
            self._setup_docling_local()

    @property
    def docling_config(self) -> DoclingSettings:
        """Return the current Docling configuration."""
        return self.settings.MEDIA_PROCESSING_DOCLING

    def _setup_docling_mcp(self) -> None:
        """Prepare Docling MCP integration."""
        try:
            ensure_docling_mcp_spec(self.docling_config)
        except Exception as e:
            self.logger.debug(f"[FileProcessor] Unable to ensure Docling MCP spec: {e}")

        try:
            self._registry_client = MCPRegistryClient()
            self._registry_client.initialize()
            manager = self._registry_client.manager
            self._docling_server_spec = manager.get_server(self.docling_config.mcp.server_name)
            if not self._docling_server_spec:
                self.logger.warning(
                    "[FileProcessor] Docling MCP server '%s' not found in registry",
                    self.docling_config.mcp.server_name,
                )
        except Exception as e:
            self.logger.error(f"[FileProcessor] Failed to initialize MCP registry client: {e}")
            self._registry_client = None
            self._docling_server_spec = None

    def _setup_docling_local(self) -> None:
        """Prepare local Docling DocumentConverter fallback."""
        try:
            from docling.document_converter import DocumentConverter  # type: ignore
        except ImportError:
            self.logger.warning(
                "[FileProcessor] Docling Python package not available; local backend disabled."
            )
            return

        try:
            self.converter = DocumentConverter()
            self.logger.info("Docling DocumentConverter initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize DocumentConverter: {e}")
            self.converter = None

    def is_available(self) -> bool:
        """
        Check if Docling processing is available and enabled.
        """
        if not self.settings.is_media_processing_enabled():
            return False
        if not self.docling_config.enabled:
            return False

        if self.docling_config.use_mcp():
            return self._docling_server_spec is not None

        if self.docling_config.use_local():
            return self.converter is not None

        return False

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats based on configuration.
        """
        if not self.is_available():
            return []
        return self.docling_config.get_enabled_formats()

    def detect_file_format(self, file_path: Path) -> Optional[str]:
        """
        Detect file format from extension and check if it's enabled in settings.
        """
        extension = file_path.suffix.lower().lstrip(".")
        if self.settings.is_format_enabled(extension, "docling"):
            return extension
        self.logger.debug("Docling format disabled in settings: %s", extension)
        return None

    async def _get_docling_client(self) -> Optional[MCPClient]:
        """Ensure MCP client for Docling is connected."""
        if not self._registry_client or not self._docling_server_spec:
            return None

        if self._docling_client and self._docling_client.is_connected:
            return self._docling_client

        client = await self._registry_client.connect_to_server(self._docling_server_spec)
        if client:
            self._docling_client = client
        return client

    async def _ensure_docling_tool_schema(self, client: MCPClient) -> bool:
        """Ensure Docling MCP tool schema is loaded and selected."""
        if self._docling_tool_schema and self._docling_tool_name:
            return True

        try:
            tools = await client.list_tools()
        except Exception as e:
            self.logger.error(f"[FileProcessor] Failed to list tools from Docling MCP: {e}")
            return False

        if not tools:
            self.logger.warning("[FileProcessor] Docling MCP server returned no tools.")
            return False

        selected = self._pick_docling_tool(tools)
        if not selected:
            self.logger.warning("[FileProcessor] Docling MCP tool could not be determined.")
            return False

        self._docling_tool_schema = selected
        self._docling_tool_name = selected.get("name")
        return True

    def _pick_docling_tool(self, tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select Docling tool from list based on configuration and heuristics."""
        if not tools:
            return None

        preferred = (self.docling_config.mcp.tool_name or "").strip().lower()

        if preferred:
            for tool in tools:
                if tool.get("name", "").lower() == preferred:
                    return tool

        if self.docling_config.mcp.auto_detect_tool:
            for candidate in self.DOCLING_TOOL_CANDIDATES:
                for tool in tools:
                    if candidate in tool.get("name", "").lower():
                        return tool
            for tool in tools:
                if "docling" in tool.get("name", "").lower():
                    return tool

        return tools[0]

    async def _process_with_mcp(
        self, file_path: Path, file_format: str
    ) -> Optional[Dict[str, Any]]:
        """Process file using Docling MCP server."""
        client = await self._get_docling_client()
        if not client:
            self.logger.warning("[FileProcessor] Docling MCP client unavailable.")
            return None

        if not await self._ensure_docling_tool_schema(client):
            return None

        arguments = self._build_mcp_arguments(self._docling_tool_schema, file_path, file_format)
        if arguments is None:
            self.logger.warning(
                "[FileProcessor] Unable to build arguments for Docling MCP tool '%s'",
                self._docling_tool_name,
            )
            return None

        self.logger.info(
            "Processing file via Docling MCP: %s (format: %s, tool: %s)",
            file_path.name,
            file_format,
            self._docling_tool_name,
        )

        result = await client.call_tool(self._docling_tool_name, arguments)
        if not result.get("success"):
            self.logger.error(
                "Docling MCP tool call failed (%s): %s",
                self._docling_tool_name,
                result.get("error"),
            )
            return None

        text_content, metadata = await self._extract_text_from_mcp_result(client, result)
        if text_content is None:
            text_content = ""

        metadata.setdefault("docling", {})
        metadata["docling"].update(
            {
                "backend": "mcp",
                "tool": self._docling_tool_name,
                "server": self.docling_config.mcp.server_name,
                "prefer_markdown_output": self.docling_config.prefer_markdown_output,
                "fallback_plain_text": self.docling_config.fallback_plain_text,
                "image_ocr_enabled": self.docling_config.image_ocr_enabled,
                "max_file_size_mb": self.docling_config.max_file_size_mb,
                "ocr_languages": list(self.docling_config.ocr_languages),
            }
        )

        return {
            "text": text_content,
            "metadata": metadata,
            "format": file_format,
            "file_name": file_path.name,
        }

    async def sync_docling_models(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """Trigger Docling container model synchronisation via MCP tool."""
        client = await self._get_docling_client()
        if not client:
            self.logger.warning("[FileProcessor] Docling MCP client unavailable for sync.")
            return None

        tool_name = "sync_docling_models"

        try:
            available_tools = await client.list_tools()
        except Exception as exc:
            self.logger.error("[FileProcessor] Failed to list Docling MCP tools: %s", exc)
            return None

        if not any(tool.get("name") == tool_name for tool in available_tools):
            self.logger.warning(
                "[FileProcessor] Docling MCP server does not expose '%s' tool.", tool_name
            )
            return None

        try:
            response = await client.call_tool(tool_name, {"force": force})
            if not response.get("success", True):
                self.logger.error(
                    "[FileProcessor] Docling model sync reported failure: %s", response
                )
            else:
                self.logger.info("[FileProcessor] Docling model sync completed (force=%s).", force)
            return response
        except Exception as exc:
            self.logger.error("[FileProcessor] Docling model sync failed: %s", exc)
            return None

    def _build_mcp_arguments(
        self, tool_schema: Dict[str, Any], file_path: Path, file_format: str
    ) -> Optional[Dict[str, Any]]:
        """Build arguments for Docling MCP tool based on schema and heuristics."""
        input_schema = tool_schema.get("inputSchema", {}) or {}
        properties: Dict[str, Dict[str, Any]] = input_schema.get("properties", {}) or {}
        required: List[str] = input_schema.get("required", []) or []

        arguments: Dict[str, Any] = {}
        normalized = {name: name.lower() for name in properties}
        used: Set[str] = set()

        file_bytes = file_path.read_bytes()
        base64_content = base64.b64encode(file_bytes).decode("utf-8")
        file_uri = file_path.as_uri()
        mime_type = self._guess_mime_type(file_path, file_format)

        # Apply explicit argument hints first
        semantic_values: Dict[str, Any] = {
            "content": base64_content,
            "file_content": base64_content,
            "bytes": base64_content,
            "path": str(file_path),
            "file_path": str(file_path),
            "source": str(file_path),
            "source_path": str(file_path),
            "source_file": str(file_path),
            "uri": file_uri,
            "url": file_uri,
            "source_uri": file_uri,
            "source_url": file_uri,
            "filename": file_path.name,
            "file_name": file_path.name,
            "name": file_path.name,
            "format": file_format,
            "extension": file_format,
            "mime": mime_type,
            "mime_type": mime_type,
            "ocr": self.docling_config.image_ocr_enabled,
            "languages": list(self.docling_config.ocr_languages),
            "language": list(self.docling_config.ocr_languages),
            "markdown": self.docling_config.prefer_markdown_output,
            "fallback": self.docling_config.fallback_plain_text,
            "max_size": self.docling_config.max_file_size_mb,
            "export_format": "markdown" if self.docling_config.prefer_markdown_output else None,
        }

        hints = self.docling_config.mcp.argument_hints or {}
        for placeholder, field_name in hints.items():
            value = semantic_values.get(placeholder)
            if value is None:
                continue
            if field_name in properties and field_name not in arguments:
                arguments[field_name] = value
                used.add(field_name)

        # Heuristic assignment based on property names
        for prop, lower_name in normalized.items():
            if prop in used:
                continue

            if any(keyword in lower_name for keyword in ("content", "data", "bytes", "payload")):
                arguments[prop] = base64_content
                used.add(prop)
            elif "source" in lower_name:
                if "uri" in lower_name or "url" in lower_name:
                    arguments[prop] = file_uri
                elif any(
                    keyword in lower_name for keyword in ("content", "data", "bytes", "payload")
                ):
                    arguments[prop] = base64_content
                else:
                    arguments[prop] = str(file_path)
                used.add(prop)
            elif "path" in lower_name and "http" not in lower_name:
                arguments[prop] = str(file_path)
                used.add(prop)
            elif lower_name in {"uri", "url"} or "uri" in lower_name or "url" in lower_name:
                arguments[prop] = file_uri
                used.add(prop)
            elif "filename" in lower_name or "file_name" in lower_name:
                arguments[prop] = file_path.name
                used.add(prop)
            elif "export" in lower_name and "format" in lower_name:
                # AICODE-NOTE: Request markdown export directly from convert_document_from_content
                # This must be checked BEFORE general "format" check to avoid conflicts
                arguments[prop] = "markdown" if self.docling_config.prefer_markdown_output else None
                used.add(prop)
            elif "format" in lower_name or "extension" in lower_name:
                # AICODE-NOTE: General format/extension field (but NOT export_format)
                arguments[prop] = file_format
                used.add(prop)
            elif "mime" in lower_name:
                arguments[prop] = mime_type
                used.add(prop)
            elif "ocr" in lower_name:
                arguments[prop] = self.docling_config.image_ocr_enabled
                used.add(prop)
            elif "language" in lower_name or lower_name.endswith("langs"):
                arguments[prop] = list(self.docling_config.ocr_languages)
                used.add(prop)
            elif "markdown" in lower_name:
                arguments[prop] = self.docling_config.prefer_markdown_output
                used.add(prop)
            elif "fallback" in lower_name or "plaintext" in lower_name:
                arguments[prop] = self.docling_config.fallback_plain_text
                used.add(prop)
            elif "max" in lower_name and "size" in lower_name:
                arguments[prop] = self.docling_config.max_file_size_mb
                used.add(prop)
            elif lower_name == "name" and prop not in arguments:
                arguments[prop] = file_path.name
                used.add(prop)

        # Merge extra arguments from configuration
        for key, value in (self.docling_config.mcp.extra_arguments or {}).items():
            if key in properties and key not in arguments:
                arguments[key] = value

        # Validate required fields
        missing = [field for field in required if field not in arguments]
        if missing:
            self.logger.error(
                "[FileProcessor] Missing required Docling MCP arguments: %s", ", ".join(missing)
            )
            return None

        return arguments

    async def _extract_text_from_mcp_result(
        self, client: MCPClient, call_result: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract textual content and metadata from Docling MCP tool result."""
        raw_result = call_result.get("result") or {}
        content = call_result.get("content") or raw_result.get("content") or []
        structured_content = call_result.get("structured_content") or raw_result.get(
            "structuredContent"
        )

        # AICODE-NOTE: Check if result contains document_key (from convert_document_from_content)
        # First check if markdown is already included in the response (export_format was used)
        document_key = None
        markdown_text = None

        if structured_content and isinstance(structured_content, dict):
            document_key = structured_content.get("document_key")
            # Check if markdown was already exported
            markdown_text = structured_content.get("markdown")

            if markdown_text:
                self.logger.info(
                    f"Document already exported to markdown (length: {len(markdown_text)} chars)"
                )
                metadata = {
                    "docling_mcp": {
                        "tool": self._docling_tool_name,
                        "server": self.docling_config.mcp.server_name,
                        "transport": self.docling_config.mcp.transport,
                        "document_key": document_key,
                        "from_cache": structured_content.get("from_cache", False),
                        "export_format": structured_content.get("export_format", "markdown"),
                    }
                }
                return markdown_text, metadata

        # If no markdown in response but we have document_key, export it separately
        if document_key and not markdown_text:
            self.logger.info(
                f"Document converted with key: {document_key}, exporting to markdown..."
            )
            export_result = await client.call_tool(
                "export_docling_document_to_markdown", {"document_key": document_key}
            )

            if export_result.get("success"):
                export_content = export_result.get("content") or []
                export_structured = export_result.get("structured_content") or {}

                markdown_text = None
                # Try to get markdown from structured_content first
                if isinstance(export_structured, dict):
                    markdown_text = export_structured.get("markdown")

                # If not found, try to extract from content
                if not markdown_text:
                    for item in export_content:
                        if isinstance(item, dict):
                            item_type = item.get("type")
                            if item_type in ("text", "markdown"):
                                markdown_text = item.get("text") or item.get("markdown")
                                break
                        else:
                            item_type = getattr(item, "type", None)
                            if item_type in ("text", "markdown"):
                                markdown_text = getattr(item, "text", None) or getattr(
                                    item, "markdown", None
                                )
                                break

                if markdown_text:
                    metadata = {
                        "docling_mcp": {
                            "tool": self._docling_tool_name,
                            "server": self.docling_config.mcp.server_name,
                            "transport": self.docling_config.mcp.transport,
                            "document_key": document_key,
                            "from_cache": structured_content.get("from_cache", False),
                        }
                    }
                    return markdown_text, metadata
                else:
                    self.logger.warning(
                        f"Failed to extract markdown from export result for document_key: {document_key}"
                    )
            else:
                self.logger.error(
                    f"Failed to export document to markdown: {export_result.get('error')}"
                )

        text_fragments: List[str] = []
        resource_uris: List[str] = []
        json_payloads: List[Dict[str, Any]] = []

        for item in content:
            # AICODE-NOTE: Handle both dict and object formats (TextContent, etc.)
            if isinstance(item, dict):
                item_type = item.get("type")
            else:
                item_type = getattr(item, "type", None)

            if item_type == "text":
                text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
                if text:
                    text_fragments.append(text)
            elif item_type == "markdown":
                if isinstance(item, dict):
                    text = item.get("text") or item.get("markdown")
                else:
                    text = getattr(item, "text", None) or getattr(item, "markdown", None)
                if text:
                    text_fragments.append(text)
            elif item_type == "html":
                if isinstance(item, dict):
                    text = item.get("text") or item.get("html")
                else:
                    text = getattr(item, "text", None) or getattr(item, "html", None)
                if text:
                    text_fragments.append(text)
            elif item_type == "json":
                if isinstance(item, dict):
                    payload = item.get("json")
                else:
                    payload = getattr(item, "json", None)
                if isinstance(payload, dict):
                    json_payloads.append(payload)
                    for key in ("text", "markdown", "content"):
                        value = payload.get(key)
                        if isinstance(value, str) and value.strip():
                            text_fragments.append(value)
                            break
            elif item_type == "resource":
                if isinstance(item, dict):
                    resource = item.get("resource") or {}
                    uri = resource.get("uri")
                else:
                    resource = getattr(item, "resource", None)
                    uri = getattr(resource, "uri", None) if resource else None
                if uri:
                    resource_uris.append(uri)

        metadata: Dict[str, Any] = {}
        metadata["docling_mcp"] = {
            "tool": self._docling_tool_name,
            "server": self.docling_config.mcp.server_name,
            "transport": self.docling_config.mcp.transport,
        }
        if raw_result.get("metadata"):
            metadata["docling_metadata"] = raw_result.get("metadata")
        if json_payloads:
            metadata["docling_json"] = json_payloads

        if not text_fragments and resource_uris:
            fetched_text, resource_info = await self._fetch_resources_text(client, resource_uris)
            if fetched_text:
                text_fragments.append(fetched_text)
            if resource_info:
                metadata["docling_resources"] = resource_info

        combined_text = "\n\n".join(part.strip() for part in text_fragments if part).strip()
        return combined_text or None, metadata

    async def _fetch_resources_text(
        self, client: MCPClient, uris: List[str]
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """Fetch resource contents referenced by Docling MCP result."""
        collected_text: List[str] = []
        resources_info: List[Dict[str, Any]] = []

        for uri in uris:
            try:
                resource = await client.read_resource(uri)
            except Exception as e:
                self.logger.warning("[FileProcessor] Failed to fetch resource %s: %s", uri, e)
                continue

            if not resource:
                continue

            info: Dict[str, Any] = {"uri": uri}

            contents = resource.get("contents") or []
            content_types: List[str] = []

            for entry in contents:
                if not isinstance(entry, dict):
                    continue
                mime = entry.get("mimeType") or entry.get("mediaType")
                if mime:
                    content_types.append(mime)

                text_value = entry.get("text") or entry.get("markdown") or entry.get("content")
                if isinstance(text_value, str) and text_value.strip():
                    collected_text.append(text_value)
                    continue

                base64_value = entry.get("data") or entry.get("base64")
                if base64_value:
                    decoded = self._decode_base64_text(base64_value, mime)
                    if decoded:
                        collected_text.append(decoded)

            if content_types:
                info["content_types"] = content_types
            resources_info.append(info)

        joined_text = "\n\n".join(text.strip() for text in collected_text if text).strip()
        return (joined_text or None, resources_info)

    def _decode_base64_text(self, data: str, mime_type: Optional[str]) -> Optional[str]:
        """Decode base64 text payload if mime type indicates textual content."""
        if not data:
            return None
        try:
            decoded_bytes = base64.b64decode(data)
        except Exception:
            return None

        if mime_type and not mime_type.startswith("text/") and mime_type != "application/json":
            return None

        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return decoded_bytes.decode(encoding)
            except Exception:
                continue
        return None

    def _guess_mime_type(self, file_path: Path, file_format: str) -> Optional[str]:
        """Guess MIME type based on file format."""
        import mimetypes

        mime, _ = mimetypes.guess_type(file_path.name)
        if mime:
            return mime
        if file_format:
            return f"application/{file_format}"
        return None

    def _extract_document_text(self, document: Any, config: DoclingSettings) -> str:
        """
        Export document content using configured preference with graceful fallback.
        (Used for local Docling backend.)
        """
        if document is None:
            return ""

        export_order: List[Tuple[str, Any]] = []
        seen: Set[str] = set()

        def add_export(name: str, attribute: str) -> None:
            if name in seen:
                return
            if hasattr(document, attribute):
                method = getattr(document, attribute)
                if callable(method):
                    export_order.append((name, method))
                    seen.add(name)

        if config.prefer_markdown_output:
            add_export("markdown", "export_to_markdown")
        else:
            add_export("text", "export_to_text")

        add_export("text", "export_to_text")
        add_export("markdown", "export_to_markdown")

        if config.fallback_plain_text:
            add_export("text", "export_to_text")
            add_export("markdown", "export_to_markdown")

        for name, exporter in export_order:
            try:
                content = exporter()
                if content:
                    if name != "markdown" and config.prefer_markdown_output:
                        self.logger.debug(
                            "Docling used %s export due to fallback configuration", name
                        )
                    return content
            except Exception as export_error:
                self.logger.debug(
                    "Docling export via %s failed: %s", name, export_error, exc_info=True
                )

        return ""

    async def _process_with_local(
        self, file_path: Path, file_format: str
    ) -> Optional[Dict[str, Any]]:
        """Process file using local Docling converter."""
        if not self.converter:
            self.logger.warning("Local Docling converter unavailable.")
            return None

        file_stats = file_path.stat()
        docling_config = self.docling_config

        try:
            self.logger.info(
                "Processing file with local Docling: %s (format: %s)", file_path.name, file_format
            )

            result = self.converter.convert(str(file_path))
            document = getattr(result, "document", None)
            text_content = self._extract_document_text(document, docling_config)

            metadata: Dict[str, Any] = {
                "file_name": file_path.name,
                "file_format": file_format,
                "file_size": file_stats.st_size,
                "docling": {
                    "backend": "local",
                    "prefer_markdown_output": docling_config.prefer_markdown_output,
                    "fallback_plain_text": docling_config.fallback_plain_text,
                    "image_ocr_enabled": docling_config.image_ocr_enabled,
                    "max_file_size_mb": docling_config.max_file_size_mb,
                    "ocr_languages": list(docling_config.ocr_languages),
                },
            }

            if document:
                if hasattr(document, "name") and document.name:
                    metadata["document_title"] = document.name
                if hasattr(document, "origin") and document.origin:
                    metadata["document_origin"] = str(document.origin)

            return {
                "text": text_content,
                "metadata": metadata,
                "format": file_format,
                "file_name": file_path.name,
            }
        except Exception as e:
            self.logger.error(
                f"Error processing file {file_path.name} with local Docling: {e}", exc_info=True
            )
            return None

    async def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Process file and extract content using Docling (MCP or local).
        """
        docling_config = self.docling_config

        if not self.settings.is_media_processing_enabled():
            self.logger.info("Media processing is disabled in settings")
            return None

        if not docling_config.enabled:
            self.logger.info("Docling processing disabled in settings")
            return None

        if not self.is_available():
            self.logger.warning("Docling backend not available, cannot process file")
            return None

        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return None

        raw_extension = file_path.suffix.lower().lstrip(".")

        # AICODE-NOTE: Image path validation is handled in download_and_process_telegram_file
        # before the file is saved, so we don't need to validate again here
        file_format = self.detect_file_format(file_path)

        if not file_format:
            normalized_formats = docling_config.normalized_formats()
            if raw_extension and raw_extension in normalized_formats:
                self.logger.info(
                    "Docling format %s is disabled in configuration; skipping file %s",
                    raw_extension,
                    file_path.name,
                )
            else:
                self.logger.warning(f"Unsupported file format: {file_path.suffix}")
            return None

        if not docling_config.is_format_enabled(file_format):
            self.logger.info(
                "Docling configuration currently skips format %s; file %s will not be processed",
                file_format,
                file_path.name,
            )
            return None

        file_stats = file_path.stat()
        if docling_config.exceeds_size_limit(file_stats.st_size):
            self.logger.warning(
                "Skipping file %s (%s bytes) because it exceeds Docling limit of %s MB",
                file_path.name,
                file_stats.st_size,
                docling_config.max_file_size_mb,
            )
            return None

        if docling_config.use_mcp():
            return await self._process_with_mcp(file_path, file_format)
        if docling_config.use_local():
            return await self._process_with_local(file_path, file_format)

        self.logger.warning("No Docling backend configured for processing.")
        return None

    def _compute_file_hash(self, file_content: bytes) -> str:
        """
        Compute SHA256 hash of file content.

        Args:
            file_content: File content as bytes

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(file_content).hexdigest()

    def _find_existing_image_by_hash(
        self, file_hash: str, images_dir: Path, extension: str
    ) -> Optional[Path]:
        """
        Find existing image with same hash in images directory.

        Args:
            file_hash: SHA256 hash of the file
            images_dir: Directory containing images
            extension: File extension (e.g., '.jpg')

        Returns:
            Path to existing file if found, None otherwise
        """
        # AICODE-NOTE: Check all images with the same extension
        pattern = f"img_*{extension}"
        for existing_file in images_dir.glob(pattern):
            if existing_file.is_file():
                try:
                    with open(existing_file, "rb") as f:
                        existing_hash = self._compute_file_hash(f.read())
                    if existing_hash == file_hash:
                        self.logger.info(
                            f"Found duplicate image: {existing_file.name} (hash: {file_hash[:8]}...)"
                        )
                        return existing_file
                except Exception as e:
                    self.logger.warning(f"Error checking file {existing_file}: {e}")
                    continue
        return None

    def _save_image_description_md(self, image_path: Path, markdown_content: str) -> Optional[Path]:
        """
        Save clean markdown description of image to .md file.

        Args:
            image_path: Path to saved image file
            markdown_content: Clean markdown content from Docling OCR

        Returns:
            Path to saved .md file or None if failed
        """
        try:
            # Create .md filename (same as image but with .md extension)
            md_path = image_path.with_suffix(".md")

            # Write clean markdown content (no extra headers or structure)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            self.logger.info(f"Saved image description to: {md_path}")
            return md_path

        except Exception as e:
            self.logger.error(f"Failed to save image description .md: {e}", exc_info=True)
            return None

    def _save_image_metadata_json(
        self,
        image_path: Path,
        metadata: Dict[str, Any],
        original_filename: str,
        file_id: Optional[str],
        message_date: Optional[int],
    ) -> Optional[Path]:
        """
        Save image metadata to JSON file alongside the image description.

        Args:
            image_path: Path to saved image file
            metadata: Metadata from Docling processing
            original_filename: Original filename from Telegram
            file_id: Telegram file_id
            message_date: Message timestamp

        Returns:
            Path to saved JSON file or None if failed
        """
        import json

        try:
            # Create JSON filename (same as image but with .json extension)
            json_path = image_path.with_suffix(".json")

            # Build JSON structure with image settings and docling config
            json_data = {
                "image": {
                    "saved_filename": image_path.name,
                    "original_filename": original_filename,
                    "file_id": file_id,
                    "message_date": message_date,
                    "file_size": image_path.stat().st_size if image_path.exists() else None,
                    "saved_at": message_date,
                },
                "docling_config": {
                    "backend": metadata.get("docling", {}).get("backend"),
                    "image_ocr_enabled": self.docling_config.image_ocr_enabled,
                    "ocr_languages": list(self.docling_config.ocr_languages),
                    "prefer_markdown_output": self.docling_config.prefer_markdown_output,
                    "fallback_plain_text": self.docling_config.fallback_plain_text,
                    "max_file_size_mb": self.docling_config.max_file_size_mb,
                },
                "docling_metadata": metadata.get("docling_mcp", {}),
                "processing": {
                    "processed_at": metadata.get("docling", {}).get("processed_at"),
                },
            }

            # Write JSON file
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved image metadata to: {json_path}")
            return json_path

        except Exception as e:
            self.logger.error(f"Failed to save image metadata JSON: {e}", exc_info=True)
            return None

    async def download_and_process_telegram_file(
        self,
        bot,
        file_info,
        original_filename: Optional[str] = None,
        kb_images_dir: Optional[Path] = None,
        file_id: Optional[str] = None,
        message_date: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Download file from Telegram and process it through Docling.

        Args:
            bot: Bot instance for downloading
            file_info: Telegram file info object
            original_filename: Original filename (e.g., "image.jpg", "document.pdf")
            kb_images_dir: If provided, images will be saved to this directory
            file_id: Telegram file_id for generating unique filename
            message_date: Message timestamp for generating unique filename

        Returns:
            Dict with processed content including 'saved_path' key if file was saved to KB
        """
        if not self.settings.is_media_processing_enabled():
            self.logger.info("Media processing disabled; skipping Telegram file download")
            return None

        if not self.docling_config.enabled:
            self.logger.info("Docling disabled; skipping Telegram file download")
            return None

        if not self.is_available():
            self.logger.warning("Docling backend not available; skipping Telegram file download")
            return None

        temp_dir = None
        temp_file = None

        try:
            # Determine file extension
            file_extension = ""
            if original_filename:
                file_extension = Path(original_filename).suffix
            elif hasattr(file_info, "file_path") and file_info.file_path:
                file_extension = Path(file_info.file_path).suffix

            extension = file_extension.lower().lstrip(".")
            if extension and not self.settings.is_format_enabled(extension, "docling"):
                self.logger.info(
                    "Skipping Telegram file %s because format %s is disabled for Docling",
                    original_filename or file_info.file_path,
                    extension,
                )
                return None

            # Check if this is an image that should be saved to KB
            is_image = extension in ["jpg", "jpeg", "png", "gif", "tiff", "bmp", "webp"]
            save_to_kb = kb_images_dir is not None and is_image

            # Download file first to check for duplicates
            downloaded_file = await bot.download_file(file_info.file_path)

            if save_to_kb:
                # AICODE-NOTE: Save images to KB for later reference in markdown files
                # Check for duplicates before saving
                kb_images_dir_abs = kb_images_dir.resolve()
                kb_images_dir_abs.mkdir(parents=True, exist_ok=True)

                # Compute hash of downloaded file
                file_hash = self._compute_file_hash(downloaded_file)

                # Check if this image already exists
                existing_file = self._find_existing_image_by_hash(
                    file_hash, kb_images_dir_abs, file_extension
                )

                if existing_file:
                    # Use existing file instead of saving duplicate
                    save_path = existing_file
                    unique_filename = existing_file.name
                    self.logger.info(f"Reusing existing image (duplicate detected): {save_path}")
                else:
                    # Generate unique filename using timestamp and file_id
                    import time

                    timestamp = message_date or int(time.time())
                    # Use first 8 chars of file_id as identifier (if available)
                    file_suffix = f"_{file_id[:8]}" if file_id else ""
                    unique_filename = f"img_{timestamp}{file_suffix}{file_extension}"

                    save_path = kb_images_dir_abs / unique_filename
                    self.logger.info(f"Saving new image to KB: {save_path}")

                    # Write file only if it's not a duplicate
                    with open(save_path, "wb") as f:
                        f.write(downloaded_file)

                    self.logger.info(f"File downloaded to: {save_path}")
            else:
                # Use temporary directory for non-images or when KB path not provided
                temp_dir = tempfile.mkdtemp(prefix="tg_note_file_")
                temp_filename = f"telegram_file{file_extension}"
                save_path = Path(temp_dir) / temp_filename
                self.logger.info(f"Downloading Telegram file to temp: {save_path}")

                with open(save_path, "wb") as f:
                    f.write(downloaded_file)

                self.logger.info(f"File downloaded to: {save_path}")

            # AICODE-NOTE: Validate saved image path (for images saved to KB)
            if save_to_kb and is_image:
                is_valid, error_msg = validate_image_path(save_path, kb_images_dir)
                if not is_valid:
                    self.logger.error(f"[FileProcessor] Saved image failed validation: {error_msg}")
                    self.logger.warning(
                        f"[FileProcessor] Image saved but may have path issues: {save_path}"
                    )
                else:
                    self.logger.info(f"[FileProcessor] ✓ Image path validated: {save_path}")

            # Process file
            result = await self.process_file(save_path)

            if result and save_to_kb:
                # AICODE-NOTE: Add saved path to result so ContentParser can reference it
                result["saved_path"] = str(save_path)
                result["saved_filename"] = unique_filename

                # AICODE-NOTE: Save image description and metadata for images
                # 1. .md file contains clean markdown from OCR (for easy reading)
                # 2. .json file contains all metadata (settings, config, timestamps)
                if is_image:
                    metadata = result.get("metadata", {})
                    markdown_text = result.get("text", "")

                    # Save clean markdown description
                    if markdown_text:
                        self._save_image_description_md(save_path, markdown_text)

                    # Save JSON metadata
                    self._save_image_metadata_json(
                        save_path,
                        metadata,
                        original_filename or "image.jpg",
                        file_id,
                        message_date,
                    )

                temp_file = None  # Don't delete this file in finally block
            elif not save_to_kb:
                temp_file = save_path  # Mark for cleanup

            return result

        except Exception as e:
            self.logger.error(f"Error downloading and processing Telegram file: {e}", exc_info=True)
            return None

        finally:
            # AICODE-NOTE: Only cleanup temporary files, not KB-saved images
            try:
                if temp_file and temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Removed temporary file: {temp_file}")
                if temp_dir:
                    Path(temp_dir).rmdir()
                    self.logger.debug(f"Removed temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                self.logger.warning(f"Error during cleanup: {cleanup_error}")
