from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import mimetypes
import os
import re
import tempfile
import threading
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
from tg_docling.config import DEFAULT_SETTINGS_PATH, load_docling_settings
from tg_docling.model_sync import sync_models

from config.settings import DoclingSettings
from mcp.types import ToolAnnotations

logger = logging.getLogger(__name__)


class DoclingModelMissingError(RuntimeError):
    """Raised when Docling conversion fails due to missing model artefacts."""


_MODEL_SYNC_LOCK = threading.Lock()


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


def _invalidate_converter_cache() -> None:
    """Clear the cached DocumentConverter so new artefacts are picked up."""
    cache_clear = getattr(conversion_tools._get_converter, "cache_clear", None)
    if callable(cache_clear):  # pragma: no cover - depends on decorated function
        cache_clear()


def _extract_missing_model_path(exc: BaseException) -> Optional[str]:
    """Attempt to extract the missing model artefact path from an exception."""
    if isinstance(exc, FileNotFoundError) and getattr(exc, "filename", None):
        filename = str(exc.filename)
        if filename:
            return filename

    message = str(exc)
    models_dir_hints = [
        os.getenv("DOCLING_MODELS_DIR"),
        "/opt/docling-mcp/models",
    ]

    for hint in [hint for hint in models_dir_hints if hint]:
        pattern = rf"({re.escape(hint)}/[^\s'\"`]+)"
        match = re.search(pattern, message)
        if match:
            return match.group(1)

    marker = "Missing safe tensors file:"
    if marker in message:
        return message.split(marker, 1)[1].strip().strip("'\"")

    fallback_match = re.search(r"(/[^'\s]+?\.(?:safetensors|onnx|bin|pt|json|txt))", message)
    if fallback_match:
        return fallback_match.group(1)

    return None


def _load_docling_settings_for_sync() -> Optional[DoclingSettings]:
    """Load Docling settings from the container configuration."""
    try:
        settings_path = Path(os.getenv("DOCLING_SETTINGS_PATH", str(DEFAULT_SETTINGS_PATH)))
        docling_settings, _ = load_docling_settings(settings_path)
        models_dir = Path(docling_settings.model_cache.base_dir)
        # AICODE-NOTE: Use direct assignment to ensure environment variables are updated
        # even if they were previously set to incorrect values
        os.environ["DOCLING_MODELS_DIR"] = str(models_dir)
        os.environ["DOCLING_ARTIFACTS_PATH"] = str(models_dir)
        if "DOCLING_CACHE_DIR" not in os.environ:
            os.environ["DOCLING_CACHE_DIR"] = "/opt/docling-mcp/cache"
        logger.debug(
            f"Updated Docling environment: DOCLING_MODELS_DIR={models_dir}, "
            f"DOCLING_ARTIFACTS_PATH={models_dir}"
        )
        return docling_settings
    except Exception:
        logger.exception(
            "Failed to load Docling settings while attempting model resynchronisation."
        )
        return None


def _attempt_model_resync(missing_path: str) -> bool:
    """
    Attempt to download missing Docling model artefacts and return True on success.

    This function is thread-safe to avoid concurrent download attempts.
    """
    with _MODEL_SYNC_LOCK:
        docling_settings = _load_docling_settings_for_sync()
        if docling_settings is None:
            return False

        logger.info(
            f"Attempting Docling model sync after detecting missing artefact: {missing_path}"
        )
        try:
            result = sync_models(docling_settings, force=False)
        except Exception:
            logger.exception(
                f"Docling model synchronisation failed for missing artefact {missing_path}"
            )
            return False

        summary = (result or {}).get("summary") or {}
        failed = summary.get("failed", 0)
        successful = summary.get("successful", 0)

        if failed:
            logger.error(
                f"Docling model sync completed with {failed} failure(s); missing artefact {missing_path} remains unavailable."
            )
            return False

        # AICODE-NOTE: Verify that model files were actually downloaded
        # The missing_path might point to artifacts_path directly (e.g., /models/model.safetensors)
        # but models are actually in subdirectories (e.g., /models/docling-models__layout__v2/model.safetensors)
        # The _fix_model_path() function in converter.py handles this by setting model_path to full path
        if successful == 0:
            logger.warning(
                f"Model sync completed but no models were downloaded (0 successful). "
                f"Missing artefact {missing_path} may still be unavailable."
            )
            # Don't return False here, as models might already be cached
            # The retry will reveal if models are truly missing

        logger.info(
            f"Docling model sync completed successfully ({successful} successful, {failed} failed); "
            "retrying conversion."
        )
        return True


def _build_missing_model_message(missing_path: str) -> str:
    """Create a user-facing error message for missing model artefacts."""
    models_dir = os.getenv("DOCLING_MODELS_DIR")
    relative_hint = None
    if models_dir:
        try:
            relative_hint = str(
                Path(missing_path).resolve().relative_to(Path(models_dir).resolve())
            )
        except Exception:
            relative_hint = None

    location_hint = (
        f"'{relative_hint}' under '{models_dir}'" if relative_hint else f"'{missing_path}'"
    )
    return (
        "Docling conversion requires a model artefact that is not available on disk "
        f"({location_hint}). Automatic recovery failed. "
        "Run the 'sync_docling_models' MCP tool or download the required Docling model bundles "
        "and retry the conversion."
    )


def _convert_with_model_recovery(tmp_path: Path):
    """Convert the provided document with automatic model resynchronisation fallback."""
    for attempt in range(2):
        converter = conversion_tools._get_converter()
        try:
            return converter.convert(tmp_path)
        except (FileNotFoundError, RuntimeError) as exc:
            missing_path = _extract_missing_model_path(exc)
            if missing_path is None:
                raise

            logger.warning(
                f"Docling conversion detected missing model artefact '{missing_path}' (attempt {attempt + 1})."
            )

            if attempt == 1:
                raise DoclingModelMissingError(_build_missing_model_message(missing_path)) from exc

            if not _attempt_model_resync(missing_path):
                raise DoclingModelMissingError(_build_missing_model_message(missing_path)) from exc

            _invalidate_converter_cache()

    raise DoclingModelMissingError(
        "Docling conversion failed due to missing model artefacts despite recovery attempts."
    )


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

        logger.info(f"Converting document from base64 content (temp file: {tmp_path})")
        result = _convert_with_model_recovery(tmp_path)

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

    except DoclingModelMissingError as exc:
        logger.exception("Missing Docling model artefact prevented document conversion.")
        raise
    except Exception as exc:
        logger.exception("Failed to convert base64 document content.")
        raise RuntimeError(f"Unexpected error: {exc!s}") from exc

    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:  # pragma: no cover - best effort cleanup
                logger.debug(f"Failed to remove temporary file: {tmp_path}", exc_info=True)
