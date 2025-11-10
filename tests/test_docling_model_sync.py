import importlib
import os
import sys
import types
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock

import pytest

from config.settings import DoclingModelDownloadSettings


def _install_docling_stubs(monkeypatch):
    from types import SimpleNamespace

    docling_pkg = types.ModuleType("docling")
    docling_pkg.__path__ = []
    datamodel_pkg = types.ModuleType("docling.datamodel")
    datamodel_pkg.__path__ = []
    pipeline_options_mod = types.ModuleType("docling.datamodel.pipeline_options")

    class LayoutOptionsStub:
        def __init__(self):
            self.model_spec = SimpleNamespace(model_repo_folder="LayoutModel")

    pipeline_options_mod.LayoutOptions = LayoutOptionsStub
    pipeline_options_mod.granite_picture_description = SimpleNamespace(
        repo_cache_folder="GraniteVision"
    )
    pipeline_options_mod.smolvlm_picture_description = SimpleNamespace(repo_cache_folder="SmolVLM")

    vlm_model_specs_mod = types.ModuleType("docling.datamodel.vlm_model_specs")
    vlm_model_specs_mod.GRANITEDOCLING_MLX = SimpleNamespace(repo_cache_folder="GraniteDoclingMLX")
    vlm_model_specs_mod.GRANITEDOCLING_TRANSFORMERS = SimpleNamespace(
        repo_cache_folder="GraniteDocling"
    )
    vlm_model_specs_mod.SMOLDOCLING_MLX = SimpleNamespace(repo_cache_folder="SmolDoclingMLX")
    vlm_model_specs_mod.SMOLDOCLING_TRANSFORMERS = SimpleNamespace(repo_cache_folder="SmolDocling")

    models_pkg = types.ModuleType("docling.models")
    models_pkg.__path__ = []

    def _model_class(folder):
        class ModelStub:
            _model_repo_folder = folder

            @staticmethod
            def download_models(**kwargs):
                return Path(folder)

        return ModelStub

    code_formula_mod = types.ModuleType("docling.models.code_formula_model")
    code_formula_mod.CodeFormulaModel = _model_class("CodeFormula")

    picture_classifier_mod = types.ModuleType("docling.models.document_picture_classifier")
    picture_classifier_mod.DocumentPictureClassifier = _model_class("PictureClassifier")

    easyocr_mod = types.ModuleType("docling.models.easyocr_model")
    easyocr_mod.EasyOcrModel = _model_class("EasyOcr")

    layout_mod = types.ModuleType("docling.models.layout_model")
    layout_mod.LayoutModel = _model_class("Layout")

    rapidocr_mod = types.ModuleType("docling.models.rapid_ocr_model")

    class RapidOcrModelStub(_model_class("RapidOcr")):
        _default_models = {"onnxruntime": "onnx", "torch": "torch"}

    rapidocr_mod.RapidOcrModel = RapidOcrModelStub

    table_mod = types.ModuleType("docling.models.table_structure_model")
    table_mod.TableStructureModel = _model_class("TableStructure")

    utils_pkg = types.ModuleType("docling.models.utils")
    utils_pkg.__path__ = []
    hf_download_mod = types.ModuleType("docling.models.utils.hf_model_download")

    def download_hf_model(**kwargs):
        return Path("HFModel")

    hf_download_mod.download_hf_model = download_hf_model

    docling_utils_pkg = types.ModuleType("docling.utils")
    docling_utils_pkg.__path__ = []
    model_downloader_mod = types.ModuleType("docling.utils.model_downloader")

    def download_models(**kwargs):
        return Path("DoclingModels")

    model_downloader_mod.download_models = download_models

    for name, module in [
        ("docling", docling_pkg),
        ("docling.datamodel", datamodel_pkg),
        ("docling.datamodel.pipeline_options", pipeline_options_mod),
        ("docling.datamodel.vlm_model_specs", vlm_model_specs_mod),
        ("docling.models", models_pkg),
        ("docling.models.code_formula_model", code_formula_mod),
        ("docling.models.document_picture_classifier", picture_classifier_mod),
        ("docling.models.easyocr_model", easyocr_mod),
        ("docling.models.layout_model", layout_mod),
        ("docling.models.rapid_ocr_model", rapidocr_mod),
        ("docling.models.table_structure_model", table_mod),
        ("docling.models.utils", utils_pkg),
        ("docling.models.utils.hf_model_download", hf_download_mod),
        ("docling.utils", docling_utils_pkg),
        ("docling.utils.model_downloader", model_downloader_mod),
    ]:
        monkeypatch.setitem(sys.modules, name, module)

    docling_pkg.datamodel = datamodel_pkg
    datamodel_pkg.pipeline_options = pipeline_options_mod
    datamodel_pkg.vlm_model_specs = vlm_model_specs_mod
    models_pkg.code_formula_model = code_formula_mod
    models_pkg.document_picture_classifier = picture_classifier_mod
    models_pkg.easyocr_model = easyocr_mod
    models_pkg.layout_model = layout_mod
    models_pkg.rapid_ocr_model = rapidocr_mod
    models_pkg.table_structure_model = table_mod
    utils_pkg.hf_model_download = hf_download_mod
    docling_utils_pkg.model_downloader = model_downloader_mod


