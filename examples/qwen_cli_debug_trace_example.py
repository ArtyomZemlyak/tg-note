"""
Пример использования QwenCodeCLIAgent с детальным DEBUG логированием

Этот пример показывает, как включить детальный трейс выполнения qwen-code CLI агента.
Все вызовы CLI команды будут логироваться с подробной информацией:
- Полная команда и аргументы
- Входные данные (stdin/prompt)
- Выходные данные (stdout/stderr)
- Время выполнения
- Переменные окружения (без чувствительных данных)
"""

import asyncio
from pathlib import Path

from config.logging_config import setup_logging
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent


async def main():
    """
    Пример использования QwenCodeCLIAgent с DEBUG трейсингом
    """

    # === 1. Настройка логирования с DEBUG уровнем ===
    # Включаем DEBUG уровень для детального трейсинга
    setup_logging(
        log_level="DEBUG",  # Устанавливаем DEBUG уровень
        log_file=Path("logs/qwen_cli_debug_trace.log"),  # Путь к лог-файлу
        enable_debug_trace=True,  # Включаем детальный трейсинг
    )

    print("\n=== Qwen CLI Agent - DEBUG Трейсинг ===\n")
    print("Логирование включено с уровнем DEBUG")
    print("Все детали выполнения будут записаны в logs/qwen_cli_debug_trace.log")
    print("А также отображены в консоли\n")

    # === 2. Инициализация агента ===
    print("Инициализация агента...")
    try:
        agent = QwenCodeCLIAgent(
            enable_web_search=True, enable_git=True, enable_github=True, timeout=300  # 5 минут
        )
        print("✓ Агент успешно инициализирован\n")
    except RuntimeError as e:
        print(f"✗ Ошибка инициализации: {e}")
        print("\nПожалуйста, установите qwen CLI:")
        print(QwenCodeCLIAgent.get_installation_instructions())
        return

    # === 3. Подготовка тестового контента ===
    test_content = {
        "text": """
        Искусственный интеллект и машинное обучение

        Машинное обучение - это подраздел искусственного интеллекта, который
        фокусируется на создании систем, способных обучаться на основе данных.

        Основные направления ML:
        - Supervised Learning (обучение с учителем)
        - Unsupervised Learning (обучение без учителя)
        - Reinforcement Learning (обучение с подкреплением)

        Нейронные сети являются мощным инструментом для решения задач
        распознавания образов, обработки естественного языка и компьютерного зрения.
        """,
        "urls": ["https://example.com/ml-intro", "https://example.com/neural-networks"],
    }

    print("Контент для обработки подготовлен")
    print(f"Длина текста: {len(test_content['text'])} символов")
    print(f"Количество URL: {len(test_content['urls'])}\n")

    # === 4. Обработка контента с трейсингом ===
    print("Начинаем обработку контента...\n")
    print("=" * 60)
    print("СМОТРИТЕ ДЕТАЛЬНЫЙ ТРЕЙС В КОНСОЛИ И В ФАЙЛЕ ЛОГОВ:")
    print("- logs/qwen_cli_debug_trace.log (основной лог)")
    print("- logs/qwen_cli_debug_trace_debug.log (только DEBUG)")
    print("=" * 60)
    print()

    try:
        result = await agent.process(test_content)

        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ ОБРАБОТКИ")
        print("=" * 60)

        print(f"\n📄 Заголовок: {result['title']}")
        print(f"\n📁 KB Структура:")
        print(f"   - Категория: {result['kb_structure'].category}")
        print(f"   - Подкатегория: {result['kb_structure'].subcategory}")
        print(f"   - Теги: {', '.join(result['kb_structure'].tags)}")

        print(f"\n📝 Metadata:")
        for key, value in result["metadata"].items():
            if key not in ["processed_at"]:
                print(f"   - {key}: {value}")

        print(f"\n📄 Markdown контент (первые 300 символов):")
        print("-" * 60)
        print(result["markdown"][:300] + "...")
        print("-" * 60)

        print("\n✅ Обработка завершена успешно!")

    except Exception as e:
        print(f"\n✗ Ошибка обработки: {e}")
        print("\nПроверьте логи для получения детальной информации:")
        print("- logs/qwen_cli_debug_trace.log")
        print("- logs/qwen_cli_debug_trace_debug.log")
        raise

    # === 5. Информация о логах ===
    print("\n" + "=" * 60)
    print("ИНФОРМАЦИЯ О ЛОГИРОВАНИИ")
    print("=" * 60)
    print(
        """
Детальный трейс выполнения включает:

1. Проверка CLI (метод _check_cli_available):
   - Команда проверки версии
   - Return code, STDOUT, STDERR

2. Выполнение CLI (метод _execute_qwen_cli):
   - Полная команда и аргументы
   - Рабочая директория
   - Переменные окружения (с маскировкой чувствительных данных)
   - Полный STDIN (промпт)
   - Process ID
   - Время выполнения
   - Полный STDOUT (результат)
   - Полный STDERR (ошибки/предупреждения)

3. Обработка результата:
   - Парсинг ответа агента
   - Извлечение KB структуры
   - Формирование метаданных

Все логи доступны в:
- logs/qwen_cli_debug_trace.log (все уровни)
- logs/qwen_cli_debug_trace_debug.log (только DEBUG)
    """
    )


