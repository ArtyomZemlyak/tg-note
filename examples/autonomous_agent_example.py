"""
Пример использования автономного агента

Демонстрирует:
- Создание агента с OpenAI-compatible API
- Регистрацию тулзов
- Автономную работу агента
- Использование function calling
"""

import asyncio
import os
from pathlib import Path

from src.agents.openai_agent import OpenAIAgent


# ═══════════════════════════════════════════════════════════════════════════
# Реализация тулзов
# ═══════════════════════════════════════════════════════════════════════════

async def web_search_tool(params: dict) -> dict:
    """
    Тулз для поиска в интернете
    
    В реальности здесь будет API вызов к поисковику
    """
    query = params.get("query", "")
    print(f"🔍 Web Search: {query}")
    
    # Симуляция поиска
    return {
        "success": True,
        "query": query,
        "results": [
            {
                "title": "Example Result",
                "url": f"https://example.com/search?q={query}",
                "snippet": "This is an example search result..."
            }
        ]
    }


async def file_create_tool(params: dict) -> dict:
    """
    Тулз для создания файла
    
    ПРИМЕЧАНИЕ: В OpenAIAgent этот тулз уже встроен и работает с реальной файловой системой!
    Этот пример только для демонстрации, в продакшене используется встроенный file_create.
    """
    path = params.get("path", "")
    content = params.get("content", "")
    
    print(f"📝 File Create: {path}")
    print(f"Content length: {len(content)} characters")
    
    # Симуляция создания файла
    return {
        "success": True,
        "path": path,
        "message": f"File created: {path}"
    }


async def folder_create_tool(params: dict) -> dict:
    """
    Тулз для создания папки
    """
    path = params.get("path", "")
    print(f"📁 Folder Create: {path}")
    
    return {
        "success": True,
        "path": path,
        "message": f"Folder created: {path}"
    }


