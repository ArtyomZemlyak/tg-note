from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import mimetypes
import tempfile
from pathlib import Path
from typing import Annotated, Optional

try:  # Optional dependency already included in container image
    import filetype  # type: ignore
except Exception:  # pragma: no cover - fallback when library is unavailable
    filetype = None  # type: ignore

from docling_core.types.doc.document import ContentLayer
from docling_core.types.doc.labels import DocItemLabel
from docling_mcp.docling_cache import get_cache_key
from docling_mcp.shared import local_document_cache, local_stack_cache
from docling_mcp.shared import mcp as d_mcp
from docling_mcp.tools import conversion as conversion_tools
from docling_mcp.tools.conversion import ConvertDocumentOutput, cleanup_memory
from pydantic import Field

from mcp.types import ToolAnnotations

logger = logging.getLogger(__name__)


def _detect_suffix(filename: Optional[str], mime_type: Optional[str], data: bytes) -> Optional[str]:
    """Best-effort detection of file extension for temporary file handling."""
    if filename:
        suffix = Path(filename).suffix
        if suffix:
            return suffix

    if mime_type:
        guessed = mimetypes.guess_extension(mime_type, strict=False)
        if guessed:
            return guessed

    if filetype is not None:  # pragma: no cover - depends on optional library
        try:
            kind = filetype.guess(data)
            if kind and kind.extension:
                return f".{kind.extension}"
        except Exception:  # Defensive: guessing failure should not break processing
            logger.debug("filetype.guess failed", exc_info=True)

    return None


@d_mcp.tool(
    title="Convert document from base64 content",
    description=(
        "Decode a base64-encoded document payload, convert it with Docling and cache the result."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
def convert_document_from_content(
    content: Annotated[
        str,
        Field(
            description="Base64 encoded document content.",
            examples=["JVBERi0xLjcKJcTl8uXrp..."],
        ),
    ],
    filename: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Optional original filename (used for extension detection and metadata).",
            examples=["document.pdf"],
        ),
    ] = None,
    mime_type: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Optional MIME type hint (e.g. application/pdf).",
            examples=["application/pdf"],
        ),
    ] = None,
) -> ConvertDocumentOutput:
    """Convert a document provided as base64 content and cache the converted Docling result."""

    try:
        payload = base64.b64decode(content)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 content provided.") from exc

    if not payload:
        raise ValueError("Empty document content received.")

    suffix = _detect_suffix(filename, mime_type, payload) or ".bin"
    cache_source = f"bytes:{hashlib.sha256(payload).hexdigest()}:{filename or ''}"
    cache_key = get_cache_key(cache_source)

    if cache_key in local_document_cache:
        logger.info("Document content already converted (cache hit).")
        return ConvertDocumentOutput(True, cache_key)

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="docling_upload_", suffix=suffix, delete=False
        ) as tmp_file:
            tmp_file.write(payload)
            tmp_file.flush()
            tmp_path = Path(tmp_file.name)

        converter = conversion_tools._get_converter()
        logger.info("Converting document from base64 content (temp file: %s)", tmp_path)
        result = converter.convert(tmp_path)

        # Mirror error handling strategy from upstream conversion tool
        has_error = False
        error_message = ""

        if hasattr(result, "status"):
            if hasattr(result.status, "is_error"):
                has_error = result.status.is_error
            elif hasattr(result.status, "error"):
                has_error = result.status.error

        if hasattr(result, "errors") and result.errors:
            has_error = True
            error_message = str(result.errors)

        if has_error:
            error_msg = f"Conversion failed: {error_message}"
            raise RuntimeError(error_msg)

        document = result.document
        source_label = filename or tmp_path.name
        item = document.add_text(
            label=DocItemLabel.TEXT,
            text=f"source: {source_label}",
            content_layer=ContentLayer.FURNITURE,
        )

        local_document_cache[cache_key] = document
        local_stack_cache[cache_key] = [item]

        cleanup_memory()

        return ConvertDocumentOutput(False, cache_key)

    except Exception as exc:
        logger.exception("Failed to convert base64 document content.")
        raise RuntimeError(f"Unexpected error: {exc!s}") from exc

    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:  # pragma: no cover - best effort cleanup
                logger.debug("Failed to remove temporary file: %s", tmp_path, exc_info=True)