def show_debug_logging_info():
    """
    Показать информацию о настройке DEBUG логирования
    """
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║         КАК ИСПОЛЬЗОВАТЬ DEBUG ЛОГИРОВАНИЕ                   ║
╚══════════════════════════════════════════════════════════════╝

1. В вашем коде импортируйте setup_logging:

   from config.logging_config import setup_logging

2. Настройте логирование с DEBUG уровнем:

   setup_logging(
       log_level="DEBUG",                          # DEBUG уровень
       log_file=Path("logs/my_debug.log"),        # Путь к логу
       enable_debug_trace=True                     # Детальный трейс
   )

3. Используйте агент как обычно:

   agent = QwenCodeCLIAgent()
   result = await agent.process(content)

4. Проверьте логи:
   - logs/my_debug.log - основной лог
   - logs/my_debug_debug.log - только DEBUG сообщения

╔══════════════════════════════════════════════════════════════╗
║         ЧТО БУДЕТ ЛОГИРОВАТЬСЯ                               ║
╚══════════════════════════════════════════════════════════════╝

DEBUG логирование включает:

✓ CLI Проверка:
  - Команда: qwen --version
  - Return code, STDOUT, STDERR

✓ CLI Выполнение:
  - Полная команда: qwen [args]
  - Рабочая директория
  - Environment variables (с маскировкой API ключей)
  - STDIN (полный промпт)
  - Process ID
  - Время выполнения (в секундах)
  - STDOUT (полный результат)
  - STDERR (ошибки)

✓ Обработка:
  - Шаги процесса
  - Парсинг результата
  - Извлечение структуры
  - Метаданные

╔══════════════════════════════════════════════════════════════╗
║         УПРАВЛЕНИЕ УРОВНЯМИ ЛОГИРОВАНИЯ                      ║
╚══════════════════════════════════════════════════════════════╝

Уровни логирования:
- DEBUG   - Детальный трейс (все операции)
- INFO    - Общая информация (основные события)
- WARNING - Предупреждения (потенциальные проблемы)
- ERROR   - Ошибки (критические проблемы)

Рекомендации:
- Development: DEBUG (для отладки)
- Production: INFO или WARNING (производительность)
- Troubleshooting: DEBUG (поиск проблем)

    """
    )


if __name__ == "__main__":
    # Показать информацию о DEBUG логировании
    show_debug_logging_info()

    # Запустить пример
    asyncio.run(main())
