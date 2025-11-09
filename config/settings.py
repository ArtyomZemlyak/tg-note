"""
Application Settings
Loads configuration from multiple sources with priority:
1. YAML file (config.yaml) - all settings except credentials
2. .env file - credentials and overrides
3. CLI arguments (future)
4. Environment variables - highest priority
"""

import os
import sys
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Literal, Optional, Set, Tuple, Type, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import YamlConfigSettingsSource


class CliSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source for CLI arguments (future implementation)"""

    def __init__(self, settings_cls: Type[BaseSettings]):
        super().__init__(settings_cls)
        self._cli_args: Dict[str, Any] = {}
        # Parse CLI args in the future
        # For now, return empty dict

    def get_field_value(self, field_name: str, field_info: Any) -> Tuple[Any, str, bool]:
        """Get field value from CLI args"""
        if field_name in self._cli_args:
            return self._cli_args[field_name], field_name, False
        return None, field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        """Prepare the field value"""
        return value

    def __call__(self) -> Dict[str, Any]:
        """Return all CLI args"""
        return self._cli_args


class EnvOverridesSource(PydanticBaseSettingsSource):
    """Custom env source to handle special parsing cases.

    Specifically fixes JSON decoding errors for complex types when env vars are
    empty strings or comma-separated values (common in Docker Compose).
    """

    def __init__(self, settings_cls: Type[BaseSettings]):
        super().__init__(settings_cls)

    def get_field_value(self, field_name: str, field_info: Any) -> Tuple[Any, str, bool]:
        """Return per-field override from environment with robust parsing.

        Only handles `ALLOWED_USER_IDS`; other fields are ignored.
        """
        import json
        import os

        if field_name != "ALLOWED_USER_IDS":
            return None, field_name, False

        raw_allowed = os.environ.get("ALLOWED_USER_IDS")
        if raw_allowed is None:
            return None, field_name, False

        value = raw_allowed.strip()
        if value == "":
            return [], field_name, False

        try:
            if value.startswith("["):
                parsed = json.loads(value)
                return [int(x) for x in parsed], field_name, False
            else:
                return (
                    [int(uid.strip()) for uid in value.split(",") if uid.strip()],
                    field_name,
                    False,
                )
        except Exception:
            # Fallback to robust comma-splitting
            return [int(uid.strip()) for uid in value.split(",") if uid.strip()], field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> Dict[str, Any]:
        import json
        import os

        result: Dict[str, Any] = {}

        # Handle ALLOWED_USER_IDS from environment in a resilient way
        raw_allowed = os.environ.get("ALLOWED_USER_IDS")
        if raw_allowed is not None:
            value = raw_allowed.strip()
            if value == "":
                # Empty string means no restriction
                result["ALLOWED_USER_IDS"] = []
            else:
                # Try JSON first if it looks like JSON, otherwise treat as comma-separated
                try:
                    if value.startswith("["):
                        parsed = json.loads(value)
                        result["ALLOWED_USER_IDS"] = [int(x) for x in parsed]
                    else:
                        result["ALLOWED_USER_IDS"] = [
                            int(uid.strip()) for uid in value.split(",") if uid.strip()
                        ]
                except Exception:
                    # Fallback to robust comma-splitting
                    result["ALLOWED_USER_IDS"] = [
                        int(uid.strip()) for uid in value.split(",") if uid.strip()
                    ]

        return result


class DoclingMCPSettings(BaseModel):
    """Docling MCP integration configuration."""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(
        default=True,
        description="Enable Docling MCP integration when Docling backend is set to 'mcp'.",
    )
    server_name: str = Field(
        default="docling",
        description="Logical name for the Docling MCP server within the registry.",
    )
    transport: Literal["stdio", "sse"] = Field(
        default="sse",
        description="Transport type for connecting to the Docling MCP server.",
    )
    url: Optional[str] = Field(
        default=None,
        description="Explicit URL for Docling MCP server (used when transport is 'sse').",
    )
    docker_url: str = Field(
        default="http://docling-mcp:8077/sse",
        description="Default Docling MCP URL to use when running inside Docker (auto-detected).",
    )
    host_url: str = Field(
        default="http://127.0.0.1:8077/sse",
        description="Default Docling MCP URL to use when running on the host machine.",
    )
    command: Optional[str] = Field(
        default=None, description="Command to launch Docling MCP server when using stdio transport."
    )
    args: List[str] = Field(
        default_factory=list,
        description="Command arguments for launching Docling MCP server (stdio transport).",
    )
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to include when launching Docling MCP via stdio.",
    )
    listen_host: str = Field(
        default="0.0.0.0", description="Host interface for the Docling MCP container."
    )
    listen_port: int = Field(default=8077, description="Port for the Docling MCP container.")
    working_dir: Optional[str] = Field(
        default=None,
        description="Working directory for launching Docling MCP server (stdio transport).",
    )
    timeout: Optional[int] = Field(
        default=None, description="Optional per-server timeout override for Docling MCP requests."
    )
    tool_name: str = Field(
        default="convert_document_from_content",
        description=(
            "Preferred Docling MCP tool name. When not found, auto-detection will attempt to "
            "select a compatible tool."
        ),
    )
    auto_detect_tool: bool = Field(
        default=True,
        description="Attempt to auto-detect Docling tool if the configured tool is unavailable.",
    )
    argument_hints: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Optional map of semantic placeholders to Docling tool argument names "
            "(e.g., {'content': 'file_content'})."
        ),
    )
    extra_arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional static arguments forwarded to Docling MCP tool calls.",
    )
    tool_groups: List[str] = Field(
        default_factory=lambda: ["conversion", "generation", "manipulation"],
        description=(
            "List of Docling MCP tool groups to enable in the container "
            "(conversion, generation, manipulation, llama-index-rag, llama-stack-rag, llama-stack-ie)."
        ),
    )

    def resolve_url(self) -> Optional[str]:
        """Resolve the effective MCP URL for Docling based on configuration and environment."""
        if self.transport != "sse":
            return None

        if self.url:
            return self.url

        env_url = os.getenv("DOCLING_MCP_URL")
        if env_url:
            return env_url

        try:
            if Path("/.dockerenv").exists():
                return self.docker_url
        except Exception:
            # Fallback to host URL when detection fails
            pass

        return self.host_url


class DoclingModelDownloadSettings(BaseModel):
    """Model artefact download configuration for Docling container."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(
        default="rapidocr-default", description="Friendly name for the download entry."
    )
    type: Literal["huggingface", "modelscope"] = Field(
        default="huggingface", description="Downloader backend to use."
    )
    repo_id: Optional[str] = Field(
        default=None, description="Repository identifier (HuggingFace or ModelScope)."
    )
    revision: Optional[str] = Field(default=None, description="Optional repo revision/tag.")
    local_dir: Optional[str] = Field(
        default=None,
        description="Directory inside the container models volume to place artefacts (relative).",
    )
    allow_patterns: List[str] = Field(
        default_factory=list,
        description="Glob patterns of files to download (include list).",
    )
    ignore_patterns: List[str] = Field(
        default_factory=list,
        description="Glob patterns of files to skip during download.",
    )
    files: List[str] = Field(
        default_factory=list,
        description="Explicit list of files to download (alternative to allow_patterns).",
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict, description="Extra backend-specific download parameters."
    )


