import pytest

from src.bot.response_formatter import LinksField


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
