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

        # Test qwen_code_cli - latest should resolve to v5
        qwen_content_latest = render(str(prompts_dir / "qwen_code_cli"), version="latest")
        qwen_content_v5 = render(str(prompts_dir / "qwen_code_cli"), version="v5")
        v5_file = prompts_dir / "qwen_code_cli" / "instruction_v5.md"
        assert v5_file.exists(), "instruction_v5.md should exist"
        assert qwen_content_latest == qwen_content_v5
        assert "Работа с медиафайлами" in qwen_content_latest

        # Test autonomous_agent - latest should resolve to v3
        auto_latest = render(str(prompts_dir / "autonomous_agent"), version="latest")
        auto_v3 = render(str(prompts_dir / "autonomous_agent"), version="v3")
        v3_file = prompts_dir / "autonomous_agent" / "instruction_v3.md"
        assert v3_file.exists(), "instruction_v3.md should exist"
        assert auto_latest == auto_v3

        # Test content_processing - latest should resolve to v2
        content_latest = render(str(prompts_dir / "content_processing"), version="latest")
        content_v2 = render(str(prompts_dir / "content_processing"), version="v2")
        v2_file = prompts_dir / "content_processing" / "template_v2.md"
        assert v2_file.exists(), "template_v2.md should exist"
        assert content_latest == content_v2

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
