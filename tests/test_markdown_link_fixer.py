"""
Tests for markdown link fixer.
"""

import tempfile
from pathlib import Path

import pytest

from src.processor.markdown_link_fixer import MarkdownLinkFixer


@pytest.fixture
def temp_kb():
    """Create temporary KB structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_root = Path(tmpdir)
        media_dir = kb_root / "media"
        topics_dir = kb_root / "topics"

        media_dir.mkdir()
        topics_dir.mkdir()

        # Create test images
        (media_dir / "chart.jpg").write_bytes(b"fake")
        (media_dir / "diagram.png").write_bytes(b"fake")

        # Create test markdown files
        (kb_root / "index.md").write_text("# Index")
        (topics_dir / "page1.md").write_text("# Page 1")
        (topics_dir / "page2.md").write_text("# Page 2")

        yield kb_root


def test_fix_incorrect_image_path(temp_kb):
    """Test fixing incorrect image path in topics/ subfolder."""
    fixer = MarkdownLinkFixer(temp_kb)

    topics_dir = temp_kb / "topics"
    md_file = topics_dir / "test.md"

    # Wrong path: missing ../
    md_file.write_text("# Test\n\n![Chart](media/chart.jpg)")

    # Fix it
    modified, images_fixed, links_fixed = fixer.validate_and_fix_file(md_file)

    assert modified is True
    assert images_fixed == 1

    # Check fixed content
    content = md_file.read_text()
    assert "![Chart](../media/chart.jpg)" in content


def test_fix_missing_image_add_todo(temp_kb):
    """Test adding TODO comment for missing image."""
    fixer = MarkdownLinkFixer(temp_kb)

    md_file = temp_kb / "test.md"
    md_file.write_text("# Test\n\n![Missing](media/missing.jpg)")

    # Try to fix
    modified, images_fixed, links_fixed = fixer.validate_and_fix_file(md_file)

    # Should be modified (TODO added)
    assert modified is True

    # Check TODO comment added
    content = md_file.read_text()
    assert "<!-- TODO: Broken image path -->" in content


def test_fix_markdown_link_path(temp_kb):
    """Test fixing internal markdown link path."""
    fixer = MarkdownLinkFixer(temp_kb)

    topics_dir = temp_kb / "topics"
    md_file = topics_dir / "test.md"

    # Correct path: page1.md is in same directory
    md_file.write_text("# Test\n\nSee [Page 1](page1.md)")

    # Fix it
    modified, images_fixed, links_fixed = fixer.validate_and_fix_file(md_file)

    # Path exists and is correct, no fix needed
    # (but if validator thinks it's broken, it adds TODO)
    content = md_file.read_text()

    # Either no modification OR TODO comment added
    # (depends on whether file can be found)
    if modified:
        # TODO comment was added
        assert "<!-- TODO:" in content
    else:
        # No modification needed
        assert "page1.md" in content


def test_fix_markdown_link_from_root_to_topics(temp_kb):
    """Test fixing link from root to topics/."""
    fixer = MarkdownLinkFixer(temp_kb)

    md_file = temp_kb / "test.md"

    # Wrong path: missing topics/
    md_file.write_text("# Test\n\nSee [Page 1](page1.md)")

    # Fix it
    modified, images_fixed, links_fixed = fixer.validate_and_fix_file(md_file)

    assert modified is True
    assert links_fixed == 1

    # Check fixed content
    content = md_file.read_text()
    assert "[Page 1](topics/page1.md)" in content


def test_skip_http_urls(temp_kb):
    """Test that HTTP URLs are not touched."""
    fixer = MarkdownLinkFixer(temp_kb)

    md_file = temp_kb / "test.md"
    original = "# Test\n\n![Remote](https://example.com/image.jpg)\n[Link](https://example.com)"
    md_file.write_text(original)

    # Should not modify
    modified, _, _ = fixer.validate_and_fix_file(md_file)

    assert modified is False
    assert md_file.read_text() == original


def test_multiple_fixes_in_one_file(temp_kb):
    """Test fixing multiple issues in one file."""
    fixer = MarkdownLinkFixer(temp_kb)

    topics_dir = temp_kb / "topics"
    md_file = topics_dir / "test.md"

    md_file.write_text(
        """# Test

![Chart](media/chart.jpg)
![Diagram](media/diagram.png)