class DoclingModelGroupSettings(BaseModel):
    """Predefined Docling model bundle download configuration."""

    model_config = ConfigDict(extra="allow")

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
    ] = Field(default="rapidocr", description="Name of the Docling model bundle to ensure.")
    enabled: bool = Field(default=True, description="Whether this model group should be processed.")
    backends: List[Literal["onnxruntime", "torch"]] = Field(
        default_factory=list,
        description="Optional RapidOCR backends to download. Ignored for other groups.",
    )


class DoclingModelCacheSettings(BaseModel):
    """Model cache configuration for Docling container."""

    model_config = ConfigDict(extra="allow")

    base_dir: str = Field(
        default="/opt/docling-mcp/models",
        description="Default models directory inside the container.",
    )
    groups: List[DoclingModelGroupSettings] = Field(
        default_factory=lambda: [
            DoclingModelGroupSettings(name="layout"),
            DoclingModelGroupSettings(name="tableformer"),
            DoclingModelGroupSettings(name="code_formula"),
            DoclingModelGroupSettings(name="picture_classifier"),
            DoclingModelGroupSettings(name="rapidocr", backends=["onnxruntime"]),
        ],
        description="Predefined Docling model bundles to download using built-in helpers.",
    )
    downloads: List[DoclingModelDownloadSettings] = Field(
        default_factory=list,
        description="Custom model artefacts to download in addition to predefined bundles.",
    )


class DoclingRapidOCRSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=True, description="Enable RapidOCR pipeline.")
    backend: Literal["onnxruntime", "openvino", "paddle", "torch"] = Field(
        default="onnxruntime", description="RapidOCR backend type."
    )
    providers: List[str] = Field(
        default_factory=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"],
        description="Preferred ONNX runtime providers.",
    )
    repo_id: Optional[str] = Field(
        default="RapidAI/RapidOCR", description="Repository used for RapidOCR models."
    )
    revision: Optional[str] = Field(default=None, description="Optional RapidOCR repo revision.")
    det_model_path: Optional[str] = Field(
        default="RapidOcr/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_infer.onnx",
        description="Detector model path relative to models base.",
    )
    rec_model_path: Optional[str] = Field(
        default="RapidOcr/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_infer.onnx",
        description="Recognizer model path relative to models base.",
    )
    cls_model_path: Optional[str] = Field(
        default="RapidOcr/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_infer.onnx",
        description="Classifier model path relative to models base.",
    )
    rec_keys_path: Optional[str] = Field(
        default="RapidOcr/paddle/PP-OCRv4/rec/ch_PP-OCRv4_rec_infer/ppocr_keys_v1.txt",
        description="Optional keys file for recognition.",
    )
    rapidocr_params: Dict[str, Any] = Field(
        default_factory=dict, description="Additional RapidOCR parameters."
    )


class DoclingEasyOCRSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="Enable EasyOCR backend.")
    languages: List[str] = Field(
        default_factory=lambda: ["en"], description="EasyOCR language codes."
    )
    gpu: Literal["auto", "cuda", "cpu"] = Field(
        default="auto", description="Preferred EasyOCR device."
    )
    recog_network: Optional[str] = Field(
        default="standard", description="EasyOCR recognition network."
    )
    model_storage_dir: Optional[str] = Field(
        default="EasyOcr",
        description="Override model storage directory relative to container base.",
    )
    download_enabled: bool = Field(
        default=True, description="Allow EasyOCR to download missing models."
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict, description="Additional EasyOCR reader parameters."
    )


class DoclingTesseractSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="Enable Tesseract (tesserocr) backend.")
    languages: List[str] = Field(
        default_factory=lambda: ["eng"], description="Language packs for Tesseract."
    )
    tessdata_prefix: Optional[str] = Field(
        default=None,
        description="Optional custom tessdata directory path.",
    )
    psm: Optional[int] = Field(
        default=None,
        description="Tesseract page segmentation mode.",
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict, description="Additional options for the backend."
    )


class DoclingOnnxtrSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="Enable Docling OnnxTR OCR backend.")
    repo_id: Optional[str] = Field(
        default=None, description="Model repository for OnnxTR artefacts."
    )
    revision: Optional[str] = Field(default=None, description="Optional OnnxTR repo revision.")
    det_model_path: Optional[str] = Field(
        default=None, description="Detector model path relative to models base."
    )
    rec_model_path: Optional[str] = Field(
        default=None, description="Recognizer model path relative to models base."
    )
    cls_model_path: Optional[str] = Field(
        default=None, description="Classifier model path relative to models base."
    )
    providers: List[str] = Field(
        default_factory=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"],
        description="Preferred providers for OnnxTR onnxruntime.",
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict, description="Additional backend parameters."
    )


class DoclingOCRSettings(BaseModel):
    """Unified OCR configuration for Docling."""

    model_config = ConfigDict(extra="allow")

    backend: Literal["rapidocr", "easyocr", "tesseract", "tesseract_cli", "onnxtr", "none"] = Field(
        default="rapidocr", description="Primary OCR backend to use."
    )
    languages: List[str] = Field(
        default_factory=list,
        description="Override OCR languages (falls back to DoclingSettings.ocr_languages when empty).",
    )
    force_full_page_ocr: bool = Field(
        default=False,
        description="Force OCR on full pages even when vector text is available.",
    )
    rapidocr: DoclingRapidOCRSettings = Field(
        default_factory=DoclingRapidOCRSettings, description="RapidOCR backend configuration."
    )
    easyocr: DoclingEasyOCRSettings = Field(
        default_factory=DoclingEasyOCRSettings, description="EasyOCR backend configuration."
    )
    tesseract: DoclingTesseractSettings = Field(
        default_factory=DoclingTesseractSettings, description="Tesseract backend configuration."
    )
    onnxtr: DoclingOnnxtrSettings = Field(
        default_factory=DoclingOnnxtrSettings, description="OnnxTR backend configuration."
    )