def _install_huggingface_stub(monkeypatch):
    huggingface_mod = types.ModuleType("huggingface_hub")

    def snapshot_download(**kwargs):
        raise RuntimeError("snapshot_download stub should be patched in tests.")

    huggingface_mod.snapshot_download = snapshot_download
    monkeypatch.setitem(sys.modules, "huggingface_hub", huggingface_mod)


@pytest.fixture
def model_sync(monkeypatch):
    _install_docling_stubs(monkeypatch)
    _install_huggingface_stub(monkeypatch)

    converter_stub = types.ModuleType("tg_docling.converter")

    def install_converter(settings):
        return None

    # AICODE-NOTE: Add _LAYOUT_PRESET_MAP and picture description stubs for model_sync imports
    from types import SimpleNamespace

    converter_stub.install_converter = install_converter
    converter_stub._LAYOUT_PRESET_MAP = {
        "layout_v2": SimpleNamespace(
            name="layout_v2",
            repo_id="test/layout-v2",
            revision="main",
            model_repo_folder="LayoutModel",
        ),
        "layout_heron": SimpleNamespace(
            name="layout_heron",
            repo_id="test/layout-heron",
            revision="main",
            model_repo_folder="LayoutHeron",
        ),
    }
    converter_stub._PICTURE_DESCRIPTION_PRESET_OPTIONS = {
        "smolvlm": SimpleNamespace(
            repo_id="test/smolvlm",
            repo_cache_folder="SmolVLM",
        ),
        "granite_vision": SimpleNamespace(
            repo_id="test/granite-vision",
            repo_cache_folder="GraniteVision",
        ),
    }
    converter_stub._PICTURE_DESCRIPTION_SPEC_MAP = {
        "granitedocling": SimpleNamespace(
            repo_id="test/granitedocling",
            repo_cache_folder="GraniteDocling",
        ),
        "smoldocling": SimpleNamespace(
            repo_id="test/smoldocling",
            repo_cache_folder="SmolDocling",
        ),
    }
    monkeypatch.setitem(sys.modules, "tg_docling.converter", converter_stub)

    from types import SimpleNamespace

    config_stub = types.ModuleType("tg_docling.config")
    config_stub.DEFAULT_SETTINGS_PATH = Path("/tmp/docling-settings.yaml")

    def load_docling_settings(settings_path=None):
        dummy_settings = SimpleNamespace(model_cache=SimpleNamespace(groups=[], downloads=[]))
        return dummy_settings, dummy_settings

    config_stub.load_docling_settings = load_docling_settings
    monkeypatch.setitem(sys.modules, "tg_docling.config", config_stub)

    app_path = Path(__file__).resolve().parents[1] / "docker" / "docling-mcp" / "app"
    monkeypatch.syspath_prepend(str(app_path))
    module = importlib.import_module("tg_docling.model_sync")
    module = importlib.reload(module)
    yield module
    module.set_sync_progress_callback(None)
    module._HF_TRANSFER_FAST_DOWNLOAD_AVAILABLE = None


def test_hf_transfer_fallback_when_package_missing(tmp_path, monkeypatch, model_sync):
    monkeypatch.setenv("HF_HUB_ENABLE_HF_TRANSFER", "1")

    download = DoclingModelDownloadSettings(name="test-repo", repo_id="org/repo")
    target_dir = tmp_path / "hf-download"

    progress_events: List[Tuple[str, dict]] = []
    model_sync.set_sync_progress_callback(
        lambda message, data: progress_events.append((message, data))
    )

    error_message = (
        "Fast download using 'hf_transfer' is enabled (HF_HUB_ENABLE_HF_TRANSFER=1) but "
        "'hf_transfer' package is not available in your environment."
    )
    mock_snapshot = MagicMock(
        side_effect=[ValueError(error_message), str(target_dir / "model-cache")]
    )
    monkeypatch.setattr(model_sync, "snapshot_download", mock_snapshot)

    result = model_sync._sync_huggingface(target_dir, download, force=True)

    assert result["status"] == "downloaded"
    assert mock_snapshot.call_count == 2
    assert os.environ["HF_HUB_ENABLE_HF_TRANSFER"] == "1"
    assert model_sync._HF_TRANSFER_FAST_DOWNLOAD_AVAILABLE is False
    assert any("hf_transfer package missing" in message for message, _ in progress_events)


def test_hf_transfer_disabled_skips_retry(tmp_path, monkeypatch, model_sync):
    monkeypatch.setenv("HF_HUB_ENABLE_HF_TRANSFER", "1")

    model_sync._HF_TRANSFER_FAST_DOWNLOAD_AVAILABLE = False

    download = DoclingModelDownloadSettings(name="test-repo", repo_id="org/repo")
    target_dir = tmp_path / "hf-download-second"

    call_env_values: List[str] = []

    def snapshot_stub(**kwargs):
        call_env_values.append(os.environ.get("HF_HUB_ENABLE_HF_TRANSFER"))
        return str(target_dir / "model-cache")

    monkeypatch.setattr(model_sync, "snapshot_download", snapshot_stub)

    result = model_sync._sync_huggingface(target_dir, download, force=True)

    assert result["status"] == "downloaded"
    assert call_env_values == ["0"]
    assert os.environ["HF_HUB_ENABLE_HF_TRANSFER"] == "1"
