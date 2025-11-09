from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class MCPConfig(BaseModel):
    """Configuration for the Docling MCP server."""

    transport: Literal["stdio", "sse", "streamable-http"] = "sse"
    host: str = "0.0.0.0"
    port: int = 8077
    tools: List[str] = Field(default_factory=lambda: ["conversion", "generation", "manipulation"])


class ModelDownloadConfig(BaseModel):
    """Describes a downloadable model artefact."""

    name: str
    type: Literal["huggingface", "modelscope"] = "huggingface"
    repo_id: Optional[str] = None
    revision: Optional[str] = None
    local_dir: Optional[str] = None
    allow_patterns: Optional[List[str]] = None
    ignore_patterns: Optional[List[str]] = None
    files: Optional[List[str]] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class ModelGroupConfig(BaseModel):
    """Describes a predefined Docling model bundle to download."""

    name: Literal[
        "layout",
        "tableformer",
        "code_formula",
        "picture_classifier",
        "rapidocr",
        "easyocr",
        "smolvlm",
        "granitedocling",
        "granitedocling_mlx",
        "smoldocling",
        "smoldocling_mlx",
        "granite_vision",
    ]
    enabled: bool = True
    backends: List[Literal["onnxruntime", "torch"]] = Field(default_factory=list)


class ModelCacheConfig(BaseModel):
    """Model cache and download configuration."""

    base_dir: Path = Path("/opt/docling-mcp/models")
    groups: List[ModelGroupConfig] = Field(
        default_factory=lambda: [
            ModelGroupConfig(name="layout"),
            ModelGroupConfig(name="tableformer"),
            ModelGroupConfig(name="code_formula"),
            ModelGroupConfig(name="picture_classifier"),
            ModelGroupConfig(name="rapidocr", backends=["onnxruntime"]),
        ]
    )
    downloads: List[ModelDownloadConfig] = Field(default_factory=list)


class RapidOCRConfig(BaseModel):
    """RapidOCR backend configuration."""

    enabled: bool = True
    backend: Literal["onnxruntime", "openvino", "paddle", "torch"] = "onnxruntime"
    providers: List[str] = Field(
        default_factory=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]
    )
    repo_id: Optional[str] = "RapidAI/RapidOCR"
    revision: Optional[str] = None
    det_model_path: Optional[str] = "RapidOcr/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_infer.onnx"
    rec_model_path: Optional[str] = "RapidOcr/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_infer.onnx"
    cls_model_path: Optional[str] = "RapidOcr/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_infer.onnx"
    rec_keys_path: Optional[str] = (
        "RapidOcr/paddle/PP-OCRv4/rec/ch_PP-OCRv4_rec_infer/ppocr_keys_v1.txt"
    )
    rapidocr_params: Dict[str, Any] = Field(default_factory=dict)


class EasyOCRConfig(BaseModel):
    """EasyOCR backend configuration."""

    enabled: bool = False
    languages: List[str] = Field(default_factory=lambda: ["en"])
    gpu: Literal["auto", "cuda", "cpu"] = "auto"
    recog_network: Optional[str] = "standard"
    model_storage_dir: Optional[str] = "EasyOcr"
    download_enabled: bool = True
    extra: Dict[str, Any] = Field(default_factory=dict)


class TesseractConfig(BaseModel):
    """Tesseract backend configuration."""

    enabled: bool = False
    languages: List[str] = Field(default_factory=lambda: ["eng"])
    tessdata_prefix: Optional[str] = None
    psm: Optional[int] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class OnnxTRConfig(BaseModel):
    """OnnxTR backend configuration."""

    enabled: bool = False
    repo_id: Optional[str] = None
    revision: Optional[str] = None
    det_model_path: Optional[str] = None
    rec_model_path: Optional[str] = None
    cls_model_path: Optional[str] = None
    providers: List[str] = Field(
        default_factory=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]
    )
    extra: Dict[str, Any] = Field(default_factory=dict)


class OCRConfig(BaseModel):
    """Unified OCR configuration."""

    backend: Literal["rapidocr", "easyocr", "tesseract", "tesseract_cli", "onnxtr", "none"] = (
        "rapidocr"
    )
    languages: List[str] = Field(default_factory=lambda: ["eng"])
    force_full_page_ocr: bool = False
    rapidocr: RapidOCRConfig = Field(default_factory=RapidOCRConfig)
    easyocr: EasyOCRConfig = Field(default_factory=EasyOCRConfig)
    tesseract: TesseractConfig = Field(default_factory=TesseractConfig)
    onnxtr: OnnxTRConfig = Field(default_factory=OnnxTRConfig)


class ConverterConfig(BaseModel):
    """Configuration for Docling converter behaviour."""

    keep_images: bool = False
    prefer_markdown_output: bool = True
    fallback_plain_text: bool = True
    image_ocr_enabled: bool = True
    generate_page_images: bool = False
    ocr: OCRConfig = Field(default_factory=OCRConfig)


class ContainerConfig(BaseModel):
    """Root configuration consumed by the container runtime."""

    log_level: str = "INFO"
    startup_sync: bool = True
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    converter: ConverterConfig = Field(default_factory=ConverterConfig)
    model_cache: ModelCacheConfig = Field(default_factory=ModelCacheConfig)


DEFAULT_CONFIG = ContainerConfig()


def load_config(path: str | Path) -> ContainerConfig:
    """Load configuration from JSON or YAML. Returns defaults when the file is missing."""
    path = Path(path)
    if not path.exists():
        return DEFAULT_CONFIG.copy(deep=True)

    raw: Dict[str, Any]
    try:
        text = path.read_text(encoding="utf-8")
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            raw = yaml.safe_load(text) or {}
    except Exception as exc:
        raise RuntimeError(f"Failed to read Docling config at {path}: {exc}") from exc

    try:
        return ContainerConfig.model_validate(raw)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid Docling configuration: {exc}") from exc


def ensure_config_file(path: str | Path) -> Path:
    """Write default configuration when the file does not exist."""
    path = Path(path)
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    data = DEFAULT_CONFIG.model_dump(mode="json", by_alias=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