class DoclingSettings(BaseModel):
    """Docling-specific media processing configuration."""

    model_config = ConfigDict(extra="allow")

    IMAGE_FORMATS: ClassVar[Set[str]] = {"jpg", "jpeg", "png", "tiff"}

    backend: Literal["mcp", "local"] = Field(
        default="mcp",
        description="Select Docling backend: 'mcp' for MCP server, 'local' for in-process library.",
    )
    enabled: bool = Field(
        default=True,
        description="Enable Docling media processing when media processing is enabled.",
    )
    formats: List[str] = Field(
        default_factory=lambda: [
            "pdf",
            "docx",
            "pptx",
            "xlsx",
            "html",
            "md",
            "txt",
            "jpg",
            "jpeg",
            "png",
            "tiff",
        ],
        description="File formats handled by Docling.",
    )
    max_file_size_mb: int = Field(
        default=25,
        ge=0,
        description="Maximum file size (in megabytes) to process with Docling. Set to 0 for no limit.",
    )
    prefer_markdown_output: bool = Field(
        default=True,
        description="Prefer Markdown export when converting documents.",
    )
    fallback_plain_text: bool = Field(
        default=True,
        description="Fallback to plain text export if Markdown export is not available.",
    )
    image_ocr_enabled: bool = Field(
        default=True,
        description="Enable OCR for image formats (jpg/jpeg/png/tiff). When disabled, image formats are skipped.",
    )
    ocr_languages: List[str] = Field(
        default_factory=lambda: ["eng"],
        description="Preferred OCR languages (ISO 639-3 codes) passed to Docling when supported.",
    )
    mcp: DoclingMCPSettings = Field(
        default_factory=DoclingMCPSettings,
        description="Docling MCP integration settings.",
    )
    keep_images: bool = Field(
        default=False,
        description="Keep generated page images in Docling output when supported.",
    )
    generate_page_images: bool = Field(
        default=False,
        description="Generate page images during conversion (may increase processing time).",
    )
    startup_sync: bool = Field(
        default=True,
        description="Automatically synchronise Docling models in the container on startup.",
    )
    ocr_config: DoclingOCRSettings = Field(
        default_factory=DoclingOCRSettings,
        description="Detailed OCR backend configuration for the Docling container.",
    )
    model_cache: DoclingModelCacheSettings = Field(
        default_factory=DoclingModelCacheSettings,
        description="Model download instructions for the Docling container.",
    )

    @field_validator("formats", mode="before")
    @classmethod
    def _normalize_formats(cls, value: Any) -> List[str]:
        """Normalize list/delimited string of formats to unique lowercase list."""
        if value is None:
            return []

        if isinstance(value, str):
            candidates = [item.strip() for item in value.split(",") if item.strip()]
        elif isinstance(value, (set, tuple, list)):
            candidates = [str(item).strip() for item in value if str(item).strip()]
        else:
            candidates = [str(value).strip()]

        normalized: List[str] = []
        seen: Set[str] = set()
        for candidate in candidates:
            fmt = candidate.lower()
            if fmt and fmt not in seen:
                seen.add(fmt)
                normalized.append(fmt)
        return normalized

    @field_validator("ocr_languages", mode="before")
    @classmethod
    def _normalize_languages(cls, value: Any) -> List[str]:
        """Normalize OCR languages to lowercase list."""
        if value is None:
            return ["eng"]

        explicit_empty_sequence = isinstance(value, (list, tuple, set)) and not value

        if isinstance(value, str):
            candidates = [item.strip() for item in value.split(",") if item.strip()]
        elif isinstance(value, (set, tuple, list)):
            candidates = [str(item).strip() for item in value if str(item).strip()]
        else:
            candidates = [str(value).strip()]

        normalized: List[str] = []
        seen: Set[str] = set()
        for candidate in candidates:
            lang = candidate.lower()
            if lang and lang not in seen:
                seen.add(lang)
                normalized.append(lang)
        if normalized:
            return normalized
        if explicit_empty_sequence:
            return []
        return ["eng"]

    @property
    def max_file_size_bytes(self) -> Optional[int]:
        """Return file size limit in bytes or None if unlimited."""
        if self.max_file_size_mb <= 0:
            return None
        return self.max_file_size_mb * 1024 * 1024

    def normalized_formats(self) -> List[str]:
        """Return normalized formats list."""
        return list(self.formats)

    def get_enabled_formats(self) -> List[str]:
        """Return formats enabled after applying OCR/image constraints."""
        if not self.enabled:
            return []

        if self.image_ocr_enabled:
            return list(self.formats)

        return [fmt for fmt in self.formats if not self.is_image_format(fmt)]

    def is_image_format(self, fmt: str) -> bool:
        """Check if format is considered an image format."""
        return fmt.lower() in self.IMAGE_FORMATS

    def is_format_enabled(self, fmt: str) -> bool:
        """Check if requested format is enabled under current configuration."""
        if not self.enabled:
            return False

        normalized = fmt.lower().lstrip(".")
        if normalized not in self.formats:
            return False

        if not self.image_ocr_enabled and self.is_image_format(normalized):
            return False

        return True

    def exceeds_size_limit(self, file_size_bytes: int) -> bool:
        """Check if file size is above configured limit."""
        limit = self.max_file_size_bytes
        return limit is not None and file_size_bytes > limit

    def use_mcp(self) -> bool:
        """Return True when Docling MCP backend should be used."""
        return self.backend == "mcp" and self.enabled and self.mcp.enabled

    def use_local(self) -> bool:
        """Return True when local Docling backend should be used."""
        return self.backend == "local" and self.enabled

    def resolved_mcp_url(self) -> Optional[str]:
        """Return resolved Docling MCP URL when using MCP backend."""
        if not self.use_mcp():
            return None
        return self.mcp.resolve_url()

    def to_container_config(self, log_level: str = "INFO") -> Dict[str, Any]:
        """Convert settings to container-friendly configuration structure."""
        languages = self.ocr_config.languages or self.ocr_languages
        ocr_section = {
            "backend": self.ocr_config.backend,
            "languages": list(languages),
            "force_full_page_ocr": self.ocr_config.force_full_page_ocr,
            "rapidocr": self.ocr_config.rapidocr.model_dump(mode="json", exclude_none=True),
            "easyocr": self.ocr_config.easyocr.model_dump(mode="json", exclude_none=True),
            "tesseract": self.ocr_config.tesseract.model_dump(mode="json", exclude_none=True),
            "onnxtr": self.ocr_config.onnxtr.model_dump(mode="json", exclude_none=True),
        }

        downloads = [
            download.model_dump(mode="json", exclude_none=True)
            for download in self.model_cache.downloads
        ]
        groups = [
            group.model_dump(mode="json", exclude_none=True) for group in self.model_cache.groups
        ]

        return {
            "log_level": log_level,
            "startup_sync": self.startup_sync,
            "mcp": {
                "transport": self.mcp.transport,
                "host": self.mcp.listen_host,
                "port": self.mcp.listen_port,
                "tools": list(self.mcp.tool_groups),
            },
            "converter": {
                "keep_images": self.keep_images,
                "prefer_markdown_output": self.prefer_markdown_output,
                "fallback_plain_text": self.fallback_plain_text,
                "image_ocr_enabled": self.image_ocr_enabled,
                "generate_page_images": self.generate_page_images,
                "ocr": ocr_section,
            },
            "model_cache": {
                "base_dir": self.model_cache.base_dir,
                "groups": groups,
                "downloads": downloads,
            },
        }


