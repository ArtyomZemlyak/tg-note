"""
Response Formatter
Unified response formatting for all agents in Telegram
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.bot.settings_manager import SettingsManager
from src.bot.utils import escape_html, escape_markdown_url


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

    def to_html(self, value: Any) -> str:
        """
        Convert field value to HTML format.

        Args:
            value: Field value to convert

        Returns:
            str: HTML formatted string
        """
        if value is None:
            return ""
        # For simple text values, we need to escape HTML special characters
        text_value = str(value)
        return self._escape_html(text_value)

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

    def _escape_html(self, text: str) -> str:
        """
        Escape special HTML characters in text.

        Args:
            text: Text to escape

        Returns:
            str: Escaped text
        """
        return escape_html(text)


class SummaryField(BaseField):
    """Summary field for response format."""

    def __init__(self):
        super().__init__(
            "summary",
            "Краткое описание выполненной работы (3-5 предложений)."
            "Если нужно форматирование - то в HTML для телеграм. Можно использовать только следующие теги: <b> or <strong> for bold text"
            "<i> or <em> for italic text"
            "<u> or <ins> for underlined text"
            "<s>, <strike>, or <del> for strikethrough text"
            '<span class="tg-spoiler"> or <tg-spoiler> for spoiler text'
            '<a href="URL"> for inline links'
            "<code> for inline fixed-width code"
            "<pre> for pre-formatted fixed-width code blocks",
        )


class AnswerField(BaseField):
    """Answer field for response format."""

    def __init__(self):
        super().__init__(
            "answer",
            'Ответ на вопрос пользователя, если это был вопросный запрос. Поле "answer" заполняй только если пользователь задал вопрос.'
            "Если нужно форматирование - то в HTML для телеграм. Можно использовать только следующие теги: <b> or <strong> for bold text"
            "<i> or <em> for italic text"
            "<u> or <ins> for underlined text"
            "<s>, <strike>, or <del> for strikethrough text"
            '<span class="tg-spoiler"> or <tg-spoiler> for spoiler text'
            '<a href="URL"> for inline links'
            "<code> for inline fixed-width code"
            "<pre> for pre-formatted fixed-width code blocks",
        )


class FileListField(BaseField):
    """Base class for file list fields (created, edited, deleted, folders)."""

    def __init__(self, name: str, text: str, icon: str, github_url: str = None):
        super().__init__(name, text)
        self.icon = icon
        self.github_url = github_url

    def generate_example(self):
        """Generate example value for file list field."""
        ex = ["относительный_путь/к/файлу1.md", "относительный_путь/к/файлу2.md", "относительный_путь/к/папке"]
        return f"{ex}  # {self.text}"

    def parse(self, response_data: Dict, **kwargs) -> Any:
        """Parse file list field with formatting."""
        return response_data.get(self.name, [])

    def to_html(self, value: Any) -> str:
        """
        Convert file list to HTML format.

        Args:
            value: List of files

        Returns:
            str: HTML formatted string
        """
        if not value:
            return ""

        lines = [f"<b>{self.icon} {self._get_display_name()}:</b>"]
        for file_path in value:
            escaped_file_path = self._escape_html(file_path)
            if self.github_url:
                url = f"{self.github_url}/{file_path}"
                escaped_url = self._escape_html(url)
                lines.append(f'- <a href="{escaped_url}">{escaped_file_path}</a>')
            else:
                lines.append(f"- {escaped_file_path}")
        return "\n".join(lines)

    def to_md(self, value: Any) -> str:
        """
        Convert file list to markdown format.

        Args:
            value: List of files

        Returns:
            str: Markdown formatted string
        """
        if not value:
            return ""

        lines = [f"{self.icon} {self._get_display_name()}:"]
        for file_path in value:
            file_path = escape_markdown_url(file_path)
            if self.github_url:
                url = escape_markdown_url(f"{self.github_url}/{file_path}")
                lines.append(f"- [{file_path}]({url})")
            else:
                lines.append(f"- {file_path}")
        return "\n".join(lines)

    def _get_display_name(self) -> str:
        """Get display name for the field type."""
        return self.name.replace("_", " ").title()


class FilesCreatedField(FileListField):
    """Files created field for response format."""

    def __init__(self, github_url: str = None):
        super().__init__(
            "created",
            "Список созданных файлов и папок (пустой массив, если ничего не создано)",
            "✅",
            github_url,
        )

    def _get_display_name(self) -> str:
        return "Создано:"


class FilesEditedField(FileListField):
    """Files edited field for response format."""

    def __init__(self, github_url: str = None):
        super().__init__(
            "edited",
            "Список отредактированных файлов и папок (пустой массив, если ничего не отредактировано)",
            "✏️",
            github_url,
        )

    def _get_display_name(self) -> str:
        return "Отредактировано:"


class FilesDeletedField(FileListField):
    """Files deleted field for response format."""

    def __init__(self, github_url: str = None):
        super().__init__(
            "deleted",
            "Список удаленных файлов и папок (пустой массив, если ничего не удалено)",
            "❌",
            github_url,
        )

    def _get_display_name(self) -> str:
        return "Удалено:"


class LinksField(BaseField):
    """Links field for response format."""

    def __init__(self, github_url: str = None):
        super().__init__(
            "links",
            "# Список связей с другими файлами или папками или сущностями внутри файлов в базе знаний (только с СУЩЕСТВУЮЩИМИ сущностями, не с сущностями, созданными в текущем запуске)."
            '# Для каждой связи в "links" обязательно добавляй содержательное описание (1-2 предложения), объясняющее природу связи'
            "# `description` ДОЛЖЕН быть содержательным (1–2 предложения): объясни природу связи (общее, различия, зависимость, часть-целое, альтернатива, последовательность, перекрывающиеся теги/понятия)."
            '# Избегай шаблонов вроде "Связанная тема" или однословных описаний.'
            "# Очень важно чтобы связи были не просто вида -О, тут тоже говорится об ЛЛМ вот это да- , а чтобы связи отражали какие-то прям инсайты и глубинные связи",
        )
        self.github_url = github_url

    def generate_example(self):
        """Generate example value for links field."""
        ex = [
            {
                "file": "относительный_путь/к/связанному1.md",
                "description": "Подробное описание связи (1-2 предложения)",
            },
            {
                "file": "относительный_путь/к/связанному2.md",
                "description": "Подробное описание связи (1-2 предложения)",
            },
            {
                "file": "относительный_путь/к/связанной_папке",
                "description": "Подробное описание связи (1-2 предложения)",
            },
        ]
        return f"""{ex} {self.text}"""

    def parse(self, response_data: Dict, **kwargs) -> Any:
        """Parse links field with formatting."""
        return response_data.get("links", [])

    def to_html(self, value: Any) -> str:
        """
        Convert links list to HTML format.

        Args:
            value: List of links

        Returns:
            str: HTML formatted string
        """
        if not value:
            return ""

        lines = ["<b>🔗 Связанные файлы:</b>"]
        for link in value:
            if isinstance(link, dict):
                file_path = link.get("file", "")
                description = link.get("description", "")
                escaped_file_path = self._escape_html(file_path)
                escaped_description = self._escape_html(description)
                if self.github_url:
                    url = f"{self.github_url}/{file_path}"
                    escaped_url = self._escape_html(url)
                    lines.append(
                        f'- <a href="{escaped_url}">{escaped_file_path}</a>: {escaped_description}'
                    )
                else:
                    lines.append(f"- {escaped_file_path}: {escaped_description}")
            else:
                escaped_link = self._escape_html(str(link))
                lines.append(f"- {escaped_link}")

        return "\n".join(lines)

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

        lines = ["🔗 Связанные файлы:"]
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


class InsiteField(BaseField):
    """Answer field for response format."""

    def __init__(self):
        super().__init__(
            "insite",
            'Текстовое поле (str). Проанализируй контент сообщения, найденные тобой связи, информацию в базе знаний.'
            "И выведи по настоящему интересные инсайты:"
            "- потенциальные мощные прорывы"
            "- применение нескольких технологий вместе, которые дополняют друг друга"
            "- Каждый инсайт должен быть подкреплён чёткой причинно-следственной логикой:"
            "почему именно эта комбинация работает, какие ограничения она снимает, какие новые степени свободы открывает."
        )

    def to_html(self, value: Any) -> str:
        """
        Convert field value to HTML format.

        Args:
            value: Field value to convert

        Returns:
            str: HTML formatted string
        """
        if value is None:
            return ""
        # For simple text values, we need to escape HTML special characters
        text_value = f"<b>💡 Инсайты:</b>\n{value}"
        return self._escape_html(text_value)


class ResponseFormatter:
    """Class to represent and generate response format for agent prompts."""

    def __init__(self, github_url: str = None):
        self.fields: list[BaseField] = [
            SummaryField(),
            AnswerField(),
            FilesCreatedField(github_url),
            FilesEditedField(github_url),
            FilesDeletedField(github_url),
            LinksField(github_url),
            InsiteField(),

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
        example = {field.name: field.generate_example() for field in self.fields}

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
        import json
        import re

        # Find agent-result block
        match = re.search(r"```agent-result\s*\n(.*?)\n```", response_text, re.DOTALL)
        if match:
            try:
                json_text = match.group(1).strip()
                # Fix unescaped newlines in JSON strings
                json_text = self._fix_json_newlines(json_text)
                data = json.loads(json_text)
                parsed_data = {field.name: field.parse(data) for field in self.fields}
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

    def to_html(self, response_data: Dict[str, Any]) -> str:
        """
        Convert response data to HTML format.

        Args:
            response_data: Parsed response data

        Returns:
            str: HTML formatted string
        """
        lines = [field.to_html(response_data.get(field.name, None)) for field in self.fields]

        return "\n\n".join([l for l in lines if l])

    def to_md(self, response_data: Dict[str, Any]) -> str:
        """
        Convert response data to markdown format.

        Args:
            response_data: Parsed response data

        Returns:
            str: Markdown formatted string
        """
        lines = [field.to_md(response_data.get(field.name, None)) for field in self.fields]

        return "\n\n".join([l for l in lines if l])
