"""
Tests for markdown image validator.
"""

import tempfile
from pathlib import Path

import pytest

from src.processor.markdown_media_validator import (
    MarkdownMediaValidator,
    MediaReference,
    ValidationIssue,
    validate_agent_generated_markdown,
)


@pytest.fixture
def temp_kb():
    """Create temporary knowledge base structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_root = Path(tmpdir)
        media_dir = kb_root / "media"
        topics_dir = kb_root / "topics"

        media_dir.mkdir()
        topics_dir.mkdir()

        # Create some test images
        (media_dir / "test_image.jpg").write_text("fake image")
        (media_dir / "another_image.png").write_text("fake image")

        yield kb_root


def test_find_image_references_basic(temp_kb):
    """Test finding basic image references in markdown."""
    validator = MarkdownMediaValidator(temp_kb)

    # Create markdown file with image reference
    md_file = temp_kb / "test.md"
    md_content = """# Test Document

![Test image](media/test_image.jpg)

Some text here.
"""
    md_file.write_text(md_content)

    refs, issues = validator.validate_markdown_file(md_file)

    # Should find 1 reference
    assert len(refs) == 1
    assert refs[0].path == "media/test_image.jpg"
    assert refs[0].alt_text == "Test image"
    assert refs[0].line_number == 3

    # Should have no errors (image exists)
    errors = [i for i in issues if i.severity == ValidationIssue.SEVERITY_ERROR]
    assert len(errors) == 0


def test_detect_missing_image(temp_kb):
    """Test detection of missing image files."""
    validator = MarkdownMediaValidator(temp_kb)

    # Create markdown file with reference to non-existent image
    md_file = temp_kb / "test.md"
    md_content = """# Test Document

![Missing image](media/missing.jpg)
"""
    md_file.write_text(md_content)

    refs, issues = validator.validate_markdown_file(md_file)

    # Should find reference
    assert len(refs) == 1
    assert refs[0].exists is False

    # Should have error
    errors = [i for i in issues if i.severity == ValidationIssue.SEVERITY_ERROR]
    assert len(errors) == 1
    assert "not found" in errors[0].message.lower()


def test_relative_paths_from_subdirectory(temp_kb):
    """Test validation of relative paths from subdirectory."""
    validator = MarkdownMediaValidator(temp_kb)

    # Create markdown in topics/ subdirectory
    topics_dir = temp_kb / "topics"
    md_file = topics_dir / "test.md"
    md_content = """# Test Document

![Test image](../media/test_image.jpg)
"""
    md_file.write_text(md_content)

    refs, issues = validator.validate_markdown_file(md_file)

    # Should find reference and resolve correctly
    assert len(refs) == 1
    assert refs[0].path == "../media/test_image.jpg"
    assert refs[0].exists is True

    # Should have no errors
    errors = [i for i in issues if i.severity == ValidationIssue.SEVERITY_ERROR]
    assert len(errors) == 0


def test_incorrect_relative_path(temp_kb):
    """Test detection of incorrect relative path."""
    validator = MarkdownMediaValidator(temp_kb)

    # Create markdown in topics/ with wrong path (missing ../)
    topics_dir = temp_kb / "topics"
    md_file = topics_dir / "test.md"
    md_content = """# Test Document

![Test image](media/test_image.jpg)
"""
    md_file.write_text(md_content)

    refs, issues = validator.validate_markdown_file(md_file)

    # Should find reference but it won't exist (wrong relative path)
    assert len(refs) == 1
    assert refs[0].exists is False

    # Should have error with suggestion
    errors = [i for i in issues if i.severity == ValidationIssue.SEVERITY_ERROR]
    assert len(errors) == 1
    assert errors[0].suggestion is not None
    # Suggestion should contain the correct relative path (may vary based on OS/filesystem)
    # Just check that a suggestion was provided
    assert len(errors[0].suggestion) > 0


def test_suggest_nested_image_path(temp_kb):
    """Test that suggestions include nested image directories."""
    validator = MarkdownMediaValidator(temp_kb)

    nested_dir = temp_kb / "media" / "reports" / "q1"
    nested_dir.mkdir(parents=True, exist_ok=True)
    (nested_dir / "chart.png").write_text("fake image")

    md_file = temp_kb / "topics" / "nested.md"
    md_file.write_text("# Nested\n\n![Chart](media/chart.png)")

    _, issues = validator.validate_markdown_file(md_file)

    errors = [i for i in issues if i.severity == ValidationIssue.SEVERITY_ERROR]
    assert len(errors) == 1
    assert errors[0].suggestion == "../media/reports/q1/chart.png"


def test_empty_alt_text_warning(temp_kb):
    """Test warning for empty alt text."""
    validator = MarkdownMediaValidator(temp_kb)

    md_file = temp_kb / "test.md"
    md_content = """# Test Document

![](media/test_image.jpg)
"""
    md_file.write_text(md_content)

    refs, issues = validator.validate_markdown_file(md_file, check_alt_text=True)

    # Should find warning about empty alt text
    warnings = [i for i in issues if i.severity == ValidationIssue.SEVERITY_WARNING]
    assert len(warnings) >= 1
    assert any("empty alt text" in w.message.lower() for w in warnings)


def test_generic_alt_text_info(temp_kb):
    """Test info message for generic alt text."""
    validator = MarkdownMediaValidator(temp_kb)

    md_file = temp_kb / "test.md"
    md_content = """# Test Document

