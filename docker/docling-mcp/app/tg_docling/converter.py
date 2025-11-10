from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Set

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    OcrOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_mcp.settings import conversion as conversion_settings
from docling_mcp.tools import conversion as conversion_tools

try:  # Optional dependency
    from docling_ocr_onnxtr.pipeline_options import OnnxtrOcrOptions
except Exception:  # pragma: no cover
    OnnxtrOcrOptions = None

from config.settings import DoclingSettings

logger = logging.getLogger(__name__)


def _model_field_names(target: object) -> Optional[Set[str]]:
    """Return the declared field names for a Pydantic model (v1 or v2)."""
    cls = target if isinstance(target, type) else target.__class__

    model_fields = getattr(cls, "model_fields", None)
    if isinstance(model_fields, dict):
        return set(model_fields.keys())
    if isinstance(model_fields, set):
        return model_fields

    legacy_fields = getattr(cls, "__fields__", None)
    if isinstance(legacy_fields, dict):
        return set(legacy_fields.keys())

    return None


def _supports_field(target: object, field: str) -> bool:
    """Return True when the provided target defines a given Pydantic field."""
    field_names = _model_field_names(target)
    return field_names is None or field in field_names


def _resolve_path(base_dir: Path, value: Optional[str]) -> Optional[str]:
    """Resolve a model path relative to the model cache directory."""
    if not value:
        return None

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()

    if not candidate.exists():
        logger.warning("Configured model path does not exist: %s", candidate)
    return str(candidate)


def _apply_optional_attributes(obj: object, values: Dict[str, object]) -> None:
    """Attempt to populate optional attributes without raising when missing."""
    for key, value in values.items():
        if value is None:
            continue
        if _supports_field(obj, key):
            setattr(obj, key, value)
        else:
            logger.debug("Skipping unsupported attribute '%s' for %s", key, type(obj).__name__)


def _build_ocr_options(settings: DoclingSettings, models_base: Path) -> Optional[OcrOptions]:
    """Construct OCR options based on container configuration."""
    ocr_cfg = settings.ocr_config
    languages = ocr_cfg.languages or settings.ocr_languages

    if settings.image_ocr_enabled is False or ocr_cfg.backend == "none":
        return None

    if ocr_cfg.backend == "rapidocr":
        backend_cfg = ocr_cfg.rapidocr
        opts = RapidOcrOptions()
        _apply_optional_attributes(
            opts,
            {
                "lang": languages,
                "backend": backend_cfg.backend,
                "det_model_path": _resolve_path(models_base, backend_cfg.det_model_path),
                "rec_model_path": _resolve_path(models_base, backend_cfg.rec_model_path),
                "cls_model_path": _resolve_path(models_base, backend_cfg.cls_model_path),
                "rec_keys_path": _resolve_path(models_base, backend_cfg.rec_keys_path),
            },
        )
        if _supports_field(opts, "rapidocr_params"):
            params = dict(getattr(opts, "rapidocr_params", {}) or {})
            params.update(backend_cfg.rapidocr_params or {})
            if backend_cfg.providers:
                params.setdefault("providers", backend_cfg.providers)
            setattr(opts, "rapidocr_params", params)
        elif backend_cfg.rapidocr_params or backend_cfg.providers:
            logger.debug("Skipping unsupported rapidocr parameters for %s", type(opts).__name__)
        return opts

    if ocr_cfg.backend == "easyocr":
        backend_cfg = ocr_cfg.easyocr
        opts = EasyOcrOptions()
        _apply_optional_attributes(
            opts,
            {
                "lang": backend_cfg.languages or languages,
                "use_gpu": backend_cfg.gpu == "cuda" if backend_cfg.gpu != "auto" else None,
                "recog_network": backend_cfg.recog_network,
                "model_storage_directory": (
                    _resolve_path(models_base, backend_cfg.model_storage_dir)
                    if backend_cfg.model_storage_dir
                    else None
                ),
                "download_enabled": backend_cfg.download_enabled,
            },
        )
        _apply_optional_attributes(opts, backend_cfg.extra or {})
        return opts

    if ocr_cfg.backend == "tesseract":
        backend_cfg = ocr_cfg.tesseract
        opts = TesseractOcrOptions()
        _apply_optional_attributes(
            opts,
            {
                "lang": backend_cfg.languages or languages,
                "path": backend_cfg.tessdata_prefix,
                "psm": backend_cfg.psm,
            },
        )
        return opts

    if ocr_cfg.backend == "onnxtr" and OnnxtrOcrOptions is not None:
        backend_cfg = ocr_cfg.onnxtr
        opts = OnnxtrOcrOptions()  # type: ignore[misc]
        _apply_optional_attributes(
            opts,
            {
                "lang": languages,
                "det_model_path": _resolve_path(models_base, backend_cfg.det_model_path),
                "rec_model_path": _resolve_path(models_base, backend_cfg.rec_model_path),
                "cls_model_path": _resolve_path(models_base, backend_cfg.cls_model_path),
            },
        )
        if backend_cfg.providers:
            _apply_optional_attributes(opts, {"providers": backend_cfg.providers})
        _apply_optional_attributes(opts, backend_cfg.extra or {})
        return opts

    if ocr_cfg.backend == "tesseract_cli":
        opts = TesseractCliOcrOptions()
        _apply_optional_attributes(opts, {"lang": languages})
        return opts

    logger.warning("Unsupported OCR backend configured: %s", ocr_cfg.backend)
    return None


def _create_converter(settings: DoclingSettings) -> DocumentConverter:
    """Internal factory for DocumentConverter configured according to settings."""
    models_base = Path(settings.model_cache.base_dir)
    models_base.mkdir(parents=True, exist_ok=True)

    pdf_options = PdfPipelineOptions()
    pdf_options.artifacts_path = models_base
    pdf_options.generate_page_images = settings.generate_page_images or settings.keep_images
    pdf_options.do_ocr = settings.image_ocr_enabled
    if _supports_field(PdfPipelineOptions, "force_full_page_ocr"):
        pdf_options.force_full_page_ocr = settings.ocr_config.force_full_page_ocr
    elif settings.ocr_config.force_full_page_ocr:
        logger.warning(
            "Docling PdfPipelineOptions does not support 'force_full_page_ocr'; option will be ignored."
        )

    ocr_options = _build_ocr_options(settings, models_base=models_base)
    if ocr_options is not None:
        pdf_options.ocr_options = ocr_options
    else:
        pdf_options.do_ocr = False

    format_options = {
        InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
        InputFormat.IMAGE: PdfFormatOption(pipeline_options=pdf_options),
    }

    logger.info(
        "Initialising DocumentConverter (ocr_enabled=%s, backend=%s)",
        pdf_options.do_ocr,
        settings.ocr_config.backend,
    )

    return DocumentConverter(format_options=format_options)


def install_converter(settings: DoclingSettings) -> None:
    """Install a patched converter factory inside docling-mcp."""
    conversion_settings.settings.keep_images = settings.keep_images

    @lru_cache(maxsize=1)
    def _factory() -> DocumentConverter:
        return _create_converter(settings)

    conversion_tools._get_converter.cache_clear()
    conversion_tools._get_converter = _factory  # type: ignore[assignment]
    logger.info("Docling converter override installed successfully")
