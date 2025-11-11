import pytest

from src.bot.response_formatter import LinksField, _fix_duplicate_topics_in_url


@pytest.fixture
def links_field():
    return LinksField()


def test_links_field_filters_created_files(links_field):
    response_data = {
        "links": [
            {
                "file": "topics/new-entry.md",
                "description": "Ссылка на файл, созданный в текущем запуске.",
            },
            {
                "file": "topics/existing-entry.md",
                "description": "Связь с ранее созданной заметкой.",
            },
        ],
        "created": ["topics/new-entry.md"],
    }

    parsed = links_field.parse(response_data)

    assert len(parsed) == 1
    remaining = parsed[0]
    assert remaining["granularity"] == "auto"
    assert remaining["description"] == "Связь с ранее созданной заметкой."
    assert remaining["targets"] == [
        {
            "path": "topics/existing-entry.md",
            "type": "file",
            "anchor": None,
            "label": None,
        }
    ]


def test_links_field_supports_grouped_targets(links_field):
    response_data = {
        "links": [
            {
                "files": [
                    "topics/ai/transformers.md",
                    "topics/ai/multi_head_attention.md",
                ],
                "granularity": "summary",
                "description": "Общие материалы по трансформерам.",
            }
        ]
    }

    parsed = links_field.parse(response_data)

    assert len(parsed) == 1
    grouped = parsed[0]
    assert grouped["granularity"] == "summary"
    assert grouped["description"] == "Общие материалы по трансформерам."
    assert grouped["targets"] == [
        {
            "path": "topics/ai/transformers.md",
            "type": "file",
            "anchor": None,
            "label": None,
        },
        {
            "path": "topics/ai/multi_head_attention.md",
            "type": "file",
            "anchor": None,
            "label": None,
        },
    ]


def test_links_field_to_html_handles_legacy_format(links_field):
    raw_links = [
        {
            "file": "topics/ai/transformers.md",
            "description": "Классический гайд по архитектуре трансформеров.",
        }
    ]

    html = links_field.to_html(raw_links)

    assert "Связанные сущности" in html
    assert "topics/ai/transformers.md" in html
    assert "Классический гайд" in html


def test_fix_duplicate_topics_in_url():
    """Test that duplicate topics/topics in URLs are fixed correctly."""
    # Test case 1: Simple duplicate
    url1 = "https://github.com/user/repo/blob/branch/topics/topics/ai/file.md"
    fixed1 = _fix_duplicate_topics_in_url(url1)
    assert fixed1 == "https://github.com/user/repo/blob/branch/topics/ai/file.md"

    # Test case 2: No duplicate (should remain unchanged)
    url2 = "https://github.com/user/repo/blob/branch/topics/ai/file.md"
    fixed2 = _fix_duplicate_topics_in_url(url2)
    assert fixed2 == url2

    # Test case 3: With anchor
    url3 = "https://github.com/user/repo/blob/branch/topics/topics/ai/file.md#anchor"
    fixed3 = _fix_duplicate_topics_in_url(url3)
    assert fixed3 == "https://github.com/user/repo/blob/branch/topics/ai/file.md#anchor"

    # Test case 4: Multiple duplicates (edge case)
    url4 = "https://github.com/user/repo/blob/branch/topics/topics/topics/ai/file.md"
    fixed4 = _fix_duplicate_topics_in_url(url4)
    assert fixed4 == "https://github.com/user/repo/blob/branch/topics/ai/file.md"