class Settings(BaseSettings):
    """Application settings loaded from multiple sources"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        yaml_file="config.yaml",  # Custom config for YAML file path
    )

    # Telegram Bot Settings (credentials - not in YAML)
    TELEGRAM_BOT_TOKEN: str = Field(
        default="", description="Telegram bot token (from .env or env vars only)"
    )
    ALLOWED_USER_IDS: List[int] = Field(
        default_factory=list, description="Comma-separated list of allowed user IDs"
    )

    # Agent System Settings (credentials - not in YAML)
    OPENAI_API_KEY: Optional[str] = Field(
        default=None, description="OpenAI API key (from .env or env vars only)"
    )
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None, description="Anthropic API key (from .env or env vars only)"
    )
    QWEN_API_KEY: Optional[str] = Field(
        default=None, description="Qwen API key (from .env or env vars only)"
    )
    OPENAI_BASE_URL: Optional[str] = Field(
        default=None,
        description="OpenAI API base URL for custom endpoints (from .env or env vars only)",
    )
    GITHUB_TOKEN: Optional[str] = Field(
        default=None, description="GitHub personal access token (from .env or env vars only)"
    )
    GITHUB_USERNAME: Optional[str] = Field(
        default=None,
        description="GitHub username for HTTPS authentication (from .env or env vars only)",
    )
    GITLAB_TOKEN: Optional[str] = Field(
        default=None, description="GitLab personal access token (from .env or env vars only)"
    )
    GITLAB_USERNAME: Optional[str] = Field(
        default=None,
        description="GitLab username for HTTPS authentication (from .env or env vars only)",
    )

    # Agent Configuration (can be in YAML)
    AGENT_TYPE: str = Field(
        default="stub", description="Agent type: stub, qwen_code, qwen_code_cli"
    )
    AGENT_QWEN_CLI_PATH: str = Field(default="qwen", description="Path to qwen CLI executable")
    AGENT_TIMEOUT: int = Field(default=300, description="Timeout in seconds for agent operations")
    AGENT_MODEL: str = Field(
        default="qwen-max", description="Model to use for agent (e.g., qwen-max, qwen-plus)"
    )
    AGENT_INSTRUCTION: Optional[str] = Field(
        default=None, description="Custom instruction for the agent"
    )
    AGENT_ENABLE_WEB_SEARCH: bool = Field(
        default=True, description="Enable web search tool for agent"
    )
    AGENT_ENABLE_GIT: bool = Field(default=True, description="Enable git command tool for agent")
    AGENT_ENABLE_GITHUB: bool = Field(default=True, description="Enable GitHub API tool for agent")
    AGENT_ENABLE_SHELL: bool = Field(
        default=False, description="Enable shell command tool for agent (security risk)"
    )
    AGENT_ENABLE_FILE_MANAGEMENT: bool = Field(
        default=True, description="Enable file operations (create, edit, delete, move files)"
    )
    AGENT_ENABLE_FOLDER_MANAGEMENT: bool = Field(
        default=True, description="Enable folder operations (create, delete, move folders)"
    )

    # MCP (Model Context Protocol) Settings (can be in YAML)
    AGENT_ENABLE_MCP: bool = Field(
        default=False, description="Enable MCP (Model Context Protocol) tools"
    )
    AGENT_ENABLE_MCP_MEMORY: bool = Field(
        default=False, description="Enable MCP memory agent tool (local memory via HTTP)"
    )
    MCP_TIMEOUT: int = Field(
        default=600, description="Timeout in seconds for MCP requests (default: 600 seconds)"
    )

    # Memory Agent Settings (can be in YAML)
    MEM_AGENT_STORAGE_TYPE: str = Field(
        default="json",
        description="Memory storage type: json (simple, fast) or vector (AI-powered semantic search)",
    )
    MEM_AGENT_MODEL: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace model ID for embeddings (used with 'vector' storage type)",
    )
    MEM_AGENT_MODEL_PRECISION: str = Field(
        default="4bit", description="Model precision: 4bit, 8bit, or fp16"
    )
    MEM_AGENT_BACKEND: str = Field(
        default="auto", description="Backend to use: auto, vllm, mlx, or transformers"
    )
    MEM_AGENT_BASE_URL: Optional[str] = Field(
        default=None, description="OpenAI-compatible endpoint URL (e.g., http://localhost:8001/v1)"
    )
    MEM_AGENT_OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for mem-agent endpoint (use 'lm-studio' for local servers)",
    )
    MEM_AGENT_MAX_TOOL_TURNS: int = Field(
        default=20, description="Maximum number of tool execution turns"
    )
    MEM_AGENT_TIMEOUT: int = Field(
        default=20, description="Timeout for sandboxed code execution (seconds)"
    )
    MEM_AGENT_FILE_SIZE_LIMIT: int = Field(
        default=1024 * 1024, description="Maximum file size in bytes"  # 1MB
    )
    MEM_AGENT_DIR_SIZE_LIMIT: int = Field(
        default=1024 * 1024 * 10, description="Maximum directory size in bytes"  # 10MB
    )
    MEM_AGENT_MEMORY_SIZE_LIMIT: int = Field(
        default=1024 * 1024 * 100, description="Maximum total memory size in bytes"  # 100MB
    )

    # OpenRouter API Key (for backward compatibility)
    OPENROUTER_API_KEY: Optional[str] = Field(
        default=None, description="OpenRouter API key (for backward compatibility)"
    )

    # Vector Search Settings (can be in YAML)
    VECTOR_SEARCH_ENABLED: bool = Field(
        default=False, description="Enable vector search for knowledge base"
    )

    # Embedding Model Settings
    VECTOR_EMBEDDING_PROVIDER: str = Field(
        default="sentence_transformers",
        description="Embedding provider: sentence_transformers, openai, infinity",
    )
    VECTOR_EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model name"
    )
    VECTOR_INFINITY_API_URL: Optional[str] = Field(
        default="http://localhost:7997", description="Infinity API URL (for infinity provider)"
    )
    VECTOR_INFINITY_API_KEY: Optional[str] = Field(
        default=None, description="Infinity API key (from .env or env vars only)"
    )

    # Vector Store Settings
    VECTOR_STORE_PROVIDER: str = Field(
        default="faiss", description="Vector store provider: faiss, qdrant"
    )
    VECTOR_QDRANT_URL: Optional[str] = Field(
        default="http://localhost:6333", description="Qdrant API URL (for qdrant provider)"
    )
    VECTOR_QDRANT_API_KEY: Optional[str] = Field(
        default=None, description="Qdrant API key (from .env or env vars only)"
    )
    VECTOR_QDRANT_COLLECTION: str = Field(
        default="knowledge_base", description="Qdrant collection name"
    )

    # Chunking Settings
    VECTOR_CHUNKING_STRATEGY: str = Field(
        default="fixed_size_overlap",
        description="Chunking strategy: fixed_size, fixed_size_overlap, semantic",
    )
    VECTOR_CHUNK_SIZE: int = Field(default=512, description="Chunk size in characters")
    VECTOR_CHUNK_OVERLAP: int = Field(
        default=50, description="Overlap between chunks (for fixed_size_overlap)"
    )
    VECTOR_RESPECT_HEADERS: bool = Field(
        default=True, description="Respect markdown headers when chunking (for semantic strategy)"
    )

    # Search Settings
    VECTOR_SEARCH_TOP_K: int = Field(
        default=5, description="Number of results to return in vector search"
    )

    # Knowledge Base Settings (can be in YAML)
    KB_PATH: Path = Field(
        default=Path("./knowledge_base"), description="Root directory for all knowledge bases"
    )
    KB_TOPICS_ONLY: bool = Field(
        default=True, description="Restrict agents to work only in topics/ folder"
    )
    KB_GIT_ENABLED: bool = Field(default=True, description="Enable Git operations")
    KB_GIT_AUTO_PUSH: bool = Field(default=True, description="Auto-push to remote")
    KB_GIT_REMOTE: str = Field(default="origin", description="Git remote name")
    KB_GIT_BRANCH: str = Field(default="main", description="Git branch name")

    # Conversation Context Settings (can be in YAML)
    CONTEXT_ENABLED: bool = Field(
        default=True, description="Enable conversation context for agents"
    )
    CONTEXT_MAX_TOKENS: int = Field(
        default=2000, description="Maximum number of tokens to keep in context"
    )

    # Processing Settings (can be in YAML)
    MESSAGE_GROUP_TIMEOUT: int = Field(
        default=30, description="Message grouping timeout in seconds"
    )
    PROCESSED_LOG_PATH: Path = Field(
        default=Path("./data/processed.json"), description="Path to processed messages log"
    )

    # Rate Limiting Settings (can be in YAML)
    RATE_LIMIT_ENABLED: bool = Field(
        default=True, description="Enable rate limiting for agent calls"
    )
    RATE_LIMIT_MAX_REQUESTS: int = Field(
        default=20, description="Maximum agent requests per user per time window"
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60, description="Rate limit time window in seconds"
    )

    # Health Check Settings (can be in YAML)
    HEALTH_CHECK_INTERVAL: int = Field(
        default=30, description="Interval between health checks in seconds"
    )
    HEALTH_CHECK_MAX_FAILURES: int = Field(
        default=5, description="Maximum consecutive health check failures before giving up"
    )

    # Logging Settings (can be in YAML)
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: Optional[Path] = Field(default=Path("./logs/bot.log"), description="Log file path")

    # Media Processing Settings (can be in YAML)
    MEDIA_PROCESSING_ENABLED: bool = Field(
        default=True, description="Enable media file processing (master switch)"
    )
    MEDIA_PROCESSING_DOCLING: DoclingSettings = Field(
        default_factory=DoclingSettings,
        description="Docling-specific media processing configuration",
    )
    MEDIA_PROCESSING_DOCLING_FORMATS: Optional[List[str]] = Field(
        default=None,
        description="Deprecated Docling formats list (use MEDIA_PROCESSING_DOCLING.formats instead)",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize the sources and their priority.

        Priority order (highest priority first):
        1. Environment variables (env_settings) - highest priority
        2. CLI arguments (cli_settings)
        3. .env file (dotenv_settings)
        4. YAML file (yaml_settings)
        5. Default values (init_settings) - lowest priority

        Note: In Pydantic, the FIRST source to find a value wins!
        So we return sources in order from highest to lowest priority.
        """
        # Get YAML file path from config
        yaml_file = Path(settings_cls.model_config.get("yaml_file", "config.yaml"))

        # Create custom sources
        yaml_settings = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file)
        cli_settings = CliSettingsSource(settings_cls)
        env_overrides = EnvOverridesSource(settings_cls)

        # Return sources in priority order (leftmost = highest priority)
        # AICODE-NOTE: Explicit constructor arguments (init_settings) MUST have the
        # highest priority so that direct instantiation like Settings(MEDIA_PROCESSING_ENABLED=False)
        # reliably overrides all other configuration sources.
        return (
            init_settings,  # Highest priority - explicit constructor args
            env_overrides,  # Then normalized env overrides
            env_settings,  # Then standard env vars
            cli_settings,  # Then CLI (reserved)
            dotenv_settings,  # Then .env file
            yaml_settings,  # Finally YAML config
        )

    @model_validator(mode="after")
    def _apply_legacy_docling_formats(self) -> "Settings":
        """Support legacy MEDIA_PROCESSING_DOCLING_FORMATS configuration."""
        legacy_formats = self.MEDIA_PROCESSING_DOCLING_FORMATS
        if legacy_formats is not None:
            docling_payload = self.MEDIA_PROCESSING_DOCLING.model_dump()
            docling_payload["formats"] = legacy_formats
            self.MEDIA_PROCESSING_DOCLING = DoclingSettings(**docling_payload)
        return self

    @field_validator("ALLOWED_USER_IDS", mode="before")
    @classmethod
    def parse_user_ids(cls, v) -> List[int]:
        """Parse comma-separated user IDs from string or return list"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
        return []

    @field_validator("KB_PATH", "PROCESSED_LOG_PATH", "LOG_FILE", mode="before")
    @classmethod
    def parse_path(cls, v) -> Optional[Path]:
        """Convert string to Path"""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return Path(v)
        return v

    def get_mem_agent_backend(self) -> str:
        """
        Determine the memory agent backend to use

        Returns:
            Backend name: vllm, mlx, or transformers
        """
        if self.MEM_AGENT_BACKEND != "auto":
            return self.MEM_AGENT_BACKEND

        # Auto-detect based on platform
        import sys

        if sys.platform == "darwin":
            # macOS - prefer MLX if available, otherwise transformers
            try:
                import mlx

                return "mlx"
            except ImportError:
                return "transformers"
        else:
            # Linux/Windows - prefer vLLM if available, otherwise transformers
            try:
                import vllm

                return "vllm"
            except ImportError:
                return "transformers"

    def get_mem_agent_model_path(self) -> Path:
        """
        Get the path where the mem-agent model will be cached

        Returns:
            Path to model cache
        """
        # Use HuggingFace cache directory
        import os

        cache_home = os.environ.get(
            "HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        )
        return Path(cache_home) / "hub" / f"models--{self.MEM_AGENT_MODEL.replace('/', '--')}"

    def get_mem_agent_memory_dir(self, user_id: int) -> Path:
        """
        Get memory directory for a specific user

        Args:
            user_id: User ID

        Returns:
            Full path to user's memory directory: data/memory/user_{user_id}
        """
        return Path(f"data/memory/user_{user_id}")

    def is_media_processing_enabled(self) -> bool:
        """
        Check if media processing is enabled globally

        Returns:
            True if media processing is enabled, False otherwise
        """
        return self.MEDIA_PROCESSING_ENABLED

    def get_media_processing_formats(self, processor: str = "docling") -> List[str]:
        """
        Get enabled file formats for a specific media processor

        Args:
            processor: Name of the processor (e.g., "docling")

        Returns:
            List of enabled file format extensions (empty list if processing is disabled)
        """
        # Check if media processing is enabled globally
        if not self.is_media_processing_enabled():
            return []

        if processor == "docling":
            if not self.MEDIA_PROCESSING_DOCLING.enabled:
                return []
            return self.MEDIA_PROCESSING_DOCLING.get_enabled_formats()
        # AICODE-NOTE: Add other processors here in the future
        return []

    def is_format_enabled(self, file_format: str, processor: str = "docling") -> bool:
        """
        Check if a specific file format is enabled for processing

        Args:
            file_format: File format/extension (e.g., "pdf", "jpg")
            processor: Name of the processor (default: "docling")

        Returns:
            True if the format is enabled and media processing is active, False otherwise
        """
        # Check if media processing is enabled globally
        if not self.is_media_processing_enabled():
            return False

        if processor == "docling":
            if not self.MEDIA_PROCESSING_DOCLING.enabled:
                return False
            return self.MEDIA_PROCESSING_DOCLING.is_format_enabled(file_format)

        formats = self.get_media_processing_formats(processor)
        return file_format.lower() in [fmt.lower() for fmt in formats]

    def ensure_mem_agent_memory_dir_exists(self, user_id: int) -> None:
        """
        Ensure memory directory exists for a specific user

        Args:
            user_id: User ID
        """
        memory_dir = self.get_mem_agent_memory_dir(user_id)
        memory_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> List[str]:
        """
        Validate settings comprehensively

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required credentials
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")

        # Timeout validations
        if self.AGENT_TIMEOUT <= 0:
            errors.append(f"AGENT_TIMEOUT must be positive, got {self.AGENT_TIMEOUT}")

        if self.MESSAGE_GROUP_TIMEOUT < 0:
            errors.append(
                f"MESSAGE_GROUP_TIMEOUT cannot be negative, got {self.MESSAGE_GROUP_TIMEOUT}"
            )

        if self.MEM_AGENT_TIMEOUT <= 0:
            errors.append(f"MEM_AGENT_TIMEOUT must be positive, got {self.MEM_AGENT_TIMEOUT}")

        if self.HEALTH_CHECK_INTERVAL <= 0:
            errors.append(
                f"HEALTH_CHECK_INTERVAL must be positive, got {self.HEALTH_CHECK_INTERVAL}"
            )

        # Rate limit validations
        if self.RATE_LIMIT_ENABLED:
            if self.RATE_LIMIT_MAX_REQUESTS <= 0:
                errors.append(
                    f"RATE_LIMIT_MAX_REQUESTS must be positive, got {self.RATE_LIMIT_MAX_REQUESTS}"
                )
            if self.RATE_LIMIT_WINDOW_SECONDS <= 0:
                errors.append(
                    f"RATE_LIMIT_WINDOW_SECONDS must be positive, got {self.RATE_LIMIT_WINDOW_SECONDS}"
                )

        # Path validations
        if self.KB_PATH:
            # Check if parent directory exists or can be created
            try:
                parent = self.KB_PATH.parent
                if not parent.exists():
                    # Try to create it to validate permissions
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        errors.append(
                            f"KB_PATH parent directory cannot be created: {parent}. Error: {e}"
                        )
            except Exception as e:
                errors.append(f"KB_PATH validation failed: {e}")

        if self.LOG_FILE:
            # Check if log directory can be created
            try:
                log_dir = self.LOG_FILE.parent
                if not log_dir.exists():
                    try:
                        log_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        errors.append(
                            f"LOG_FILE directory cannot be created: {log_dir}. Error: {e}"
                        )
            except Exception as e:
                errors.append(f"LOG_FILE validation failed: {e}")

        # Context validations
        if self.CONTEXT_MAX_TOKENS <= 0:
            errors.append(f"CONTEXT_MAX_TOKENS must be positive, got {self.CONTEXT_MAX_TOKENS}")

        # Vector search validations
        if self.VECTOR_SEARCH_ENABLED:
            if self.VECTOR_CHUNK_SIZE <= 0:
                errors.append(f"VECTOR_CHUNK_SIZE must be positive, got {self.VECTOR_CHUNK_SIZE}")
            if self.VECTOR_CHUNK_OVERLAP < 0:
                errors.append(
                    f"VECTOR_CHUNK_OVERLAP cannot be negative, got {self.VECTOR_CHUNK_OVERLAP}"
                )
            if self.VECTOR_CHUNK_OVERLAP >= self.VECTOR_CHUNK_SIZE:
                errors.append(
                    f"VECTOR_CHUNK_OVERLAP ({self.VECTOR_CHUNK_OVERLAP}) "
                    f"must be less than VECTOR_CHUNK_SIZE ({self.VECTOR_CHUNK_SIZE})"
                )
            if self.VECTOR_SEARCH_TOP_K <= 0:
                errors.append(
                    f"VECTOR_SEARCH_TOP_K must be positive, got {self.VECTOR_SEARCH_TOP_K}"
                )

        # File size validations
        if self.MEM_AGENT_FILE_SIZE_LIMIT <= 0:
            errors.append(
                f"MEM_AGENT_FILE_SIZE_LIMIT must be positive, got {self.MEM_AGENT_FILE_SIZE_LIMIT}"
            )
        if self.MEM_AGENT_DIR_SIZE_LIMIT <= 0:
            errors.append(
                f"MEM_AGENT_DIR_SIZE_LIMIT must be positive, got {self.MEM_AGENT_DIR_SIZE_LIMIT}"
            )
        if self.MEM_AGENT_MEMORY_SIZE_LIMIT <= 0:
            errors.append(
                f"MEM_AGENT_MEMORY_SIZE_LIMIT must be positive, got {self.MEM_AGENT_MEMORY_SIZE_LIMIT}"
            )

        # Log level validation
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of {valid_log_levels}, got {self.LOG_LEVEL}")

        return errors

    def __repr__(self) -> str:
        """String representation (hiding sensitive data)"""
        return (
            f"Settings(\n"
            f"  TELEGRAM_BOT_TOKEN={'*' * 10 if self.TELEGRAM_BOT_TOKEN else 'NOT_SET'},\n"
            f"  ALLOWED_USER_IDS={self.ALLOWED_USER_IDS},\n"
            f"  KB_PATH={self.KB_PATH},\n"
            f"  KB_GIT_ENABLED={self.KB_GIT_ENABLED},\n"
            f"  KB_GIT_AUTO_PUSH={self.KB_GIT_AUTO_PUSH},\n"
            f"  MESSAGE_GROUP_TIMEOUT={self.MESSAGE_GROUP_TIMEOUT}\n"
            f")"
        )


