"""
Тесты для форматирования прогресса (progress text formatting)
"""

import pytest

from src.services.progress_monitor import CheckboxItem, ProgressSnapshot


class MockBaseKBService:
    """Mock для тестирования _clean_checkbox_text"""

    def _clean_checkbox_text(self, text: str) -> str:
        """Очистка текста чекбокса от служебных слов и символов"""
        import re

        # Убираем "###", "##", "#" в начале
        text = re.sub(r"^#{1,6}\s+", "", text)

        # Убираем "Шаг N:" в начале
        text = re.sub(r"^Шаг\s+\d+:\s*", "", text)

        # Убираем "Этап N:" в начале
        text = re.sub(r"^Этап\s+\d+:\s*", "", text)

        # Убираем слова в начале: КРИТИЧНО, ВАЖНО, и т.д.
        text = re.sub(
            r"^(КРИТИЧНО|ВАЖНО|ОБЯЗАТЕЛЬНО|ВНИМАНИЕ)[:.\s]*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Убираем markdown ссылки, оставляем только текст
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Убираем множественные пробелы
        text = re.sub(r"\s+", " ", text)

        return text.strip()


class TestProgressTextCleaning:
    """Тесты очистки текста чекбоксов"""

    def test_clean_hash_symbols(self):
        """Тест удаления символов ###"""
        service = MockBaseKBService()

        # Когда есть и ### и Шаг N: - оба удаляются
        assert service._clean_checkbox_text("### Шаг 1: Анализ") == "Анализ"
        # Когда только Этап N: - удаляется и ## и Этап
        assert service._clean_checkbox_text("## Этап 2: Поиск") == "Поиск"
        # Когда только # и текст - убирается #
        assert service._clean_checkbox_text("# Заголовок") == "Заголовок"

    def test_clean_step_prefix(self):
        """Тест удаления префиксов Шаг N:"""
        service = MockBaseKBService()

        assert service._clean_checkbox_text("Шаг 1: Анализ контента") == "Анализ контента"
        assert service._clean_checkbox_text("Шаг 10: Проверка") == "Проверка"
        assert service._clean_checkbox_text("Этап 2: Поиск") == "Поиск"

    def test_clean_kritichno(self):
        """Тест удаления слов КРИТИЧНО, ВАЖНО и т.д."""
        service = MockBaseKBService()

        assert service._clean_checkbox_text("КРИТИЧНО: Обработать файлы") == "Обработать файлы"
        assert service._clean_checkbox_text("ВАЖНО Проверить данные") == "Проверить данные"
        assert service._clean_checkbox_text("важно: Тестирование") == "Тестирование"
        assert service._clean_checkbox_text("ОБЯЗАТЕЛЬНО сделать") == "сделать"

    def test_clean_markdown_links(self):
        """Тест удаления markdown ссылок"""
        service = MockBaseKBService()

        assert (
            service._clean_checkbox_text("[Инструкция для агента](qwen_code_cli/instruction.md)")
            == "Инструкция для агента"
        )
        assert (
            service._clean_checkbox_text("[Формат ответа](../response.md) прочитан")
            == "Формат ответа прочитан"
        )

    def test_clean_combined(self):
        """Тест комбинированной очистки"""
        service = MockBaseKBService()

        # Реальный пример из промпта
        text = "### Шаг 1: Определение типа источника"
        assert service._clean_checkbox_text(text) == "Определение типа источника"

        # Еще один реальный пример
        text = "КРИТИЧНО: [Стратегия поиска](../search.md) прочитана"
        assert service._clean_checkbox_text(text) == "Стратегия поиска прочитана"

        # Пример с несколькими проблемами
        text = "### Шаг 5: ВАЖНО: Создание структуры"
        assert service._clean_checkbox_text(text) == "Создание структуры"

    def test_clean_multiple_spaces(self):
        """Тест удаления множественных пробелов"""
        service = MockBaseKBService()

        assert service._clean_checkbox_text("Текст   с    пробелами") == "Текст с пробелами"
        assert service._clean_checkbox_text("  Пробелы  в начале  ") == "Пробелы в начале"

    def test_clean_real_examples(self):
        """Тест на реальных примерах из промптов"""
        service = MockBaseKBService()

        # Примеры из instruction_v5.md
        examples = [
            ("### Шаг 0: Язык", "Язык"),
            ("### Шаг 1: Определение типа источника", "Определение типа источника"),
            ("### Шаг 2: Многоэтапный поиск в базе знаний", "Многоэтапный поиск в базе знаний"),
            ("### Этап 1: Файловый поиск", "Файловый поиск"),
            ("КРИТИЧНО: Многоэтапная стратегия поиска", "Многоэтапная стратегия поиска"),
            (
                "[Инструкция для агента](qwen_code_cli/instruction_v5.md) прочитана",
                "Инструкция для агента прочитана",
            ),
        ]

        for input_text, expected in examples:
            assert service._clean_checkbox_text(input_text) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
