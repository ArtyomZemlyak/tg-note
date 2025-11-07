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