# Global settings instance
settings = Settings()


# ═══════════════════════════════════════════════════════════════════════════════
# Mem-Agent Helper Functions and Constants
# ═══════════════════════════════════════════════════════════════════════════════

import os

# Environment variable overrides for mem-agent (have priority over config)
MEM_AGENT_BASE_URL = os.getenv("MEM_AGENT_BASE_URL", settings.MEM_AGENT_BASE_URL)
MEM_AGENT_OPENAI_API_KEY = os.getenv("MEM_AGENT_OPENAI_API_KEY", settings.MEM_AGENT_OPENAI_API_KEY)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY)

# Mem-agent constants with environment variable overrides
MAX_TOOL_TURNS = int(os.getenv("MEM_AGENT_MAX_TOOL_TURNS", str(settings.MEM_AGENT_MAX_TOOL_TURNS)))
FILE_SIZE_LIMIT = int(
    os.getenv("MEM_AGENT_FILE_SIZE_LIMIT", str(settings.MEM_AGENT_FILE_SIZE_LIMIT))
)
DIR_SIZE_LIMIT = int(os.getenv("MEM_AGENT_DIR_SIZE_LIMIT", str(settings.MEM_AGENT_DIR_SIZE_LIMIT)))
MEMORY_SIZE_LIMIT = int(
    os.getenv("MEM_AGENT_MEMORY_SIZE_LIMIT", str(settings.MEM_AGENT_MEMORY_SIZE_LIMIT))
)
SANDBOX_TIMEOUT = int(os.getenv("MEM_AGENT_TIMEOUT", str(settings.MEM_AGENT_TIMEOUT)))
MEM_AGENT_MODEL = settings.MEM_AGENT_MODEL

# Memory path - will be set dynamically by the agent based on KB path
MEMORY_PATH = "memory"

# Path settings
SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "mcp"
    / "memory"
    / "mem_agent_impl"
    / "system_prompt.txt"
)
SAVE_CONVERSATION_PATH = Path("output/conversations/")


def get_memory_path(kb_path: Optional[Path] = None) -> Path:
    """
    Get the memory path for a specific knowledge base.

    Args:
        kb_path: Path to knowledge base. If None, uses default.

    Returns:
        Path to memory directory
    """
    if kb_path is None:
        return Path(MEMORY_PATH)
    return kb_path / MEMORY_PATH
