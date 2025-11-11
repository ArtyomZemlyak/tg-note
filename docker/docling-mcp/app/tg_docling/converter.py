from __future__ import annotations

import os
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
from loguru import logger

try:  # Optional dependency
    from docling_ocr_onnxtr.pipeline_options import OnnxtrOcrOptions
except Exception:  # pragma: no cover
    OnnxtrOcrOptions = None

from tg_docling.tesseract import resolve_tessdata_path

from config.settings import DoclingSettings

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
        logger.warning(f"Configured model path does not exist: {candidate}")
    return str(candidate)


def _apply_optional_attributes(obj: object, values: Dict[str, object]) -> None:
    """Attempt to populate optional attributes without raising when missing."""
    for key, value in values.items():
        if value is None:
            continue
        if _supports_field(obj, key):
            setattr(obj, key, value)
        else:
            logger.debug(f"Skipping unsupported attribute '{key}' for {type(obj).__name__}")


def _build_ocr_options(settings: DoclingSettings, models_base: Path) -> Optional[OcrOptions]:
    """Construct OCR options based on container configuration."""
    ocr_cfg = settings.ocr_config
    languages = ocr_cfg.languages or settings.ocr_languages

    logger.info(
        f"Building OCR options: backend={ocr_cfg.backend}, "
        f"image_ocr_enabled={settings.image_ocr_enabled}, languages={languages}"
    )

    if settings.image_ocr_enabled is False or ocr_cfg.backend == "none":
        logger.info(
            f"OCR disabled (image_ocr_enabled={settings.image_ocr_enabled}, backend={ocr_cfg.backend})"
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
            logger.debug(f"Skipping unsupported rapidocr parameters for {type(opts).__name__}")
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
            f"Creating TesseractOcrOptions: enabled={backend_cfg.enabled}, "
            f"languages={backend_cfg.languages or languages}, "
            f"tessdata_prefix={backend_cfg.tessdata_prefix}"
        )
        try:
            opts = TesseractOcrOptions()
            tessdata_path = resolve_tessdata_path(models_base, backend_cfg.tessdata_prefix)
            if tessdata_path:
                if not os.environ.get("TESSDATA_PREFIX"):
                    os.environ["TESSDATA_PREFIX"] = tessdata_path
                    logger.debug(f"Set TESSDATA_PREFIX environment variable to {tessdata_path}")
                logger.info(f"Using Tesseract tessdata directory: {tessdata_path}")
            _apply_optional_attributes(
                opts,
                {
                    "lang": backend_cfg.languages or languages,
                    "path": tessdata_path or backend_cfg.tessdata_prefix,
                    "psm": backend_cfg.psm,
                },
            )
            _apply_optional_attributes(opts, backend_cfg.extra or {})
            logger.info(f"TesseractOcrOptions created successfully: lang={opts.lang}")
            return opts
        except Exception as exc:
            logger.error(
                f"Failed to create TesseractOcrOptions: {exc}. Falling back to None (Docling will auto-select).",
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

    logger.warning(f"Unsupported OCR backend configured: {ocr_cfg.backend}")
    return None


def _fix_model_path(
    model_spec_or_options: object, models_base: Path, folder_attr: str = "model_repo_folder"
) -> None:
    """
    Fix model path in model spec or options to use absolute path.

    This ensures Docling can find model.safetensors files in the correct subdirectory.
    Problem: Docling searches for model.safetensors in artifacts_path directly, ignoring
    model_repo_folder/repo_cache_folder from model_spec. Solution: set model_path to full path.

    Args:
        model_spec_or_options: Model spec or options object (e.g., layout_spec, preset_options)
        models_base: Base directory for models
        folder_attr: Attribute name for folder path (model_repo_folder or repo_cache_folder)
    """
    if not hasattr(model_spec_or_options, folder_attr):
        return

    folder_path = getattr(model_spec_or_options, folder_attr)
    if not folder_path:
        return

    # Construct full path to model directory: models_base / folder_path
    if Path(folder_path).is_absolute():
        model_dir_path = Path(folder_path)
    else:
        model_dir_path = models_base / folder_path

    model_dir_str = str(model_dir_path.resolve())

    # Set model_path if the spec supports it (preferred method)
    if hasattr(model_spec_or_options, "model_path"):
        setattr(model_spec_or_options, "model_path", model_dir_str)
        logger.info(
            f"Set model_path in {type(model_spec_or_options).__name__} to: {model_dir_str} "
            f"({folder_attr} remains: {folder_path})"
        )
    else:
        # If model_path is not supported, try setting folder_attr to absolute path
        # This is a fallback for older Docling versions
        if not Path(folder_path).is_absolute():
            setattr(model_spec_or_options, folder_attr, model_dir_str)
            logger.info(
                f"model_path not supported, set {folder_attr} to absolute path: {model_dir_str} (was: {folder_path})"
            )


def _create_converter(settings: DoclingSettings) -> DocumentConverter:
    """Internal factory for DocumentConverter configured according to settings."""
    logger.info("Creating CUSTOM DocumentConverter with tg-note settings")
    models_base = Path(settings.model_cache.base_dir)
    models_base.mkdir(parents=True, exist_ok=True)

    pipeline_flags, missing_models = settings.resolved_pipeline_flags()
    for missing in missing_models:
        logger.warning(
            f"Docling pipeline requested model bundle '{missing}' but it is disabled; corresponding stage will be skipped."
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
    logger.debug(f"Set PdfPipelineOptions.artifacts_path to: {models_base}")
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
            f"Unknown Docling layout preset '{layout_cfg.preset}'; defaulting to 'layout_v2'."
        )
        layout_spec = DOCLING_LAYOUT_V2

    # AICODE-NOTE: Use layout preset attributes (repo_id, revision, model_path) for model loading
    # The model_copy() ensures all preset attributes are properly transferred
    logger.info(
        f"Using layout preset '{layout_cfg.preset}' "
        f"(repo_id={getattr(layout_spec, 'repo_id', 'N/A')}, "
        f"revision={getattr(layout_spec, 'revision', 'N/A')}, "
        f"model_repo_folder={getattr(layout_spec, 'model_repo_folder', 'N/A')})"
    )

    # AICODE-NOTE: Fix model path to ensure Docling can find model.safetensors in correct subdirectory
    model_spec_copy = layout_spec.model_copy()
    logger.debug(
        f"Layout model spec before path fix: model_repo_folder={getattr(model_spec_copy, 'model_repo_folder', 'N/A')}, "
        f"model_path={getattr(model_spec_copy, 'model_path', 'N/A')}"
    )
    _fix_model_path(model_spec_copy, models_base, folder_attr="model_repo_folder")
    logger.debug(
        f"Layout model spec after path fix: model_repo_folder={getattr(model_spec_copy, 'model_repo_folder', 'N/A')}, "
        f"model_path={getattr(model_spec_copy, 'model_path', 'N/A')}"
    )

    pdf_options.layout_options = LayoutOptions(
        create_orphan_clusters=layout_cfg.create_orphan_clusters,
        keep_empty_clusters=layout_cfg.keep_empty_clusters,
        skip_cell_assignment=layout_cfg.skip_cell_assignment,
        model_spec=model_spec_copy,
    )

    table_cfg = settings.pipeline.table_structure
    pdf_options.do_table_structure = pipeline_flags["table_structure"]
    try:
        pdf_options.table_structure_options.mode = TableFormerMode(table_cfg.mode)
    except Exception:
        logger.warning(f"Unknown TableFormer mode '{table_cfg.mode}'; defaulting to 'accurate'.")
        pdf_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pdf_options.table_structure_options.do_cell_matching = table_cfg.do_cell_matching

    # AICODE-NOTE: Fix model path for table_structure if it uses model_spec
    # TableStructureOptions may have model_spec with model_repo_folder
    if hasattr(pdf_options.table_structure_options, "model_spec"):
        table_model_spec = getattr(pdf_options.table_structure_options, "model_spec")
        if table_model_spec is not None:
            # Create a copy to avoid modifying the original if it's shared
            if hasattr(table_model_spec, "model_copy"):
                table_model_spec = table_model_spec.model_copy()
                setattr(pdf_options.table_structure_options, "model_spec", table_model_spec)
            _fix_model_path(table_model_spec, models_base, folder_attr="model_repo_folder")

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
                f"Using picture description preset '{preset_name}' "
                f"(repo_id={getattr(preset_copy, 'repo_id', 'N/A')}, "
                f"repo_cache_folder={getattr(preset_copy, 'repo_cache_folder', 'N/A')})"
            )
            # AICODE-NOTE: Fix model path for picture description preset
            _fix_model_path(preset_copy, models_base, folder_attr="repo_cache_folder")

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
            # Copy fixed model_path/repo_cache_folder to desc_options if supported
            if hasattr(preset_copy, "model_path") and hasattr(desc_options, "model_path"):
                setattr(desc_options, "model_path", getattr(preset_copy, "model_path"))
            if hasattr(preset_copy, "repo_cache_folder") and hasattr(
                desc_options, "repo_cache_folder"
            ):
                setattr(
                    desc_options, "repo_cache_folder", getattr(preset_copy, "repo_cache_folder")
                )
        else:
            spec = _PICTURE_DESCRIPTION_SPEC_MAP.get(preset_name)
            if spec is None:
                logger.warning(
                    f"Unknown picture description preset '{preset_name}'; picture description will use default options."
                )
            else:
                logger.info(
                    f"Using picture description spec '{preset_name}' "
                    f"(repo_id={getattr(spec, 'repo_id', 'N/A')}, "
                    f"repo_cache_folder={getattr(spec, 'repo_cache_folder', 'N/A')})"
                )
                # AICODE-NOTE: Fix model path for picture description spec
                # Create a copy to avoid modifying the original spec
                spec_copy = spec.model_copy() if hasattr(spec, "model_copy") else spec
                _fix_model_path(spec_copy, models_base, folder_attr="repo_cache_folder")

                if hasattr(desc_options, "repo_id"):
                    setattr(desc_options, "repo_id", getattr(spec, "repo_id", None))
                # Copy fixed model_path/repo_cache_folder to desc_options if supported
                if hasattr(spec_copy, "model_path") and hasattr(desc_options, "model_path"):
                    setattr(desc_options, "model_path", getattr(spec_copy, "model_path"))
                if hasattr(spec_copy, "repo_cache_folder") and hasattr(
                    desc_options, "repo_cache_folder"
                ):
                    setattr(
                        desc_options, "repo_cache_folder", getattr(spec_copy, "repo_cache_folder")
                    )

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
        f"Initialising CUSTOM DocumentConverter (ocr_enabled={pdf_options.do_ocr}, backend={settings.ocr_config.backend})"
    )
    logger.info(f"OCR options type: {type(ocr_options).__name__ if ocr_options else 'None'}")

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
