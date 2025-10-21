#!/usr/bin/env python3
"""
Тест для проверки исправленного шаблона ask режима
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

def test_ask_mode_template():
    """Тест исправленного шаблона ask режима"""
    
    # Симулируем ответ агента с исправленным форматом
    result_text = """# Ответ на вопрос о GPT-4

Я нашел информацию о GPT-4 в базе знаний.

```agent-result
{
  "summary": "Найден ответ в базе знаний",
  "files_created": [],
  "files_edited": [],
  "folders_created": [],
  "metadata": {
    "sources": ["ai/models/gpt4.md", "ai/multimodal/vision.md"],
    "related_topics": ["GPT-3", "Transformers", "Vision Models"]
  },
  "answer": "**GPT-4** - это большая языковая модель от OpenAI, четвертое поколение архитектуры GPT.\\n\\nОсновные характеристики:\\n- Мультимодальная модель (текст + изображения)\\n- Улучшенное понимание контекста\\n- Более высокая точность ответов\\n\\nПодробнее в файлах:\\n- `ai/models/gpt4.md` - основная информация\\n- `ai/multimodal/vision.md` - возможности работы с изображениями\\n\\nСвязанные темы: GPT-3, Transformers, Vision Models"
}
```

Дополнительная информация...
"""
    
    print("Тестируем исправленный шаблон ask режима...")
    print("=" * 60)
    
    try:
        # Парсим ответ
        agent_result = parse_agent_response(result_text)
        
        print(f"✅ Парсинг успешен!")
        print(f"Summary: {agent_result.summary}")
        print(f"Answer: {agent_result.answer[:100]}..." if agent_result.answer else "Answer: None")
        print(f"Files created: {agent_result.files_created}")
        print(f"Metadata: {agent_result.metadata}")
        
        # Проверяем, что все поля корректно извлечены
        assert agent_result.summary == "Найден ответ в базе знаний", f"Summary неверный: {agent_result.summary}"
        assert agent_result.answer is not None, "Answer поле не найдено!"
        assert "GPT-4" in agent_result.answer, "Answer не содержит ожидаемый контент!"
        assert "Мультимодальная модель" in agent_result.answer, "Answer не содержит ожидаемый контент!"
        assert agent_result.files_created == [], "Files created должен быть пустым списком"
        assert agent_result.files_edited == [], "Files edited должен быть пустым списком"
        assert agent_result.folders_created == [], "Folders created должен быть пустым списком"
        assert "sources" in agent_result.metadata, "Metadata должен содержать sources"
        assert "related_topics" in agent_result.metadata, "Metadata должен содержать related_topics"
        
        print("\n✅ Все проверки пройдены!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Запуск теста исправленного шаблона ask режима...")
    print("=" * 60)
    
    success = test_ask_mode_template()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Тест пройден успешно! Шаблон исправлен.")
    else:
        print("❌ Тест не прошел!")
        exit(1)