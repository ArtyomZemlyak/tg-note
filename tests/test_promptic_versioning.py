"""
Tests for promptic library versioning functionality.

This module tests that the promptic library correctly:
1. Detects versioned files with _vX naming convention
2. Returns the latest (highest) version when requested
3. Returns specific versions when requested
"""

from pathlib import Path

import pytest
from promptic import render


class TestPrompticVersioning:
    """Tests for promptic version resolution."""

    def test_render_returns_latest_version(self, tmp_path):
        """render with version='latest' returns the highest version file."""
        # Create versioned prompt files
        base = tmp_path / "test_prompt"
        base.mkdir(parents=True)
        (base / "prompt_v1.md").write_text("Version 1 content", encoding="utf-8")
        (base / "prompt_v2.md").write_text("Version 2 content", encoding="utf-8")
        (base / "prompt_v3.md").write_text("Version 3 content", encoding="utf-8")

        # Load latest version
        content = render(str(base), version="latest")

        # Should return v3 (the highest version)
        assert content == "Version 3 content"

    def test_render_returns_specific_version(self, tmp_path):
        """render with specific version returns that version."""
        base = tmp_path / "test_prompt"
        base.mkdir(parents=True)
        (base / "prompt_v1.md").write_text("Version 1 content", encoding="utf-8")
        (base / "prompt_v2.md").write_text("Version 2 content", encoding="utf-8")
        (base / "prompt_v3.md").write_text("Version 3 content", encoding="utf-8")

        # Load specific versions
        v1_content = render(str(base), version="v1")
        v2_content = render(str(base), version="v2")

        assert v1_content == "Version 1 content"
        assert v2_content == "Version 2 content"

    def test_version_detection_with_multi_digit_versions(self, tmp_path):
        """Versioning works with multi-digit version numbers."""
        base = tmp_path / "test_prompt"
        base.mkdir(parents=True)
        (base / "prompt_v1.md").write_text("v1", encoding="utf-8")
        (base / "prompt_v9.md").write_text("v9", encoding="utf-8")
        (base / "prompt_v10.md").write_text("v10", encoding="utf-8")
        (base / "prompt_v11.md").write_text("v11", encoding="utf-8")

        # Load latest - should be v11, not v9 (lexicographic would give v9)
        content = render(str(base), version="latest")
        assert content == "v11"

    def test_real_prompts_directory_versioning(self):
        """Test versioning with actual project prompts directory."""
        prompts_dir = Path(__file__).parent.parent / "config" / "prompts"

        # Test qwen_code_cli - should have v4 as latest
        qwen_content = render(str(prompts_dir / "qwen_code_cli"), version="latest")
        v4_file = prompts_dir / "qwen_code_cli" / "instruction_v4.md"
        assert v4_file.exists(), "instruction_v4.md should exist"
        assert qwen_content == v4_file.read_text()

        # Test autonomous_agent - should have v3 as latest
        auto_content = render(str(prompts_dir / "autonomous_agent"), version="latest")
        v3_file = prompts_dir / "autonomous_agent" / "instruction_v3.md"
        assert v3_file.exists(), "instruction_v3.md should exist"
        assert auto_content == v3_file.read_text()

        # Test content_processing - should have v2 as latest
        content_proc = render(str(prompts_dir / "content_processing"), version="latest")
        v2_file = prompts_dir / "content_processing" / "template_v2.md"
        assert v2_file.exists(), "template_v2.md should exist"
        assert content_proc == v2_file.read_text()

    def test_naming_convention_underscore_v_required(self, tmp_path):
        """Promptic requires _vX naming convention (not .vX)."""
        base = tmp_path / "test_prompt"
        base.mkdir(parents=True)

        # Files with incorrect naming (.vX) - these should NOT be detected as versioned
        (base / "prompt.v1.md").write_text("dot v1", encoding="utf-8")
        (base / "prompt.v2.md").write_text("dot v2", encoding="utf-8")

        # File with correct naming (_vX)
        (base / "prompt_v3.md").write_text("underscore v3", encoding="utf-8")

        # Should find v3 as the only versioned file
        content = render(str(base), version="latest")
        assert content == "underscore v3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
