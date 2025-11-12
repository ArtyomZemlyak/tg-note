"""
Markdown Link Fixer
Validates and fixes links (images and internal pages) in markdown files before git commit.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger

from src.processor.markdown_image_validator import MarkdownImageValidator


class LinkValidationResult:
    """Result of link validation and fixing."""

    def __init__(self):
        self.files_checked: int = 0
        self.files_fixed: int = 0
        self.images_fixed: int = 0
        self.links_fixed: int = 0
        self.images_broken: int = 0
        self.links_broken: int = 0
        self.errors: List[str] = []

    def has_changes(self) -> bool:
        """Check if any fixes were applied."""
        return self.files_fixed > 0

    def has_broken_links(self) -> bool:
        """Check if there are still broken links after fixing."""
        return self.images_broken > 0 or self.links_broken > 0

    def __str__(self) -> str:
        lines = [
            f"Files checked: {self.files_checked}",
            f"Files fixed: {self.files_fixed}",
            f"Images fixed: {self.images_fixed}",
            f"Links fixed: {self.links_fixed}",
        ]
        if self.has_broken_links():
            lines.append(f"⚠️ Images still broken: {self.images_broken}")
            lines.append(f"⚠️ Links still broken: {self.links_broken}")
        return "\n".join(lines)


class MarkdownLinkFixer:
    """
    Validates and fixes links in markdown files.

    Checks:
    - Image paths: ![alt](path)
    - Internal markdown links: [text](path.md)

    Auto-fix strategies:
    - Calculate correct relative path (../)
    - Find file by name if path wrong
    - Add TODO comment if can't fix
    """

    # Regex patterns
    IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")  # Negative lookbehind for !

    def __init__(self, kb_root: Path):
        """
        Initialize link fixer.

        Args:
            kb_root: Root path of knowledge base
        """
        self.kb_root = Path(kb_root).resolve()
        self.images_dir = self.kb_root / "images"
        self.image_validator = MarkdownImageValidator(kb_root)

    def validate_and_fix_file(self, md_file: Path, dry_run: bool = False) -> Tuple[bool, int, int]:
        """
        Validate and fix links in a markdown file.

        Args:
            md_file: Path to markdown file
            dry_run: If True, don't write changes (just report)

        Returns:
            Tuple of (file_was_modified, images_fixed, links_fixed)
        """
        md_path = Path(md_file).resolve()

        if not md_path.exists() or not md_path.is_file():
            return False, 0, 0

        try:
            original_content = md_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {md_path}: {e}")
            return False, 0, 0

        modified_content = original_content
        images_fixed = 0
        links_fixed = 0

        # Fix image paths
        modified_content, img_fixed = self._fix_image_paths(modified_content, md_path)
        images_fixed += img_fixed

        # Fix internal markdown links
        modified_content, link_fixed = self._fix_markdown_links(modified_content, md_path)
        links_fixed += link_fixed

        # Write back if modified
        if modified_content != original_content:
            if not dry_run:
                try:
                    md_path.write_text(modified_content, encoding="utf-8")
                    logger.info(f"Fixed {md_path.name}: {images_fixed} images, {links_fixed} links")
                except Exception as e:
                    logger.error(f"Failed to write fixes to {md_path}: {e}")
                    return False, 0, 0
            return True, images_fixed, links_fixed

        return False, 0, 0

    def _fix_image_paths(self, content: str, md_file: Path) -> Tuple[str, int]:
        """
        Fix image paths in markdown content.

        Args:
            content: Markdown content
            md_file: Path to markdown file

        Returns:
            Tuple of (modified_content, count_of_fixes)
        """
        fixes_count = 0
        lines = content.split("\n")
        modified_lines = []

        for line in lines:
            modified_line = line
            matches = list(self.IMAGE_PATTERN.finditer(line))

            for match in reversed(matches):  # Reverse to preserve positions
                alt_text = match.group(1)
                img_path = match.group(2)

                # Skip URLs
                if img_path.startswith(("http://", "https://")):
                    continue

                # Try to fix the path
                fixed_path = self._try_fix_image_path(img_path, md_file)

                if fixed_path and fixed_path != img_path:
                    # Replace in line
                    old_ref = f"![{alt_text}]({img_path})"
                    new_ref = f"![{alt_text}]({fixed_path})"
                    modified_line = modified_line.replace(old_ref, new_ref, 1)
                    fixes_count += 1
                    logger.debug(f"Fixed image: {img_path} → {fixed_path}")
                elif not fixed_path:
                    # Can't fix - add TODO comment
                    old_ref = f"![{alt_text}]({img_path})"
                    new_ref = f"![{alt_text}]({img_path}) <!-- TODO: Broken image path -->"
                    if "<!-- TODO:" not in modified_line:  # Don't add duplicate
                        modified_line = modified_line.replace(old_ref, new_ref, 1)
                        logger.warning(f"Can't fix image path: {img_path} in {md_file.name}")

            modified_lines.append(modified_line)

        return "\n".join(modified_lines), fixes_count

    def _try_fix_image_path(self, img_path: str, md_file: Path) -> Optional[str]:
        """
        Try to fix an image path.

        Args:
            img_path: Original image path
            md_file: Path to markdown file containing the reference

        Returns:
            Fixed path or None if can't fix
        """
        # Try to resolve current path
        md_dir = md_file.parent
        resolved = (md_dir / img_path).resolve()

        # If it exists and is valid, path is correct
        if resolved.exists() and resolved.is_file():
            try:
                # Check if it's within images directory
                resolved.relative_to(self.images_dir)
                return None  # Path is already correct
            except ValueError:
                pass  # Not in images dir, continue trying to fix

        # Extract filename
        filename = Path(img_path).name

        # Search for file in images directory
        if self.images_dir.exists():
            for img_file in self.images_dir.rglob(filename):
                if img_file.is_file():
                    # Calculate correct relative path
                    try:
                        rel_path = img_file.relative_to(md_dir)
                        return str(rel_path)
                    except ValueError:
                        # Can't create relative path, try from KB root
                        try:
                            rel_from_kb = img_file.relative_to(self.kb_root)
                            # Calculate how many levels up from md_file to kb_root
                            md_rel_to_kb = md_file.relative_to(self.kb_root)
                            levels_up = len(md_rel_to_kb.parent.parts)
                            prefix = "../" * levels_up
                            return prefix + str(rel_from_kb)
                        except ValueError:
                            pass

        return None  # Can't fix

    def _fix_markdown_links(self, content: str, md_file: Path) -> Tuple[str, int]:
        """
        Fix internal markdown links.

        Args:
            content: Markdown content
            md_file: Path to markdown file

        Returns:
            Tuple of (modified_content, count_of_fixes)
        """
        fixes_count = 0
        lines = content.split("\n")
        modified_lines = []

        for line in lines:
            modified_line = line
            matches = list(self.LINK_PATTERN.finditer(line))

            for match in reversed(matches):
                link_text = match.group(1)
                link_path = match.group(2)

                # Skip URLs and anchors
                if link_path.startswith(("http://", "https://", "#", "mailto:")):
                    continue

                # Only process .md links
                if not link_path.endswith(".md") and ".md#" not in link_path:
                    continue

                # Try to fix the path
                fixed_path = self._try_fix_markdown_link(link_path, md_file)

                if fixed_path and fixed_path != link_path:
                    # Replace in line
                    old_link = f"[{link_text}]({link_path})"
                    new_link = f"[{link_text}]({fixed_path})"
                    modified_line = modified_line.replace(old_link, new_link, 1)
                    fixes_count += 1
                    logger.debug(f"Fixed link: {link_path} → {fixed_path}")
                elif not fixed_path:
                    # Can't fix - add TODO comment
                    old_link = f"[{link_text}]({link_path})"
                    new_link = f"[{link_text}]({link_path}) <!-- TODO: Broken link -->"
                    if "<!-- TODO:" not in modified_line:
                        modified_line = modified_line.replace(old_link, new_link, 1)
                        logger.warning(f"Can't fix link: {link_path} in {md_file.name}")

            modified_lines.append(modified_line)

        return "\n".join(modified_lines), fixes_count

    def _try_fix_markdown_link(self, link_path: str, md_file: Path) -> Optional[str]:
        """
        Try to fix a markdown link path.

        Args:
            link_path: Original link path (may include #anchor)
            md_file: Path to markdown file containing the link

        Returns:
            Fixed path or None if can't fix
        """
        # Split anchor if present
        if "#" in link_path:
            path_part, anchor_part = link_path.split("#", 1)
            anchor = f"#{anchor_part}"
        else:
            path_part = link_path
            anchor = ""

        # Try to resolve current path
        md_dir = md_file.parent
        resolved = (md_dir / path_part).resolve()

        # If it exists, path is correct
        if resolved.exists() and resolved.is_file():
            return None  # Path is already correct

        # Extract filename
        filename = Path(path_part).name

        # Search for file in KB
        for found_file in self.kb_root.rglob(filename):
            if found_file.is_file() and found_file.suffix == ".md":
                # Calculate correct relative path
                try:
                    rel_path = found_file.relative_to(md_dir)
                    return str(rel_path) + anchor
                except ValueError:
                    # Can't create relative path, try from KB root
                    try:
                        rel_from_kb = found_file.relative_to(self.kb_root)
                        md_rel_to_kb = md_file.relative_to(self.kb_root)
                        levels_up = len(md_rel_to_kb.parent.parts)
                        prefix = "../" * levels_up
                        return prefix + str(rel_from_kb) + anchor
                    except ValueError:
                        pass

        return None  # Can't fix

    def validate_and_fix_kb(
        self, changed_files: Optional[List[Path]] = None, dry_run: bool = False
    ) -> LinkValidationResult:
        """
        Validate and fix all (or specified) markdown files in KB.

        Args:
            changed_files: List of changed files to check (None = check all .md files)
            dry_run: If True, don't write changes

        Returns:
            LinkValidationResult with statistics
        """
        result = LinkValidationResult()

        # Determine which files to check
        if changed_files:
            files_to_check = [f for f in changed_files if f.suffix == ".md" and f.exists()]
        else:
            files_to_check = list(self.kb_root.rglob("*.md"))

        logger.info(f"Checking {len(files_to_check)} markdown files for broken links...")

        for md_file in files_to_check:
            result.files_checked += 1

            try:
                modified, images_fixed, links_fixed = self.validate_and_fix_file(
                    md_file, dry_run=dry_run
                )

                if modified:
                    result.files_fixed += 1
                    result.images_fixed += images_fixed
                    result.links_fixed += links_fixed

                # Check for remaining broken links
                if not dry_run:
                    # Re-read file to check for TODO comments
                    content = md_file.read_text(encoding="utf-8")
                    result.images_broken += content.count("<!-- TODO: Broken image path -->")
                    result.links_broken += content.count("<!-- TODO: Broken link -->")

            except Exception as e:
                error_msg = f"Error processing {md_file.name}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        logger.info(f"Link validation complete: {result}")
        return result


def validate_and_fix_links_before_commit(
    kb_root: Path, changed_files: Optional[List[Path]] = None
) -> LinkValidationResult:
    """
    Convenience function to validate and fix links before git commit.

    Args:
        kb_root: Root path of knowledge base
        changed_files: List of changed files (None = check all .md)

    Returns:
        LinkValidationResult
    """
    fixer = MarkdownLinkFixer(kb_root)
    return fixer.validate_and_fix_kb(changed_files=changed_files, dry_run=False)
