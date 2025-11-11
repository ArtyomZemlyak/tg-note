import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


def _ensure_stub_modules():
    """Install lightweight stubs for external Docling dependencies when running unit tests."""
    # docling_core stubs
    sys.modules.setdefault("docling_core", types.ModuleType("docling_core"))
    sys.modules.setdefault("docling_core.types", types.ModuleType("docling_core.types"))
    sys.modules.setdefault("docling_core.types.doc", types.ModuleType("docling_core.types.doc"))

    doc_document = types.ModuleType("docling_core.types.doc.document")
    doc_document.ContentLayer = SimpleNamespace(FURNITURE="furniture")
    sys.modules["docling_core.types.doc.document"] = doc_document

    doc_labels = types.ModuleType("docling_core.types.doc.labels")
    doc_labels.DocItemLabel = SimpleNamespace(TEXT="text")
    sys.modules["docling_core.types.doc.labels"] = doc_labels

    # docling_mcp stubs
    sys.modules.setdefault("docling_mcp", types.ModuleType("docling_mcp"))

    docling_cache = types.ModuleType("docling_mcp.docling_cache")
    docling_cache.get_cache_key = lambda source: source
    sys.modules["docling_mcp.docling_cache"] = docling_cache

    class _MCPStub:
        def tool(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    shared_module = types.ModuleType("docling_mcp.shared")
    shared_module.local_document_cache = {}
    shared_module.local_stack_cache = {}
    shared_module.mcp = _MCPStub()
    sys.modules["docling_mcp.shared"] = shared_module

    tools_conversion = types.ModuleType("docling_mcp.tools.conversion")

    class _ConvertDocumentOutput(SimpleNamespace):
        def __init__(self, cache_hit: bool, cache_key: str):
            super().__init__(cache_hit=cache_hit, cache_key=cache_key)

    tools_conversion.ConvertDocumentOutput = _ConvertDocumentOutput
    tools_conversion.cleanup_memory = lambda: None
    tools_conversion._get_converter = lambda: None
    sys.modules.setdefault("docling_mcp.tools", types.ModuleType("docling_mcp.tools"))
    sys.modules["docling_mcp.tools.conversion"] = tools_conversion

    # tg_docling model sync stub to avoid heavy imports
    docling_model_sync = types.ModuleType("tg_docling.model_sync")
    docling_model_sync.sync_models = lambda settings, force=False: {"summary": {"failed": 0}}
    sys.modules["tg_docling.model_sync"] = docling_model_sync

    # mcp types stub
    mcp_types = types.ModuleType("mcp.types")

    class _ToolAnnotations(SimpleNamespace):
        pass

    mcp_types.ToolAnnotations = _ToolAnnotations
    sys.modules["mcp.types"] = mcp_types


def _load_tools_module():
    """Ensure tg_docling.tools is importable during tests."""
    _ensure_stub_modules()
    docling_app_path = Path(__file__).resolve().parents[1] / "docker" / "docling-mcp" / "app"
    if str(docling_app_path) not in sys.path:
        sys.path.insert(0, str(docling_app_path))
    module = importlib.import_module("tg_docling.tools")
    return importlib.reload(module)


def test_extract_missing_model_path_from_message():
    tools = _load_tools_module()
    exc = RuntimeError("Missing safe tensors file: /opt/docling-mcp/models/model.safetensors")
    assert (
        tools._extract_missing_model_path(exc)  # type: ignore[attr-defined]
        == "/opt/docling-mcp/models/model.safetensors"
    )


def test_convert_with_model_recovery_triggers_sync(monkeypatch, tmp_path):
    tools = _load_tools_module()
    attempts = {"convert": 0, "sync": 0}

    class DummyConverter:
        def convert(self, _path):
            attempts["convert"] += 1
            if attempts["convert"] == 1:
                raise FileNotFoundError(
                    "Missing safe tensors file: /opt/docling-mcp/models/model.safetensors"
                )
            return SimpleNamespace()

    monkeypatch.setattr(tools.conversion_tools, "_get_converter", lambda: DummyConverter())

    def fake_attempt_model_resync(_missing):
        attempts["sync"] += 1
        return True

    monkeypatch.setattr(tools, "_attempt_model_resync", fake_attempt_model_resync)
    monkeypatch.setattr(tools, "_invalidate_converter_cache", lambda: None)

    tools._convert_with_model_recovery(tmp_path / "sample.pdf")  # type: ignore[attr-defined]

    assert attempts["convert"] == 2
    assert attempts["sync"] == 1


def test_convert_with_model_recovery_raises_when_resync_fails(monkeypatch, tmp_path):
    tools = _load_tools_module()
    monkeypatch.setenv("DOCLING_MODELS_DIR", "/opt/docling-mcp/models")

    class FailingConverter:
        def convert(self, _path):
            raise FileNotFoundError(
                "Missing safe tensors file: /opt/docling-mcp/models/model.safetensors"
            )

    monkeypatch.setattr(tools.conversion_tools, "_get_converter", lambda: FailingConverter())
    monkeypatch.setattr(tools, "_invalidate_converter_cache", lambda: None)
    monkeypatch.setattr(tools, "_attempt_model_resync", lambda _missing: False)

    with pytest.raises(tools.DoclingModelMissingError):
        tools._convert_with_model_recovery(tmp_path / "sample.pdf")  # type: ignore[attr-defined]
