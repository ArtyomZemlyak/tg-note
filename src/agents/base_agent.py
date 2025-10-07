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
    STOP_WORDS,
    MAX_TITLE_LENGTH,
    MAX_SUMMARY_LENGTH,
    MAX_KEYWORD_COUNT,
    MIN_KEYWORD_LENGTH,
)


class KBStructure:
    """Knowledge Base structure definition from agent"""
    
    def __init__(
        self,
        category: str = "general",
        subcategory: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_path: Optional[str] = None
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
            "custom_path": self.custom_path
        }


@dataclass
class AgentResult:
    """
    Стандартизированный результат работы любого агента
    
    Все агенты возвращают этот формат:
    - markdown: Итоговый markdown контент
    - summary: Краткая суммаризация действий агента
    - files_created: Список созданных файлов
    - files_edited: Список отредактированных файлов
    - folders_created: Список созданных папок
    - metadata: Дополнительные метаданные
    - answer: Итоговый ответ пользователю (для режима ask)
    """
    markdown: str
    summary: str
    files_created: List[str] = field(default_factory=list)
    files_edited: List[str] = field(default_factory=list)
    folders_created: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    answer: Optional[str] = None  # For ask mode - final answer to user
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "markdown": self.markdown,
            "summary": self.summary,
            "files_created": self.files_created,
            "files_edited": self.files_edited,
            "folders_created": self.folders_created,
            "metadata": self.metadata,
            "answer": self.answer
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
    
    def parse_agent_response(self, response: str) -> AgentResult:
        """
        Парсит ответ агента в стандартизированном формате
        
        Ожидаемый формат в markdown:
        ```agent-result
        {
          "summary": "Краткая суммаризация действий",
          "files_created": ["path/to/file1.md", "path/to/file2.md"],
          "files_edited": ["path/to/file3.md"],
          "folders_created": ["path/to/folder1"],
          "metadata": {
            ...,
            "links": [
              {"file": "path/to/related.md", "description": "Related topic"}
            ]
          },
          "answer": "Итоговый ответ пользователю (для режима ask)"
        }
        ```
        
        Args:
            response: Ответ от агента (markdown)
        
        Returns:
            AgentResult с распарсенными данными
        """
        # Попытка извлечь JSON блок с результатами
        files_created = []
        files_edited = []
        folders_created = []
        summary = ""
        metadata = {}
        answer = None
        
        # Ищем блок ```agent-result
        result_match = re.search(r'```agent-result\s*\n(.*?)\n```', response, re.DOTALL)
        if result_match:
            try:
                json_text = result_match.group(1).strip()
                result_data = json.loads(json_text)
                
                # Ensure result_data is a dictionary
                if not isinstance(result_data, dict):
                    import logging
                    logging.warning(f"agent-result JSON is not a dictionary (type: {type(result_data).__name__}). Content: {json_text[:100]}")
                    # Fall back to simple parsing
                    result_data = {}
                
                summary = result_data.get("summary", "")
                files_created = result_data.get("files_created", [])
                files_edited = result_data.get("files_edited", [])
                folders_created = result_data.get("folders_created", [])
                metadata = result_data.get("metadata", {})
                answer = result_data.get("answer")  # Extract answer for ask mode
            except json.JSONDecodeError as e:
                # Если не удалось распарсить JSON, используем простой парсинг
                # Log the error for debugging
                import logging
                logging.warning(f"Failed to parse agent-result JSON: {e}. Content: {result_match.group(1)[:100]}")
                pass
        
        # Фоллбэк: попытка найти информацию в тексте
        if not summary:
            # Ищем секцию Summary
            summary_match = re.search(r'##\s*Summary\s*\n(.*?)(?=\n##|\Z)', response, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
            else:
                summary = "Agent completed processing"
        
        # Ищем упоминания созданных файлов
        if not files_created:
            files_created = re.findall(r'(?:Created file|✓ Created):?\s*[`"]?([\w\-/.]+\.md)[`"]?', response)
        
        # Ищем упоминания отредактированных файлов  
        if not files_edited:
            files_edited = re.findall(r'(?:Edited file|✓ Edited|Updated):?\s*[`"]?([\w\-/.]+\.md)[`"]?', response)
        
        # Ищем упоминания созданных папок
        if not folders_created:
            folders_created = re.findall(r'(?:Created folder|✓ Created folder):?\s*[`"]?([\w\-/]+)[`"]?', response)
        
        return AgentResult(
            markdown=response,
            summary=summary,
            files_created=files_created,
            files_edited=files_edited,
            folders_created=folders_created,
            metadata=metadata,
            answer=answer
        )
    
    def extract_kb_structure_from_response(self, response: str, default_category: str = "general") -> KBStructure:
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
        metadata_match = re.search(r'```metadata\s*\n(.*?)\n```', response, re.DOTALL)
        if metadata_match:
            metadata_text = metadata_match.group(1)
            for line in metadata_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == 'category' and value:
                        category = value
                    elif key == 'subcategory' and value:
                        subcategory = value
                    elif key == 'tags' and value:
                        tags = [t.strip() for t in value.split(',') if t.strip()]
        
        return KBStructure(
            category=category,
            subcategory=subcategory,
            tags=tags
        )
    
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