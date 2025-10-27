"""
Base Agent
Abstract base class for all agents
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config.agent_prompts import (
    CATEGORY_KEYWORDS,
    DEFAULT_CATEGORY,
    MAX_KEYWORD_COUNT,
    MAX_SUMMARY_LENGTH,
    MAX_TITLE_LENGTH,
    MIN_KEYWORD_LENGTH,
    STOP_WORDS,
)


class KBStructure:
    """Knowledge Base structure definition from agent"""

    def __init__(
        self,
        category: str = "general",
        subcategory: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_path: Optional[str] = None,
    ):
        """
        Initialize KB structure

        Args:
            category: Main category (e.g., "ai", "biology", "physics")
            subcategory: Optional subcategory (e.g., "machine-learning", "genetics")
            tags: Optional list of tags for the content
            custom_path: Optional custom relative path from KB root
        """
        self.category = category
        self.subcategory = subcategory
        self.tags = tags or []
        self.custom_path = custom_path

    def get_relative_path(self) -> str:
        """
        Get relative path for the article based on structure

        Returns:
            Relative path string (e.g., "topics/ai/machine-learning")
        """
        if self.custom_path:
            return self.custom_path

        # Ensure category is valid (not None or empty)
        category = self.category if self.category else "general"

        parts = ["topics", category]
        if self.subcategory:
            parts.append(self.subcategory)

        # Filter out None values to prevent join errors
        parts = [str(p) for p in parts if p is not None]

        return "/".join(parts)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "tags": self.tags,
            "custom_path": self.custom_path,
        }




class BaseAgent(ABC):
    """Abstract base class for content processing agents"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    @abstractmethod
    async def process(self, content: Dict) -> Dict:
        """
        Process content and return structured output with KB structure

        Args:
            content: Content dictionary with text, urls, etc.

        Returns:
            Processed content dictionary with:
            - markdown: str - formatted markdown content
            - title: str - article title
            - metadata: Dict - article metadata
            - kb_structure: KBStructure - where to save the article
        """
        pass

    @abstractmethod
    def validate_input(self, content: Dict) -> bool:
        """
        Validate input content

        Args:
            content: Content to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    def parse_agent_response(self, response: str) -> Dict[str, Any]:
        """
        Парсит ответ агента в стандартизированном формате используя ResponseFormatter

        Args:
            response: Ответ от агента (markdown)

        Returns:
            Dict с распарсенными данными
        """
        # Используем ResponseFormatter для парсинга
        from src.bot.response_formatter import ResponseFormatter
        formatter = ResponseFormatter()
        return formatter.parse(response)

    def extract_kb_structure_from_response(
        self, response: str, default_category: str = "general"
    ) -> KBStructure:
        """
        Извлекает KB структуру из ответа агента

        Агент должен указать в своем ответе метаданные в формате:
        ```metadata
        category: ai
        subcategory: models
        tags: gpt, transformer, llm
        ```

        Args:
            response: Ответ от агента
            default_category: Категория по умолчанию

        Returns:
            KBStructure
        """
        category = default_category
        subcategory = None
        tags = []

        # Ищем блок метаданных
        metadata_match = re.search(r"```metadata\s*\n(.*?)\n```", response, re.DOTALL)
        if metadata_match:
            metadata_text = metadata_match.group(1)
            for line in metadata_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if key == "category" and value:
                        category = value
                    elif key == "subcategory" and value:
                        subcategory = value
                    elif key == "tags" and value:
                        tags = [t.strip() for t in value.split(",") if t.strip()]

        return KBStructure(category=category, subcategory=subcategory, tags=tags)

    # Helper methods for content analysis (shared across all agents)

    @staticmethod
    def extract_keywords(text: str, top_n: int = MAX_KEYWORD_COUNT) -> List[str]:
        """
        Extract keywords from text (simple implementation)

        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to return

        Returns:
            List of keywords
        """
        # Use stop words from config
        stop_words = STOP_WORDS

        # Simple word frequency
        words = text.lower().split()
        word_freq = {}

        for word in words:
            # Remove punctuation
            word = word.strip(".,!?;:()[]{}\"'")
            if len(word) > MIN_KEYWORD_LENGTH and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        return [word for word, _ in sorted_words[:top_n]]

    @staticmethod
    def detect_category(text: str) -> str:
        """
        Detect content category using keywords from config

        Args:
            text: Text to analyze

        Returns:
            Category name
        """
        text_lower = text.lower()

        # Use category keywords from config
        categories = CATEGORY_KEYWORDS

        # Count matches for each category
        category_scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score

        # Return category with highest score
        if category_scores:
            return max(category_scores, key=category_scores.get)

        return DEFAULT_CATEGORY

    @staticmethod
    def generate_title(text: str, max_length: int = MAX_TITLE_LENGTH) -> str:
        """
        Generate title from text

        Args:
            text: Text to generate title from
            max_length: Maximum title length

        Returns:
            Generated title
        """
        # Try first line
        lines = text.strip().split("\n")
        first_line = lines[0].strip() if lines else ""

        # Clean up
        first_line = first_line.lstrip("#").strip()

        if len(first_line) > max_length:
            return first_line[:max_length].strip() + "..."

        return first_line or "Untitled Note"

    @staticmethod
    def generate_summary(text: str, max_length: int = MAX_SUMMARY_LENGTH) -> str:
        """
        Generate summary from text

        Args:
            text: Text to summarize
            max_length: Maximum summary length

        Returns:
            Summary text
        """
        # Simple summary: first paragraph or first N characters
        paragraphs = text.split("\n\n")
        first_para = paragraphs[0].strip() if paragraphs else ""

        if len(first_para) > max_length:
            return first_para[:max_length].strip() + "..."

        return first_para or ""

    def _fix_json_newlines(self, json_text: str) -> str:
        """
        Исправляет неэкранированные переносы строк в JSON

        Проблема: агент может генерировать JSON с неэкранированными \n в строках,
        что приводит к ошибке парсинга JSON.

        Args:
            json_text: Исходный JSON текст

        Returns:
            Исправленный JSON текст
        """
        import re

        # AICODE-FIX: Более надежное исправление JSON
        # Сначала убираем лишние пробелы и переносы строк в начале/конце
        json_text = json_text.strip()

        # Ищем строковые значения в JSON и экранируем переносы строк
        def fix_string_value(match):
            key = match.group(1)
            value = match.group(2)

            # Экранируем переносы строк в значении
            value = value.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            # Убираем лишние пробелы
            value = value.strip()

            return f'"{key}": "{value}"'

        # Паттерн для поиска строковых пар ключ-значение
        # Ищем "key": "value" где value может содержать переносы строк
        pattern = r'"([^"]+)":\s*"([^"]*(?:\\.[^"]*)*)"'

        # Применяем исправления
        fixed_json = re.sub(pattern, fix_string_value, json_text)

        # AICODE-FIX: Дополнительная очистка - убираем лишние запятые в конце
        # Убираем запятую перед закрывающей скобкой
        fixed_json = re.sub(r",\s*}", "}", fixed_json)
        fixed_json = re.sub(r",\s*]", "]", fixed_json)

        return fixed_json
