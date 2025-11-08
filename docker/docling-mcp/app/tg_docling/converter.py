from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, OcrOptions, PdfPipelineOptions, RapidOcrOptions, TesseractCliOcrOptions, TesseractOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_mcp.settings import conversion as conversion_settings
from docling_mcp.tools import conversion as conversion_tools

try:  # Optional dependency
    from docling_ocr_onnxtr.pipeline_options import OnnxtrOcrOptions
except Exception:  # pragma: no cover
    OnnxtrOcrOptions = None

from tg_docling.config import ContainerConfig

logger = logging.getLogger(__name__)


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
        if hasattr(obj, key):
            setattr(obj, key, value)
        else:
            logger.debug(
                "Skipping unsupported attribute '%s' for %s", key, type(obj).__name__
            )


def _build_ocr_options(
    config: ContainerConfig, models_base: Path
) -> Optional[OcrOptions]:
    """Construct OCR options based on container configuration."""
    ocr_cfg = config.converter.ocr
    languages = ocr_cfg.languages

    if config.converter.image_ocr_enabled is False or ocr_cfg.backend == "none":
        return None

    if ocr_cfg.backend == "rapidocr":
        backend_cfg = ocr_cfg.rapidocr
        opts = RapidOcrOptions()
        opts.lang = languages
        opts.backend = backend_cfg.backend
        opts.det_model_path = _resolve_path(models_base, backend_cfg.det_model_path)
        opts.rec_model_path = _resolve_path(models_base, backend_cfg.rec_model_path)
        opts.cls_model_path = _resolve_path(models_base, backend_cfg.cls_model_path)
        opts.rec_keys_path = _resolve_path(models_base, backend_cfg.rec_keys_path)
        opts.rapidocr_params.update(backend_cfg.rapidocr_params or {})
        if backend_cfg.providers:
            opts.rapidocr_params.setdefault("providers", backend_cfg.providers)
        return opts

    if ocr_cfg.backend == "easyocr":
        backend_cfg = ocr_cfg.easyocr
        opts = EasyOcrOptions()
        opts.lang = backend_cfg.languages or languages
        if backend_cfg.gpu != "auto":
            opts.use_gpu = backend_cfg.gpu == "cuda"
        opts.recog_network = backend_cfg.recog_network
        opts.model_storage_directory = (
            _resolve_path(models_base, backend_cfg.model_storage_dir)
            if backend_cfg.model_storage_dir
            else None
        )
        opts.download_enabled = backend_cfg.download_enabled
        _apply_optional_attributes(opts, backend_cfg.extra or {})
        return opts

    if ocr_cfg.backend == "tesseract":
        backend_cfg = ocr_cfg.tesseract
        opts = TesseractOcrOptions()
        opts.lang = backend_cfg.languages or languages
        opts.path = backend_cfg.tessdata_prefix
        opts.psm = backend_cfg.psm
        return opts

    if ocr_cfg.backend == "onnxtr" and OnnxtrOcrOptions is not None:
        backend_cfg = ocr_cfg.onnxtr
        opts = OnnxtrOcrOptions()  # type: ignore[misc]
        opts.lang = languages
        opts.det_model_path = _resolve_path(models_base, backend_cfg.det_model_path)
        opts.rec_model_path = _resolve_path(models_base, backend_cfg.rec_model_path)
        opts.cls_model_path = _resolve_path(models_base, backend_cfg.cls_model_path)
        if backend_cfg.providers:
            _apply_optional_attributes(opts, {"providers": backend_cfg.providers})
        _apply_optional_attributes(opts, backend_cfg.extra or {})
        return opts

    if ocr_cfg.backend == "tesseract_cli":
        opts = TesseractCliOcrOptions()
        opts.lang = languages
        return opts

    logger.warning("Unsupported OCR backend configured: %s", ocr_cfg.backend)
    return None


def _create_converter(config: ContainerConfig) -> DocumentConverter:
    """Internal factory for DocumentConverter configured according to settings."""
    models_base = config.model_cache.base_dir
    models_base.mkdir(parents=True, exist_ok=True)

    pdf_options = PdfPipelineOptions()
    pdf_options.generate_page_images = (
        config.converter.generate_page_images or config.converter.keep_images
    )
    pdf_options.do_ocr = config.converter.image_ocr_enabled
    pdf_options.force_full_page_ocr = config.converter.ocr.force_full_page_ocr

    ocr_options = _build_ocr_options(config, models_base=models_base)
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
        config.converter.ocr.backend,
    )

    return DocumentConverter(format_options=format_options)


def install_converter(config: ContainerConfig) -> None:
    """Install a patched converter factory inside docling-mcp."""
    conversion_settings.settings.keep_images = config.converter.keep_images

    @lru_cache(maxsize=1)
    def _factory() -> DocumentConverter:
        return _create_converter(config)

    conversion_tools._get_converter.cache_clear()
    conversion_tools._get_converter = _factory  # type: ignore[assignment]
    logger.info("Docling converter override installed successfully")
