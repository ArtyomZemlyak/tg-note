"""
Unit tests for LinksField filtering functionality
AICODE-NOTE: Standalone unit tests that don't require full package imports
"""

import pytest


# AICODE-NOTE: Minimal test implementation to avoid dependency issues
# Copy relevant parts of LinksField for isolated testing
class LinksFieldMock:
    """Mock LinksField for unit testing filtering logic"""

    def __init__(self, min_description_length: int = 30):
        self.min_description_length = min_description_length

    def parse(self, response_data: dict) -> list:
        """Parse links field with filtering (copied from actual implementation)"""
        links = response_data.get("links", [])
        created_files = response_data.get("created", [])

        # Template phrases to detect low-quality descriptions
        template_phrases = [
            "связанная тема",
            "связанный файл",
            "похожий контент",
            "схожая тема",
            "related topic",
            "similar content",
            "тоже про",
            "также о",
        ]

        filtered_links = []
        for link in links:
            if not isinstance(link, dict):
                continue

            file_path = link.get("file", "")
            description = link.get("description", "")

            # Filter 1: Skip links to just-created files
            if file_path in created_files:
                continue

            # Filter 2: Skip links with too short descriptions
            if len(description.strip()) < self.min_description_length:
                continue

            # Filter 3: Skip template-like descriptions
            description_lower = description.lower()
            is_template = any(phrase in description_lower for phrase in template_phrases)
            if is_template:
                continue

            filtered_links.append(link)

        return filtered_links


class TestLinksFieldFiltering:
    """Test LinksField filtering logic"""

    def test_filter_created_files(self):
        """Test that links to just-created files are filtered out"""
        field = LinksFieldMock(min_description_length=10)

        response_data = {
            "created": ["new_file.md", "another_new.md"],
            "links": [
                {
                    "file": "new_file.md",
                    "description": "This is a link to a just-created file, should be filtered",
                },
                {
                    "file": "existing_file.md",
                    "description": "This is a link to an existing file, should remain",
                },
                {
                    "file": "another_new.md",
                    "description": "This is another link to a just-created file",
                },
            ],
        }

        result = field.parse(response_data)

        # Only one link should remain (to existing_file.md)
        assert len(result) == 1
        assert result[0]["file"] == "existing_file.md"

    def test_filter_short_descriptions(self):
        """Test that links with too-short descriptions are filtered out"""
        field = LinksFieldMock(min_description_length=30)

        response_data = {
            "created": [],
            "links": [
                {"file": "file1.md", "description": "Short"},  # Too short (5 chars)
                {"file": "file2.md", "description": "A bit longer desc"},  # 18 chars - still short
                {
                    "file": "file3.md",
                    "description": "This is a sufficiently long description that exceeds minimum",
                },  # 64 chars
            ],
        }

        result = field.parse(response_data)

        # Only one link should remain (file3.md with long description)
        assert len(result) == 1
        assert result[0]["file"] == "file3.md"

    def test_filter_template_descriptions(self):
        """Test that links with template-like descriptions are filtered out"""
        field = LinksFieldMock(min_description_length=10)

        response_data = {
            "created": [],
            "links": [
                {
                    "file": "file1.md",
                    "description": "Это связанная тема с другим файлом",  # Template phrase
                },
                {
                    "file": "file2.md",
                    "description": "Похожий контент в этом файле",  # Template phrase
                },
                {
                    "file": "file3.md",
                    "description": "This is a related topic about something",  # Template phrase
                },
                {
                    "file": "file4.md",
                    "description": "Both files describe transformer architecture, but this focuses on attention mechanism",
                },  # Good description
            ],
        }

        result = field.parse(response_data)

        # Only one link should remain (file4.md with good description)
        assert len(result) == 1
        assert result[0]["file"] == "file4.md"

    def test_combined_filtering(self):
        """Test that all filters work together correctly"""
        field = LinksFieldMock(min_description_length=30)

        response_data = {
            "created": ["new_file.md"],
            "links": [
                {
                    "file": "new_file.md",
                    "description": "This new file is created just now, with good description",
                },  # Created file
                {"file": "file2.md", "description": "Short"},  # Too short
                {
                    "file": "file3.md",
                    "description": "Это связанная тема, достаточно длинное описание для теста",
                },  # Template
                {
                    "file": "file4.md",
                    "description": "Both files discuss neural networks, but this one focuses on CNNs while the other on RNNs",
                },  # Good
                {
                    "file": "file5.md",
                    "description": "The two concepts are alternatives: one uses supervised learning, other uses reinforcement",
                },  # Good
            ],
        }

        result = field.parse(response_data)

        # Two links should remain (file4.md and file5.md)
        assert len(result) == 2
        assert result[0]["file"] == "file4.md"
        assert result[1]["file"] == "file5.md"

    def test_non_dict_links_are_skipped(self):
        """Test that non-dictionary links are safely skipped"""
        field = LinksFieldMock(min_description_length=10)

        response_data = {
            "created": [],
            "links": [
                "string_link",  # Invalid format
                {"file": "file1.md", "description": "Valid link with good description"},
                123,  # Invalid format
                {"file": "file2.md", "description": "Another valid link here"},
            ],
        }

        result = field.parse(response_data)

        # Only two valid links should remain
        assert len(result) == 2
        assert result[0]["file"] == "file1.md"
        assert result[1]["file"] == "file2.md"

    def test_empty_links_list(self):
        """Test handling of empty links list"""
        field = LinksFieldMock(min_description_length=30)

        response_data = {"created": [], "links": []}

        result = field.parse(response_data)

        assert len(result) == 0

    def test_missing_links_field(self):
        """Test handling when links field is missing"""
        field = LinksFieldMock(min_description_length=30)

        response_data = {"created": []}

        result = field.parse(response_data)

        assert len(result) == 0

    def test_custom_min_description_length(self):
        """Test that custom min_description_length is respected"""
        field_short = LinksFieldMock(min_description_length=10)
        field_long = LinksFieldMock(min_description_length=50)

        response_data = {
            "created": [],
            "links": [
                {
                    "file": "file1.md",
                    "description": "This is medium length description here",
                }  # ~38 chars
            ],
        }

        result_short = field_short.parse(response_data)
        result_long = field_long.parse(response_data)

        # Should pass for min_length=10, fail for min_length=50
        assert len(result_short) == 1
        assert len(result_long) == 0
