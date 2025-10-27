"""
Response Formatter
Unified response formatting for all agents in Telegram
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from src.bot.settings_manager import SettingsManager
from src.bot.utils import escape_markdown, escape_markdown_url, split_long_message


class BaseField:
    """Base class for response fields."""
    
    def __init__(self, name: str, text: str):
        self.name = name
        self.text = text
    
    def parse(self, response_data: Dict, **kwargs) -> Any:
        """
        Parse field from response data.
        
        Args:
            response_data: Agent response data
            **kwargs: Additional arguments for parsing
            
        Returns:
            Any: Parsed field data
        """
        return response_data.get(self.name, "")
    
    def to_md(self, value: Any) -> str:
        """
        Convert field value to markdown format.
        
        Args:
            value: Field value to convert
            
        Returns:
            str: Markdown formatted string
        """
        if value is None:
            return ""
        return str(value)
    
    def generate_example(self):
        """
        Generate example value for the field.
        
        Returns:
            Example value for the field
        """
        return self.text


class SummaryField(BaseField):
    """Summary field for response format."""
    
    def __init__(self):
        super().__init__(
            "summary",
            "Краткое описание выполненной работы (3-5 предложений)"
        )


class AnswerField(BaseField):
    """Answer field for response format."""
    
    def __init__(self):
        super().__init__(
            "answer",
            'Ответ на вопрос пользователя, если это был вопросный запрос. Поле "answer" заполняй только если пользователь задал вопрос'
        )


class FilesCreatedField(BaseField):
    """Files created field for response format."""
    
    def __init__(self, github_url: str = None):
        super().__init__(
            "files_created",
            "Список созданных файлов (пустой массив, если ничего не создано)"
        )
        self.github_url = github_url
    
    def generate_example(self):
        """Generate example value for files created field."""
        ex = ["путь/к/файлу1.md", "путь/к/файлу2.md"]
        return f"{ex}  # {self.text}"
    
    def parse(self, response_data: Dict, **kwargs) -> Any:
        """Parse files created field with formatting."""
        files_created = response_data.get("files_created", [])
        # Implementation will be similar to _format_file_changes for created files
        return files_created
    
    def to_md(self, value: Any) -> str:
        """
        Convert files created list to markdown format.
        
        Args:
            value: List of created files
            
        Returns:
            str: Markdown formatted string
        """
        if not value:
            return ""
        
        lines = ["✅ **Созданные файлы:**"]
        for file_path in value:
            file_path = escape_markdown_url(file_path)
            if self.github_url:
                url = escape_markdown_url(f"{self.github_url}/{file_path}")
                lines.append(f"- [{file_path}]({url})")
            else:
                lines.append(f"- {file_path}")
        return "\n".join(lines)


class FilesEditedField(BaseField):
    """Files edited field for response format."""
    
    def __init__(self, github_url: str = None):
        super().__init__(
            "files_edited",
            "Список отредактированных файлов (пустой массив, если ничего не отредактировано)"
        )
        self.github_url = github_url
    
    def generate_example(self):
        """Generate example value for files edited field."""
        ex = ["путь/к/файлу3.md"]
        return f"{ex}  # {self.text}"
    
    def parse(self, response_data: Dict, **kwargs) -> Any:
        """Parse files edited field with formatting."""
        files_edited = response_data.get("files_edited", [])
        # Implementation will be similar to _format_file_changes for edited files
        return files_edited
    
    def to_md(self, value: Any) -> str:
        """
        Convert files edited list to markdown format.
        
        Args:
            value: List of edited files
            
        Returns:
            str: Markdown formatted string
        """
        if not value:
            return ""
        
        lines = ["✏️ **Отредактированные файлы:**"]
        for file_path in value:
            file_path = escape_markdown_url(file_path)
            if self.github_url:
                url = escape_markdown_url(f"{self.github_url}/{file_path}")
                lines.append(f"- [{file_path}]({url})")
            else:
                lines.append(f"- {file_path}")
        return "\n".join(lines)


class FilesDeletedField(BaseField):
    """Files deleted field for response format."""
    
    def __init__(self, github_url: str = None):
        super().__init__(
            "files_deleted",
            "Список удаленных файлов (пустой массив, если ничего не удалено)"
        )
        self.github_url = github_url
    
    def generate_example(self):
        """Generate example value for files deleted field."""
        ex = ["путь/к/файлу4.md"]
        return f"{ex}  # {self.text}"
    
    def parse(self, response_data: Dict, **kwargs) -> Any:
        """Parse files deleted field with formatting."""
        files_deleted = response_data.get("files_deleted", [])
        # Implementation will be similar to _format_file_changes for deleted files
        return files_deleted
    
    def to_md(self, value: Any) -> str:
        """
        Convert files deleted list to markdown format.
        
        Args:
            value: List of deleted files
            
        Returns:
            str: Markdown formatted string
        """
        if not value:
            return ""
        
        lines = ["❌ **Удаленные файлы:**"]
        for file_path in value:
            file_path = escape_markdown_url(file_path)
            if self.github_url:
                url = escape_markdown_url(f"{self.github_url}/{file_path}")
                lines.append(f"- [{file_path}]({url})")
            else:
                lines.append(f"- {file_path}")
        return "\n".join(lines)


class FoldersCreatedField(BaseField):
    """Folders created field for response format."""
    
    def __init__(self, github_url: str = None):
        super().__init__(
            "folders_created",
            "Список созданных папок (пустой массив, если ничего не создано)"
        )
        self.github_url = github_url
    
    def generate_example(self):
        """Generate example value for folders created field."""
        ex = ["путь/к/папке"]
        return f"{ex}  # {self.text}"
    
    def parse(self, response_data: Dict, **kwargs) -> Any:
        """Parse folders created field with formatting."""
        folders_created = response_data.get("folders_created", [])
        # Implementation will be similar to _format_file_changes for folders
        return folders_created
    
    def to_md(self, value: Any) -> str:
        """
        Convert folders created list to markdown format.
        
        Args:
            value: List of created folders
            
        Returns:
            str: Markdown formatted string
        """
        if not value:
            return ""
        
        lines = ["📁 **Созданные папки:**"]
        for folder_path in value:
            folder_path = escape_markdown_url(folder_path)
            if self.github_url:
                url = escape_markdown_url(f"{self.github_url}/{folder_path}")
                lines.append(f"- [{folder_path}]({url})")
            else:
                lines.append(f"- {folder_path}")
        return "\n".join(lines)


class LinksField(BaseField):
    """Links field for response format."""
    
    def __init__(self, github_url: str = None):
        super().__init__(
            "links",
            'Список связей с другими файлами в базе знаний (только с СУЩЕСТВУЮЩИМИ файлами, не с файлами, созданными в текущем запуске). В поле "links" указывай только связи с СУЩЕСТВУЮЩИМИ файлами в базе знаний, не с файлами, созданными в текущем запуске. Для каждой связи в "links" обязательно добавляй содержательное описание (1-2 предложения), объясняющее природу связи'
        )
        self.github_url = github_url
    
    def generate_example(self):
        """Generate example value for links field."""
        ex = [
            {"file": "путь/к/связанному1.md", "description": "Подробное описание связи (1-2 предложения)"},
            {"file": "путь/к/связанному2.md", "description": "Подробное описание связи (1-2 предложения)"}
        ]
        return f"""
        {ex} # В поле `links` возвращай массив найденных связей с существующими файлами в базе знаний:
