from __future__ import annotations

import sys
from pathlib import Path

import pytest

TEST_ROOT = Path(__file__).resolve().parents[2]
DOC_MCP_APP = TEST_ROOT / "docker" / "docling-mcp" / "app"
if str(DOC_MCP_APP) not in sys.path:
    sys.path.insert(0, str(DOC_MCP_APP))

from tg_docling import tesseract  # noqa: E402  # Import after sys.path modification


def test_resolve_tessdata_prefers_configured_relative_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    models_base = tmp_path / "models"
    models_base.mkdir()
    tess_dir = models_base / "tessdata"
    tess_dir.mkdir()

    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)

    resolved = tesseract.resolve_tessdata_path(models_base, "tessdata")
    assert resolved == str(tess_dir.resolve())


def test_resolve_tessdata_environment_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    models_base = tmp_path / "models"
    models_base.mkdir()
    env_dir = tmp_path / "env_tessdata"
    env_dir.mkdir()

    monkeypatch.setenv("TESSDATA_PREFIX", str(env_dir))

    resolved = tesseract.resolve_tessdata_path(models_base, None)
    assert resolved == str(env_dir)


def test_resolve_tessdata_default_candidates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    candidate_dir = tmp_path / "default_tessdata"
    candidate_dir.mkdir()

    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    monkeypatch.setattr(
        tesseract,
        "DEFAULT_TESSDATA_CANDIDATES",
        (candidate_dir,),
        raising=False,
    )

    resolved = tesseract.resolve_tessdata_path(tmp_path, None)
    assert resolved == str(candidate_dir)


def test_resolve_tessdata_missing_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    monkeypatch.setattr(tesseract, "DEFAULT_TESSDATA_CANDIDATES", tuple(), raising=False)

    resolved = tesseract.resolve_tessdata_path(tmp_path, None)
    assert resolved is None