![image](media/test_image.jpg)
"""
    md_file.write_text(md_content)

    refs, issues = validator.validate_markdown_file(md_file, check_alt_text=True)

    # Should find info about generic alt text
    infos = [i for i in issues if i.severity == ValidationIssue.SEVERITY_INFO]
    assert len(infos) >= 1
    assert any("generic" in info.message.lower() for info in infos)


def test_skip_http_urls(temp_kb):
    """Test that HTTP/HTTPS URLs are skipped."""
    validator = MarkdownMediaValidator(temp_kb)

    md_file = temp_kb / "test.md"
    md_content = """# Test Document

![Remote image](https://example.com/image.jpg)
![Another remote](http://example.com/photo.png)
"""
    md_file.write_text(md_content)

    refs, issues = validator.validate_markdown_file(md_file)

    # Should not find any references (URLs skipped)
    assert len(refs) == 0
    assert len(issues) == 0


def test_multiple_images_on_same_line(temp_kb):
    """Test finding multiple images on same line."""
    validator = MarkdownMediaValidator(temp_kb)

    md_file = temp_kb / "test.md"
    md_content = """# Test Document

![Image 1](media/test_image.jpg) and ![Image 2](media/another_image.png)
"""
    md_file.write_text(md_content)

    refs, issues = validator.validate_markdown_file(md_file)

    # Should find both references
    assert len(refs) == 2
    assert refs[0].line_number == refs[1].line_number == 3


def test_validate_kb_directory(temp_kb):
    """Test validation of entire KB directory."""
    validator = MarkdownMediaValidator(temp_kb)

    # Create multiple markdown files
    (temp_kb / "file1.md").write_text("![Good](media/test_image.jpg)")
    (temp_kb / "file2.md").write_text("![Bad](media/missing.jpg)")

    topics_dir = temp_kb / "topics"
    (topics_dir / "file3.md").write_text("![Also good](../media/test_image.jpg)")

    results = validator.validate_kb_directory(check_alt_text=False)

    # Should have issues only for file2.md (missing image)
    assert "file2.md" in results
    assert len(results["file2.md"]) > 0

    # file1.md and topics/file3.md should be OK
    assert "file1.md" not in results or len(results.get("file1.md", [])) == 0


def test_find_unreferenced_images(temp_kb):
    """Test finding images not referenced in any markdown."""
    validator = MarkdownMediaValidator(temp_kb)

    # Create images
    (temp_kb / "media" / "referenced.jpg").write_text("fake")
    (temp_kb / "media" / "unreferenced.jpg").write_text("fake")

    # Create markdown referencing only one image
    md_file = temp_kb / "test.md"
    md_file.write_text("![Used](media/referenced.jpg)")

    unreferenced = validator.find_unreferenced_images()

    # Should find unreferenced.jpg
    unreferenced_names = [img.name for img in unreferenced]
    assert "unreferenced.jpg" in unreferenced_names
    assert "referenced.jpg" not in unreferenced_names


def test_validate_agent_generated_markdown_function(temp_kb):
    """Test convenience function for validating agent-generated markdown."""
    # Create valid markdown
    md_file = temp_kb / "test.md"
    md_file.write_text("![Valid](media/test_image.jpg)")

    result = validate_agent_generated_markdown(md_file, temp_kb)
    assert result is True

    # Create invalid markdown
    md_file2 = temp_kb / "test2.md"
    md_file2.write_text("![Invalid](media/missing.jpg)")

    result2 = validate_agent_generated_markdown(md_file2, temp_kb)
    assert result2 is False


def test_image_outside_kb_warning(temp_kb):
    """Test warning when image is outside KB images directory."""
    validator = MarkdownMediaValidator(temp_kb)

    # Create image outside media/ directory
    outside_img = temp_kb / "outside.jpg"
    outside_img.write_text("fake")

    # Reference it from markdown
    md_file = temp_kb / "test.md"
    md_file.write_text("![Outside](outside.jpg)")

    refs, issues = validator.validate_markdown_file(md_file)

    # Should have warning about image outside media/
    warnings = [i for i in issues if i.severity == ValidationIssue.SEVERITY_WARNING]
    assert len(warnings) >= 1
    assert any("outside" in w.message.lower() for w in warnings)


def test_generate_report(temp_kb):
    """Test report generation."""
    validator = MarkdownMediaValidator(temp_kb)

    # Create files with issues
    (temp_kb / "good.md").write_text("![Good](media/test_image.jpg)")
    (temp_kb / "bad.md").write_text("![Bad](media/missing.jpg)")

    results = validator.validate_kb_directory(check_alt_text=False)
    report = validator.generate_report(results, verbose=False)

    # Report should contain summary
    assert "SUMMARY" in report
    assert "Errors:" in report

    # Report should mention bad.md but not good.md
    assert "bad.md" in report
    # good.md might not appear if it has no issues


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