# - Каждая связь — объект с полями `file` (путь к связанному файлу) и `description`.
# - `description` ДОЛЖЕН быть содержательным (1–2 предложения): объясни природу связи (общее, различия, зависимость, часть-целое, альтернатива, последовательность, перекрывающиеся теги/понятия).
# - Избегай шаблонов вроде "Связанная тема" или однословных описаний.
# - Не включай связи на файлы, которые ты только что создал в текущем запуске.
# {self.text}
"""
    
    def parse(self, response_data: Dict, **kwargs) -> Any:
        """Parse links field with formatting."""
        links = response_data.get("links", [])
        return links
    
    def to_md(self, value: Any) -> str:
        """
        Convert links list to markdown format.
        
        Args:
            value: List of links
            
        Returns:
            str: Markdown formatted string
        """
        if not value:
            return ""
        
        lines = ["**Связанные файлы:**"]
        for link in value:
            if isinstance(link, dict):
                file_path = link.get("file", "")
                description = link.get("description", "")
                file_path = escape_markdown_url(file_path)
                if self.github_url:
                    url = escape_markdown_url(f"{self.github_url}/{file_path}")
                    lines.append(f"- [{file_path}]({url}): {description}")
                else:
                    lines.append(f"- {file_path}: {description}")
            else:
                link = escape_markdown_url(link)
                lines.append(f"- {str(link)}")
        return "\n".join(lines)


class ResponseFormatter:
    """Class to represent and generate response format for agent prompts."""
    
    def __init__(self, github_url: str = None):
        self.fields: list[BaseField] = [
            SummaryField(),
            AnswerField(),
            FilesCreatedField(github_url),
            FilesEditedField(github_url),
            FilesDeletedField(github_url),
            FoldersCreatedField(github_url),
            LinksField(github_url)
        ]

    def generate_prompt_text(self) -> str:
        """
        Generate the complete prompt text for ResponseFormatter.
        
        Returns:
            str: Formatted prompt text
        """
        from src.prompts.registry import prompt_registry
        
        # Load the prompt template
        prompt_template = prompt_registry.get("response_formatter.instruction", locale="ru")
        
        # Generate the values for placeholders
        example = {
            field.name: field.generate_example()
            for field in self.fields
        }

        # Convert to JSON string for use in prompt
        import json
        response_format = json.dumps(example, ensure_ascii=False, indent=2)
        
        # Replace placeholders with actual values
        prompt_text = prompt_template.replace("{response_format}", response_format)
        
        return prompt_text

    def parse(self, response_text: str) -> Dict[str, Any]:
        """
        Parse agent response text to extract structured data.
        
        Args:
            response_text: Agent response text containing agent-result block
            
        Returns:
            Dict with parsed response data
        """
        import re
        import json
        
        # Find agent-result block
        match = re.search(r"```agent-result\s*\n(.*?)\n```", response_text, re.DOTALL)
        if match:
            try:
                json_text = match.group(1).strip()
                # Fix unescaped newlines in JSON strings
                json_text = self._fix_json_newlines(json_text)
                data = json.loads(json_text)
                parsed_data = {
                    field.name: field.parse(data)
                    for field in self.fields
                }
                return parsed_data
            except json.JSONDecodeError:
                # If JSON parsing fails, return empty dict
                pass
        
        # Return empty dict if no valid agent-result block found
        return {}
    
    def _fix_json_newlines(self, json_text: str) -> str:
        """
        Fix unescaped newlines in JSON strings.
        
        Args:
            json_text: Raw JSON text
            
        Returns:
            Fixed JSON text
        """
        import re
        
        # Pattern to match string values and escape newlines
        def fix_string_value(match):
            key = match.group(1)
            value = match.group(2)
            # Escape newlines, carriage returns, and tabs
            value = value.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
            return f'"{key}": "{value}"'
        
        # Pattern for key-value pairs in JSON
        pattern = r'"([^"]+)":\s*"([^"]*(?:\\.[^"]*)*)"'
        fixed_json = re.sub(pattern, fix_string_value, json_text)
        
        # Remove trailing commas before closing braces/brackets
        fixed_json = re.sub(r",\s*}", "}", fixed_json)
        fixed_json = re.sub(r",\s*]", "]", fixed_json)
        
        return fixed_json
    
    def to_md(self, response_data: Dict[str, Any]) -> str:
        """
        Convert response data to markdown format.
        
        Args:
            response_data: Parsed response data
            
        Returns:
            str: Markdown formatted string
        """
        lines = [
            field.to_md(response_data.get(field.name, None))
            for field in self.fields
        ]

        return "\n".join(lines)
