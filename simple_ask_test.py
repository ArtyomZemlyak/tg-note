#!/usr/bin/env python3
"""
Упрощенный тест для проверки парсинга answer поля
"""

import re
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class AgentResult:
    """Упрощенная версия AgentResult для тестирования"""
    markdown: str
    summary: str
    files_created: List[str] = field(default_factory=list)
    files_edited: List[str] = field(default_factory=list)
    folders_created: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    answer: Optional[str] = None

def parse_agent_response(response: str) -> AgentResult:
    """
    Упрощенная версия парсинга ответа агента
    """
    # Инициализация значений по умолчанию
    files_created = []
    files_edited = []
    folders_created = []
    summary = ""
    metadata = {}
    answer = None

    # Ищем блок ```agent-result
    result_match = re.search(r"```agent-result\s*\n(.*?)\n```", response, re.DOTALL)
    if result_match:
        try:
            json_text = result_match.group(1).strip()
            result_data = json.loads(json_text)

            # Ensure result_data is a dictionary
            if not isinstance(result_data, dict):
                print(f"WARNING: agent-result JSON is not a dictionary (type: {type(result_data).__name__}). Content: {json_text[:100]}")
                result_data = {}

            summary = result_data.get("summary", "")
            files_created = result_data.get("files_created", [])
            files_edited = result_data.get("files_edited", [])
            folders_created = result_data.get("folders_created", [])
            metadata = result_data.get("metadata", {})
            answer = result_data.get("answer")  # Extract answer for ask mode
            
        except json.JSONDecodeError as e:
            print(f"WARNING: Failed to parse agent-result JSON: {e}. Content: {result_match.group(1)[:100]}")
            pass

    # Фоллбэк: попытка найти информацию в тексте
    if not summary:
        summary = "Agent completed processing"

    return AgentResult(
        markdown=response,
        summary=summary,
        files_created=files_created,
        files_edited=files_edited,
        folders_created=folders_created,
        metadata=metadata,
        answer=answer
    )

def test_parse_agent_result_with_answer():
    """Тест парсинга agent-result с полем answer"""
    
    # Тестовый ответ с answer полем (как должен быть в ask режиме)
    result_text = """# Ответ на вопрос

Вот подробный ответ на вопрос пользователя.

```agent-result
{
  "summary": "Найден ответ в базе знаний",
  "files_created": [],
  "files_edited": [],
  "folders_created": [],
  "metadata": {
    "sources": ["file1.md", "file2.md"],
    "related_topics": ["тема1", "тема2"]
  },
  "answer": "**GPT-4** - это большая языковая модель от OpenAI, четвертое поколение архитектуры GPT.\\n\\nОсновные характеристики:\\n- Мультимодальная модель (текст + изображения)\\n- Улучшенное понимание контекста\\n- Более высокая точность ответов\\n\\nПодробнее в файлах:\\n- `ai/models/gpt4.md` - основная информация\\n- `ai/multimodal/vision.md` - возможности работы с изображениями\\n\\nСвязанные темы: GPT-3, Transformers, Vision Models"
}
```

Дополнительная информация...
"""
    
    print("Тестируем парсинг agent-result с answer полем...")
    print("=" * 60)
    
    try:
        # Парсим ответ
        agent_result = parse_agent_response(result_text)
        
        print(f"✅ Парсинг успешен!")
        print(f"Summary: {agent_result.summary}")
        print(f"Answer: {repr(agent_result.answer[:200])}..." if agent_result.answer else "Answer: None")
        print(f"Files created: {agent_result.files_created}")
        print(f"Metadata: {agent_result.metadata}")
        
        # Проверяем, что answer поле корректно извлечено
        assert agent_result.answer is not None, "Answer поле не найдено!"
        assert "GPT-4" in agent_result.answer, "Answer не содержит ожидаемый контент!"
        assert "Мультимодальная модель" in agent_result.answer, "Answer не содержит ожидаемый контент!"
        
        print("\n✅ Все проверки пройдены!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parse_agent_result_without_answer():
    """Тест парсинга agent-result без поля answer (fallback)"""
    
    # Тестовый ответ без answer поля
    result_text = """# Обычный результат

```agent-result
{
  "summary": "Обычная обработка контента",
  "files_created": ["new_file.md"],
  "files_edited": [],
  "folders_created": [],
  "metadata": {}
}
```

Основной контент здесь.
"""
    
    print("\nТестируем парсинг agent-result без answer поля...")
    print("=" * 60)
    
    try:
        agent_result = parse_agent_response(result_text)
        
        print(f"✅ Парсинг успешен!")
        print(f"Summary: {agent_result.summary}")
        print(f"Answer: {agent_result.answer}")
        print(f"Files created: {agent_result.files_created}")
        
        # Проверяем, что answer поле None (как ожидается)
        assert agent_result.answer is None, "Answer должно быть None для обычного контента!"
        
        print("\n✅ Все проверки пройдены!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parse_invalid_json():
    """Тест парсинга с невалидным JSON"""
    
    # Тестовый ответ с невалидным JSON
    result_text = """# Ответ с ошибкой

```agent-result
{
  "summary": "Тест с ошибкой",
  "files_created": [],
  "files_edited": [],
  "folders_created": [],
  "metadata": {},
  "answer": "Ответ пользователю"
  // Ошибка: лишняя запятая
}
```

Контент...
"""
    
    print("\nТестируем парсинг с невалидным JSON...")
    print("=" * 60)
    
    try:
        agent_result = parse_agent_response(result_text)
        
        print(f"✅ Парсинг с fallback успешен!")
        print(f"Summary: {agent_result.summary}")
        print(f"Answer: {agent_result.answer}")
        
        # При невалидном JSON должен сработать fallback
        assert agent_result.summary == "Agent completed processing", "Должен сработать fallback!"
        
        print("\n✅ Fallback работает корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Запуск упрощенных тестов парсинга ask режима...")
    print("=" * 60)
    
    success = True
    success &= test_parse_agent_result_with_answer()
    success &= test_parse_agent_result_without_answer()
    success &= test_parse_invalid_json()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Все тесты пройдены успешно!")
    else:
        print("❌ Некоторые тесты не прошли!")
        exit(1)