from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Type

# AICODE-NOTE: Initialize environment variables BEFORE any Docling imports
import tg_docling.env_setup  # noqa: F401
from pydantic import ValidationError

from config.settings import DoclingSettings, Settings

DEFAULT_SETTINGS_PATH = Path("/opt/docling-mcp/config.yaml")


def _container_settings_cls(yaml_path: Path) -> Type[Settings]:
    """
    Create a temporary Settings subclass that reads configuration from the provided YAML file.

    Settings.model_config is copied to avoid mutating global configuration used by the main app.
    """

    yaml_path = yaml_path.resolve()

    class ContainerSettings(Settings):  # type: ignore[misc, valid-type]
        model_config = {**Settings.model_config, "yaml_file": str(yaml_path)}

    return ContainerSettings


def load_app_settings(settings_path: Path | None = None) -> Settings:
    """
    Load full application settings inside the container using the shared YAML file.
    """

    resolved_path = Path(settings_path or os.getenv("DOCLING_SETTINGS_PATH", DEFAULT_SETTINGS_PATH))
    settings_cls = _container_settings_cls(resolved_path)

    try:
        return settings_cls()
    except ValidationError as exc:  # pragma: no cover - defensive, hard to trigger in tests
        raise RuntimeError(f"Failed to load tg-note settings from {resolved_path}: {exc}") from exc


def load_docling_settings(settings_path: Path | None = None) -> Tuple[DoclingSettings, Settings]:
    """
    Load Docling-specific configuration from the shared tg-note settings.

    Returns both the Docling settings section and the encompassing Settings instance so callers
    can reuse additional metadata (e.g., log level).
    """

    app_settings = load_app_settings(settings_path=settings_path)
    return app_settings.MEDIA_PROCESSING_DOCLING, app_settings