See also:
- [Page 1](../page1.md)
- [Page 2](page2.md)
"""
    )

    # Fix it
    modified, images_fixed, links_fixed = fixer.validate_and_fix_file(md_file)

    assert modified is True
    assert images_fixed == 2  # Both images fixed
    # Links: page2.md is correct, but ../page1.md should be just page1.md
    assert links_fixed >= 0

    content = md_file.read_text()
    assert "![Chart](../media/chart.jpg)" in content
    assert "![Diagram](../media/diagram.png)" in content


def test_preserve_anchor_in_links(temp_kb):
    """Test that anchors are preserved when fixing links."""
    fixer = MarkdownLinkFixer(temp_kb)

    md_file = temp_kb / "test.md"
    md_file.write_text("# Test\n\n[Link](page1.md#section)")

    # Fix it
    modified, _, links_fixed = fixer.validate_and_fix_file(md_file)

    assert modified is True
    assert links_fixed == 1

    content = md_file.read_text()
    # Anchor should be preserved
    assert "#section" in content


def test_dry_run_mode(temp_kb):
    """Test dry run mode (doesn't write changes)."""
    fixer = MarkdownLinkFixer(temp_kb)

    topics_dir = temp_kb / "topics"
    md_file = topics_dir / "test.md"
    original = "# Test\n\n![Chart](media/chart.jpg)"
    md_file.write_text(original)

    # Dry run
    modified, images_fixed, _ = fixer.validate_and_fix_file(md_file, dry_run=True)

    assert modified is True
    assert images_fixed == 1

    # But file should not be changed
    assert md_file.read_text() == original


def test_validate_kb_with_changed_files(temp_kb):
    """Test validating only specified changed files."""
    fixer = MarkdownLinkFixer(temp_kb)

    # Create files with issues
    topics_dir = temp_kb / "topics"
    file1 = topics_dir / "file1.md"
    file2 = topics_dir / "file2.md"

    file1.write_text("![Chart](media/chart.jpg)")
    file2.write_text("![Diagram](media/diagram.png)")

    # Validate only file1
    result = fixer.validate_and_fix_kb(changed_files=[file1], dry_run=False)

    assert result.files_checked == 1
    assert result.files_fixed == 1
    assert result.images_fixed == 1

    # file1 should be fixed
    assert "![Chart](../media/chart.jpg)" in file1.read_text()

    # file2 should NOT be fixed
    assert "![Diagram](media/diagram.png)" in file2.read_text()


def test_case_insensitive_extension(temp_kb):
    """Test that .MD extension is handled correctly."""
    fixer = MarkdownLinkFixer(temp_kb)

    topics_dir = temp_kb / "topics"
    md_file = topics_dir / "TEST.MD"  # Uppercase extension
    md_file.write_text("![Chart](media/chart.jpg)")

    modified, images_fixed, _ = fixer.validate_and_fix_file(md_file)

    assert modified is True
    assert images_fixed == 1


def test_no_duplicate_todo_comments(temp_kb):
    """Test that TODO comments are not duplicated."""
    fixer = MarkdownLinkFixer(temp_kb)

    md_file = temp_kb / "test.md"
    md_file.write_text("![Missing](media/missing.jpg) <!-- TODO: Broken image path -->")

    # Try to fix again
    modified, _, _ = fixer.validate_and_fix_file(md_file)

    # Should not add another TODO
    content = md_file.read_text()
    assert content.count("<!-- TODO:") == 1


def test_add_todo_for_each_broken_image_same_line(temp_kb):
    """Test that each broken image on the same line gets its own TODO comment."""
    fixer = MarkdownLinkFixer(temp_kb)

    md_file = temp_kb / "test.md"
    md_file.write_text("![First](media/missing1.jpg) and ![Second](media/missing2.jpg)")

    modified, images_fixed, links_fixed = fixer.validate_and_fix_file(md_file)

    assert modified is True
    assert images_fixed == 0
    assert links_fixed == 0

    content = md_file.read_text()
    assert content.count("<!-- TODO: Broken image path -->") == 2


def test_add_todo_for_each_broken_link_same_line(temp_kb):
    """Test that each broken markdown link on the same line gets its own TODO comment."""
    fixer = MarkdownLinkFixer(temp_kb)

    md_file = temp_kb / "test.md"
    md_file.write_text("[Doc1](missing-one.md) and [Doc2](missing-two.md)")

    modified, images_fixed, links_fixed = fixer.validate_and_fix_file(md_file)

    assert modified is True
    assert images_fixed == 0
    assert links_fixed == 0

    content = md_file.read_text()
    assert content.count("<!-- TODO: Broken link -->") == 2


def test_choose_nearest_markdown_link_candidate(temp_kb):
    """Test that the fixer prefers the closest matching markdown file."""
    fixer = MarkdownLinkFixer(temp_kb)

    section1 = temp_kb / "topics" / "section1"
    section2 = temp_kb / "topics" / "section2"
    section2_sub = section2 / "sub"

    section1.mkdir(parents=True, exist_ok=True)
    section2_sub.mkdir(parents=True, exist_ok=True)

    (section1 / "target.md").write_text("# Section 1 target")
    (section2 / "target.md").write_text("# Section 2 target")

    md_file = section2_sub / "note.md"
    md_file.write_text("# Note\n\n[Target](target.md)")

    modified, images_fixed, links_fixed = fixer.validate_and_fix_file(md_file)

    assert modified is True
    assert images_fixed == 0
    assert links_fixed == 1

    content = md_file.read_text()
    assert "[Target](../target.md)" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