async def analyze_content_tool(params: dict) -> dict:
    """
    Тулз для анализа контента
    """
    text = params.get("text", "")
    print(f"🔬 Analyze Content: {len(text)} characters")
    
    # Простой анализ
    words = text.split()
    
    return {
        "success": True,
        "analysis": {
            "word_count": len(words),
            "char_count": len(text),
            "has_urls": "http" in text.lower(),
            "language": "unknown"
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# Примеры использования
# ═══════════════════════════════════════════════════════════════════════════

async def example_basic():
    """
    Базовый пример: агент анализирует текст и создает файл
    """
    print("\n" + "="*80)
    print("ПРИМЕР 1: Базовое использование с автоматическим созданием файлов в KB")
    print("="*80 + "\n")
    
    # Создать агента с указанием пути к базе знаний
    from pathlib import Path
    agent = OpenAIAgent(
        api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        model="qwen-max",
        max_iterations=5,
        kb_root_path=Path("./test_kb")  # Агент будет создавать файлы здесь
    )
    
    # ВАЖНО: file_create, file_edit, folder_create уже встроены в OpenAIAgent!
    # Нет необходимости регистрировать их вручную.
    # Регистрируем только дополнительные тулзы если нужны:
    # agent.register_tool("web_search", web_search_tool)
    # agent.register_tool("analyze_content", analyze_content_tool)
    
    # Задача
    content = {
        "text": """
        Машинное обучение - это раздел искусственного интеллекта,
        который позволяет системам автоматически улучшать свою работу
        на основе опыта без явного программирования.
        
        Основные типы машинного обучения:
        1. Обучение с учителем (supervised learning)
        2. Обучение без учителя (unsupervised learning)
        3. Обучение с подкреплением (reinforcement learning)
        """,
        "urls": ["https://en.wikipedia.org/wiki/Machine_learning"]
    }
    
    # Запустить агента
    print("🤖 Запуск агента...\n")
    
    result = await agent.process(content)
    
    print("\n" + "="*80)
    print("РЕЗУЛЬТАТ:")
    print("="*80)
    print(f"\nЗаголовок: {result['title']}")
    print(f"\nКатегория: {result['kb_structure'].category}")
    print(f"\nИтераций: {result['metadata']['iterations']}")
    print(f"\nИспользованные тулзы: {result['metadata']['tools_used']}")
    print(f"\n--- Markdown ---\n{result['markdown'][:500]}...")


async def example_with_custom_instruction():
    """
    Пример с кастомной инструкцией
    """
    print("\n" + "="*80)
    print("ПРИМЕР 2: Кастомная инструкция для научных статей")
    print("="*80 + "\n")
    
    custom_instruction = """
Ты специализированный агент для обработки научных статей.

Твоя задача:
1. Создай план анализа (plan_todo)
2. Проанализируй статью и извлеки:
   - Основную гипотезу
   - Методологию
   - Результаты
   - Выводы
3. Создай структуру папок для категоризации
4. Сохрани информацию в файлы

Используй тулзы:
- plan_todo: Создать план
- analyze_content: Анализ контента
- folder_create: Создание папок
- file_create: Создание файлов

Работай систематично и автономно.
"""
    
    agent = OpenAIAgent(
        api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="qwen-max",
        instruction=custom_instruction,
        max_iterations=8
    )
    
    # Зарегистрировать тулзы
    agent.register_tool("analyze_content", analyze_content_tool)
    agent.register_tool("folder_create", folder_create_tool)
    agent.register_tool("file_create", file_create_tool)
    
    content = {
        "text": """
        Research Paper: Deep Learning for Natural Language Processing
        
        Abstract:
        This study investigates the application of deep neural networks
        to various NLP tasks, including sentiment analysis and machine translation.
        
        Methodology:
        We used transformer-based models with self-attention mechanisms.
        The dataset consisted of 1M sentences from diverse sources.
        
        Results:
        Our model achieved 94.3% accuracy on sentiment classification
        and BLEU score of 42.1 on translation tasks.
        
        Conclusion:
        Deep learning shows significant promise for NLP applications.
        """,
        "urls": ["https://arxiv.org/abs/example"]
    }
    
    print("🤖 Запуск агента с кастомной инструкцией...\n")
    
    result = await agent.process(content)
    
    print("\n" + "="*80)
    print("РЕЗУЛЬТАТ:")
    print("="*80)
    print(f"\nВыполненные действия:")
    for execution in result['metadata']['executions']:
        status = "✓" if execution['success'] else "✗"
        print(f"  {status} {execution['tool_name']}: {execution.get('result', {}).get('message', 'OK')}")


async def example_error_handling():
    """
    Пример обработки ошибок
    """
    print("\n" + "="*80)
    print("ПРИМЕР 3: Обработка ошибок")
    print("="*80 + "\n")
    
    async def failing_tool(params: dict) -> dict:
        """Тулз который всегда падает"""
        raise Exception("This tool always fails!")
    
    agent = OpenAIAgent(
        api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="qwen-max",
        max_iterations=3
    )
    
    agent.register_tool("failing_tool", failing_tool)
    agent.register_tool("analyze_content", analyze_content_tool)
    
    content = {
        "text": "Test content for error handling"
    }
    
    print("🤖 Запуск агента (с ошибками)...\n")
    
    result = await agent.process(content)
    
    print("\n" + "="*80)
    print("РЕЗУЛЬТАТ (с обработкой ошибок):")
    print("="*80)
    print(f"\nОшибки в контексте: {result['metadata']['context']['errors']}")
    print(f"\nАгент всё равно вернул результат!")


# ═══════════════════════════════════════════════════════════════════════════
# Запуск примеров
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    """Запустить все примеры"""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                  ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ АВТОНОМНОГО АГЕНТА                ║
╚══════════════════════════════════════════════════════════════════════════╝

ВНИМАНИЕ: Это демонстрационные примеры с мок-тулзами.
Для реальной работы необходимо:
1. Установить openai: pip install openai
2. Настроить API ключи в .env
3. Зарегистрировать реальные тулзы

Примеры показывают:
- Как создавать агента
- Как регистрировать тулзы
- Как агент автономно планирует и выполняет задачи
- Как обрабатываются ошибки
""")
    
    # Проверка наличия API ключей
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY не установлен в .env")
        print("   Примеры будут использовать тестовый ключ\n")
    
    # Запустить примеры
    try:
        await example_basic()
        await example_with_custom_instruction()
        await example_error_handling()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\nЭто нормально для примеров без реального API.")
        print("Примеры показывают архитектуру и API агента.")
    
    print("\n" + "="*80)
    print("Примеры завершены!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
