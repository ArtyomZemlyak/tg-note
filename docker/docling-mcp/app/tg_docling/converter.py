from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Set

from docling.datamodel.base_models import InputFormat
from docling.datamodel.layout_model_specs import (
    DOCLING_LAYOUT_EGRET_LARGE,
    DOCLING_LAYOUT_EGRET_MEDIUM,
    DOCLING_LAYOUT_EGRET_XLARGE,
    DOCLING_LAYOUT_HERON,
    DOCLING_LAYOUT_HERON_101,
    DOCLING_LAYOUT_V2,
)
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    LayoutOptions,
    OcrOptions,
    PdfPipelineOptions,
    PictureDescriptionVlmOptions,
    RapidOcrOptions,
    TableFormerMode,
    TableStructureOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
    granite_picture_description,
    smolvlm_picture_description,
)
from docling.datamodel.vlm_model_specs import (
    GRANITE_VISION_TRANSFORMERS,
    GRANITEDOCLING_MLX,
    GRANITEDOCLING_TRANSFORMERS,
    SMOLDOCLING_MLX,
    SMOLDOCLING_TRANSFORMERS,
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

# AICODE-NOTE: Layout model presets map - exported for use in model_sync.py
_LAYOUT_PRESET_MAP = {
    "layout_v2": DOCLING_LAYOUT_V2,
    "layout_heron": DOCLING_LAYOUT_HERON,
    "layout_heron_101": DOCLING_LAYOUT_HERON_101,
    "layout_egret_medium": DOCLING_LAYOUT_EGRET_MEDIUM,
    "layout_egret_large": DOCLING_LAYOUT_EGRET_LARGE,
    "layout_egret_xlarge": DOCLING_LAYOUT_EGRET_XLARGE,
}

# AICODE-NOTE: Picture description preset options - exported for use in model_sync.py
_PICTURE_DESCRIPTION_PRESET_OPTIONS = {
    "smolvlm": smolvlm_picture_description,
    "granite_vision": granite_picture_description,
}

# AICODE-NOTE: Picture description model specs map - exported for use in model_sync.py
_PICTURE_DESCRIPTION_SPEC_MAP = {
    "granitedocling": GRANITEDOCLING_TRANSFORMERS,
    "granitedocling_mlx": GRANITEDOCLING_MLX,
    "smoldocling": SMOLDOCLING_TRANSFORMERS,
    "smoldocling_mlx": SMOLDOCLING_MLX,
    # Granite Vision preset handled via _PICTURE_DESCRIPTION_PRESET_OPTIONS, but keep transformers fallback
    "granite_vision": GRANITE_VISION_TRANSFORMERS,
}


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

    logger.info(
        "Building OCR options: backend=%s, image_ocr_enabled=%s, languages=%s",
        ocr_cfg.backend,
        settings.image_ocr_enabled,
        languages,
    )

    if settings.image_ocr_enabled is False or ocr_cfg.backend == "none":
        logger.info(
            "OCR disabled (image_ocr_enabled=%s, backend=%s)",
            settings.image_ocr_enabled,
            ocr_cfg.backend,
        )
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
        logger.info(
            "Creating TesseractOcrOptions: enabled=%s, languages=%s, tessdata_prefix=%s",
            backend_cfg.enabled,
            backend_cfg.languages or languages,
            backend_cfg.tessdata_prefix,
        )
        try:
            opts = TesseractOcrOptions()
            _apply_optional_attributes(
                opts,
                {
                    "lang": backend_cfg.languages or languages,
                    "path": backend_cfg.tessdata_prefix,
                    "psm": backend_cfg.psm,
                },
            )
            logger.info("TesseractOcrOptions created successfully: lang=%s", opts.lang)
            return opts
        except Exception as exc:
            logger.error(
                "Failed to create TesseractOcrOptions: %s. Falling back to None (Docling will auto-select).",
                exc,
                exc_info=True,
            )
            return None

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

    pipeline_flags, missing_models = settings.resolved_pipeline_flags()
    for missing in missing_models:
        logger.warning(
            "Docling pipeline requested model bundle '%s' but it is disabled; corresponding stage will be skipped.",
            missing,
        )

    if not pipeline_flags.get("layout", False):
        if settings.pipeline.layout.enabled:
            raise RuntimeError(
                "Docling layout model bundle is disabled but layout stage is required. "
                "Enable the layout bundle under MEDIA_PROCESSING_DOCLING.model_cache.builtin_models."
            )
        raise RuntimeError(
            "Docling layout analysis stage cannot be disabled. "
            "Set MEDIA_PROCESSING_DOCLING.pipeline.layout.enabled to true."
        )

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

    layout_cfg = settings.pipeline.layout
    layout_spec = _LAYOUT_PRESET_MAP.get(layout_cfg.preset)
    if layout_spec is None:
        logger.warning(
            "Unknown Docling layout preset '%s'; defaulting to 'layout_v2'.", layout_cfg.preset
        )
        layout_spec = DOCLING_LAYOUT_V2

    # AICODE-NOTE: Use layout preset attributes (repo_id, revision, model_path) for model loading
    # The model_copy() ensures all preset attributes are properly transferred
    logger.info(
        "Using layout preset '%s' (repo_id=%s, revision=%s, model_repo_folder=%s)",
        layout_cfg.preset,
        getattr(layout_spec, "repo_id", "N/A"),
        getattr(layout_spec, "revision", "N/A"),
        getattr(layout_spec, "model_repo_folder", "N/A"),
    )

    pdf_options.layout_options = LayoutOptions(
        create_orphan_clusters=layout_cfg.create_orphan_clusters,
        keep_empty_clusters=layout_cfg.keep_empty_clusters,
        skip_cell_assignment=layout_cfg.skip_cell_assignment,
        model_spec=layout_spec.model_copy(),
    )

    table_cfg = settings.pipeline.table_structure
    pdf_options.do_table_structure = pipeline_flags["table_structure"]
    try:
        pdf_options.table_structure_options.mode = TableFormerMode(table_cfg.mode)
    except Exception:
        logger.warning("Unknown TableFormer mode '%s'; defaulting to 'accurate'.", table_cfg.mode)
        pdf_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pdf_options.table_structure_options.do_cell_matching = table_cfg.do_cell_matching

    pdf_options.do_code_enrichment = pipeline_flags["code_enrichment"]
    pdf_options.do_formula_enrichment = pipeline_flags["formula_enrichment"]

    pdf_options.do_picture_classification = pipeline_flags["picture_classifier"]

    picture_description_enabled = pipeline_flags["picture_description"]
    pdf_options.do_picture_description = picture_description_enabled

    # Generate picture images whenever any vision pipeline is active
    pdf_options.generate_picture_images = any(
        [
            pdf_options.do_picture_classification,
            picture_description_enabled,
        ]
    )

    if picture_description_enabled:
        desc_cfg = settings.pipeline.picture_description
        desc_options: PictureDescriptionVlmOptions = pdf_options.picture_description_options
        preset_name = desc_cfg.model

        # AICODE-NOTE: Log which picture description model is being loaded
        preset_options = _PICTURE_DESCRIPTION_PRESET_OPTIONS.get(preset_name)
        if preset_options is not None:
            preset_copy = preset_options.model_copy()
            logger.info(
                "Using picture description preset '%s' (repo_id=%s, repo_cache_folder=%s)",
                preset_name,
                getattr(preset_copy, "repo_id", "N/A"),
                getattr(preset_copy, "repo_cache_folder", "N/A"),
            )
            for attr in (
                "batch_size",
                "scale",
                "picture_area_threshold",
                "prompt",
                "generation_config",
            ):
                if hasattr(desc_options, attr) and hasattr(preset_copy, attr):
                    value = getattr(preset_copy, attr)
                    if attr == "generation_config":
                        value = dict(value or {})
                    setattr(desc_options, attr, value)

            if hasattr(desc_options, "repo_id") and hasattr(preset_copy, "repo_id"):
                setattr(desc_options, "repo_id", getattr(preset_copy, "repo_id"))
        else:
            spec = _PICTURE_DESCRIPTION_SPEC_MAP.get(preset_name)
            if spec is None:
                logger.warning(
                    "Unknown picture description preset '%s'; picture description will use default options.",
                    preset_name,
                )
            else:
                logger.info(
                    "Using picture description spec '%s' (repo_id=%s, repo_cache_folder=%s)",
                    preset_name,
                    getattr(spec, "repo_id", "N/A"),
                    getattr(spec, "repo_cache_folder", "N/A"),
                )
                if hasattr(desc_options, "repo_id"):
                    setattr(desc_options, "repo_id", getattr(spec, "repo_id", None))

        if desc_cfg.batch_size is not None and hasattr(desc_options, "batch_size"):
            desc_options.batch_size = desc_cfg.batch_size
        if desc_cfg.scale is not None and hasattr(desc_options, "scale"):
            desc_options.scale = desc_cfg.scale
        if desc_cfg.picture_area_threshold is not None and hasattr(
            desc_options, "picture_area_threshold"
        ):
            desc_options.picture_area_threshold = desc_cfg.picture_area_threshold
        if desc_cfg.prompt is not None and hasattr(desc_options, "prompt"):
            desc_options.prompt = desc_cfg.prompt
        if desc_cfg.generation_config:
            if hasattr(desc_options, "generation_config"):
                config = dict(getattr(desc_options, "generation_config", {}) or {})
                config.update(desc_cfg.generation_config)
                desc_options.generation_config = config
            else:
                logger.debug(
                    "Picture description generation config overrides ignored (unsupported attribute)."
                )

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
