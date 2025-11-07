from importlib import util
from pathlib import Path


def _load_bot_utils_module():
    spec = util.spec_from_file_location("bot_utils", Path("src/bot/utils.py"))
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


bot_utils = _load_bot_utils_module()


def test_nested_unordered_lists_retain_structure_without_tags():
    html = """
    <ul>
        <li>Когда на проде возникает ошибка, можно передать в агента логи</li>
        <li>Подробные логи позволяют агенту понять:
            <ul>
                <li>Что и как должно было происходить</li>
                <li>Где находится проблема</li>
                <li>Из-за чего она могла возникнуть</li>
            </ul>
        </li>
        <li>Это улучшает контекст</li>
    </ul>
    """

    sanitized = bot_utils.validate_telegram_html(html)

    assert "<ul" not in sanitized
    assert "<li" not in sanitized
    assert "• Когда на проде возникает ошибка, можно передать в агента логи" in sanitized
    assert (
        "• Подробные логи позволяют агенту понять" in sanitized
    ), "Top-level bullet text should be preserved"
    assert (
        "    • Что и как должно было происходить" in sanitized
    ), "Nested bullet should be indented with a bullet"
    assert "    • Где находится проблема" in sanitized
    assert "    • Из-за чего она могла возникнуть" in sanitized
    assert "• Это улучшает контекст" in sanitized


def test_ordered_lists_preserve_numbering_and_nested_items():
    html = """
    <ol>
        <li>Первый пункт</li>
        <li>Второй пункт
            <ul>
                <li>Вложенный пункт</li>
            </ul>
        </li>
    </ol>
    """

    sanitized = bot_utils.validate_telegram_html(html)

    assert "<ol" not in sanitized
    assert "1. Первый пункт" in sanitized
    assert "2. Второй пункт" in sanitized
    assert "  • Вложенный пункт" in sanitized


def test_html_entities_are_decoded():
    """Test that HTML entities like &lt;b&gt; are decoded to <b>"""
    # AICODE-NOTE: This is a critical test - escaped HTML should be unescaped
    html = "This is &lt;b&gt;bold&lt;/b&gt; text"

    sanitized = bot_utils.validate_telegram_html(html)

    assert "&lt;" not in sanitized
    assert "&gt;" not in sanitized
    assert "<b>bold</b>" in sanitized


def test_unclosed_tags_are_automatically_closed():
    """Test that unclosed tags are automatically closed"""
    html = "<b>Bold text without closing tag"

    sanitized = bot_utils.validate_telegram_html(html)

    assert sanitized == "<b>Bold text without closing tag</b>"


def test_improperly_nested_tags_are_fixed():
    """Test that improperly nested tags are fixed"""
    html = "<b>Bold <i>and italic</b> text</i>"

    sanitized = bot_utils.validate_telegram_html(html)

    # The validator should fix the nesting by closing tags in the right order
    # When </b> is encountered, it should close both <i> and <b>
    assert "<b>Bold <i>and italic</i></b>" in sanitized


def test_empty_tags_are_removed():
    """Test that empty tags like <b></b> are removed"""
    html = "Text with <b></b> empty <i></i> tags"

    sanitized = bot_utils.validate_telegram_html(html)

    assert "<b></b>" not in sanitized
    assert "<i></i>" not in sanitized
    assert sanitized.strip() == "Text with  empty  tags"


def test_mixed_escaped_and_normal_html():
    """Test handling of mixed escaped and normal HTML"""
    html = "Normal <b>bold</b> and escaped &lt;i&gt;italic&lt;/i&gt; text"

    sanitized = bot_utils.validate_telegram_html(html)

    assert "<b>bold</b>" in sanitized
    assert "<i>italic</i>" in sanitized
    assert "&lt;" not in sanitized


def test_complex_nested_structure_with_lists():
    """Test complex nested structure with bold, italic, and lists"""
    html = """
    <b>Основные принципы:</b><br>
    <ul>
        <li><b>Итеративность</b>: разбивать задачи</li>
        <li><b>Четкость</b>: формулировать конкретно</li>
    </ul>
    """

    sanitized = bot_utils.validate_telegram_html(html)

    assert "<b>Основные принципы:</b>" in sanitized
    assert "<br>" in sanitized
    assert "• <b>Итеративность</b>: разбивать задачи" in sanitized
    assert "• <b>Четкость</b>: формулировать конкретно" in sanitized
    assert "<ul" not in sanitized
    assert "<li" not in sanitized


def test_strong_and_em_tags_are_converted():
    """Test that <strong> and <em> are converted to <b> and <i>"""
    html = "<strong>Bold</strong> and <em>italic</em> text"

    sanitized = bot_utils.validate_telegram_html(html)

    assert "<b>Bold</b>" in sanitized
    assert "<i>italic</i>" in sanitized
    assert "<strong>" not in sanitized
    assert "<em>" not in sanitized


def test_link_with_escaped_url():
    """Test that links with special characters in URL are properly escaped"""
    html = '<a href="http://example.com?param=<value>">Link</a>'

    sanitized = bot_utils.validate_telegram_html(html)

    # URL should be escaped
    assert "&lt;" in sanitized
    assert "&gt;" in sanitized
    assert 'href="http://example.com?param=&lt;value&gt;"' in sanitized


def test_spoiler_tag_is_preserved():
    """Test that tg-spoiler span tags are preserved"""
    html = 'Normal text <span class="tg-spoiler">hidden text</span> more text'

    sanitized = bot_utils.validate_telegram_html(html)

    assert '<span class="tg-spoiler">hidden text</span>' in sanitized


def test_non_spoiler_span_is_removed():
    """Test that span tags without tg-spoiler class are removed"""
    html = '<span class="other-class">Some text</span>'

    sanitized = bot_utils.validate_telegram_html(html)

    assert "<span" not in sanitized
    assert "Some text" in sanitized


def test_self_closing_br_tags():
    """Test that self-closing br tags work correctly"""
    html = "Line 1<br/>Line 2<br>Line 3"

    sanitized = bot_utils.validate_telegram_html(html)

    assert "Line 1<br>Line 2<br>Line 3" in sanitized
