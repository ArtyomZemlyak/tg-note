"""
Response Formatter
Unified response formatting for all agents in Telegram
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.bot.settings_manager import SettingsManager
from src.bot.utils import escape_html, escape_markdown, escape_markdown_url


def _fix_duplicate_topics_in_url(url: str) -> str:
    """
    Fix duplicate 'topics/topics' in GitHub URLs.

    AICODE-NOTE: This function fixes the issue where paths already contain 'topics/'
    but the base URL also includes '/topics', resulting in 'topics/topics/...'.

    Args:
        url: GitHub URL that may contain duplicate topics

    Returns:
        URL with fixed duplicate topics

    Examples:
        >>> _fix_duplicate_topics_in_url("https://github.com/user/repo/blob/branch/topics/topics/ai/file.md")
        'https://github.com/user/repo/blob/branch/topics/ai/file.md'
        >>> _fix_duplicate_topics_in_url("https://github.com/user/repo/blob/branch/topics/ai/file.md")
        'https://github.com/user/repo/blob/branch/topics/ai/file.md'
        >>> _fix_duplicate_topics_in_url("https://github.com/user/repo/blob/branch/topics/topics/ai/file.md#anchor")
        'https://github.com/user/repo/blob/branch/topics/ai/file.md#anchor'
    """
    # Fix duplicate topics/topics pattern (can appear as /topics/topics/ or /topics/topics)
    # Replace all occurrences to handle multiple duplicates
    while "/topics/topics" in url:
        url = url.replace("/topics/topics", "/topics", 1)
    return url


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
            "Краткое описание выполненной работы (3-5 предложений). "
            "Для форматирования используй HTML теги для Telegram: <b>, <i>, <u>, <s>, <a href='URL'>, <code>, <pre>, <blockquote>, <span class='tg-spoiler'>. "
            "Для переноса строки используй символ новой строки (\\n). "
            "Полный список доступных тегов и правила использования указаны в инструкции ResponseFormatter.",
        )


class AnswerField(BaseField):
    """Answer field for response format."""

    def __init__(self):
        super().__init__(
            "answer",
            'Ответ на вопрос пользователя, если это был вопросный запрос. Поле "answer" заполняй только если пользователь задал вопрос. '
            "Для форматирования используй HTML теги для Telegram: <b>, <i>, <u>, <s>, <a href='URL'>, <code>, <pre>, <blockquote>, <span class='tg-spoiler'>. "
            "Для переноса строки используй символ новой строки (\\n). "
            "Полный список доступных тегов и правила использования указаны в инструкции ResponseFormatter.",
        )


class FileListField(BaseField):
    """Base class for file list fields (created, edited, deleted, folders)."""

    def __init__(self, name: str, text: str, icon: str, github_url: str = None):
        super().__init__(name, text)
        self.icon = icon
        self.github_url = github_url

    def generate_example(self):
        """Generate example value for file list field."""
        ex = [
            "относительный_путь/к/файлу1.md",
            "относительный_путь/к/файлу2.md",
            "относительный_путь/к/папке",
        ]
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
                url = _fix_duplicate_topics_in_url(url)
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
                url = f"{self.github_url}/{file_path}"
                url = _fix_duplicate_topics_in_url(url)
                url = escape_markdown_url(url)
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
            "# Список связей с другими файлами/папками/сущностями в базе знаний. Используй только объекты, "
            "которые существовали ДО текущего запуска (все, что создано прямо сейчас, перечислено в "
            "полях created/files_created/folders_created — их нужно исключить). Для каждой связи обязательно "
            "указывай содержательный `description` (1–2 предложения, объясняющие тип связи: сходство, "
            "зависимость, часть-целое, альтернатива, последовательность, пересечение тегов и т.п.). "
            "Можно агрегировать несколько целей в одну связь с помощью `files`, `folder` или массива `targets` "
            '({"path": "topics/ai/transformers.md", "label": "Обзор трансформеров"}). '
            'Для обобщённых групп устанавливай `granularity: "summary"`, для точечных ссылок — `granularity: "detailed"` '
            "и добавляй конкретику (файл + `anchor`, список конкретных сущностей). "
            "Избегай пустых и шаблонных описаний вроде «Связанная тема».",
        )
        self.github_url = github_url

    def generate_example(self):
        """Generate example value for links field."""
        example = [
            {
                "files": [
                    "topics/ai/transformers.md",
                    "topics/ai/multi_head_attention.md",
                ],
                "granularity": "summary",
                "description": (
                    "Сводная связь: обе заметки описывают архитектуру трансформеров и раскрывают разные аспекты "
                    "механизма внимания. Укажи, как они дополняют друг друга."
                ),
            },
            {
                "folder": "topics/ml/practical-cases",
                "granularity": "summary",
                "description": (
                    "Связь на уровне папки: здесь собраны практические кейсы, которые можно использовать как "
                    "следующий шаг после текущего материала."
                ),
            },
            {
                "file": "topics/ai/transformers.md#implementation-notes",
                "granularity": "detailed",
                "description": (
                    "Детализированная связь: секция с заметками по реализации расширяет рекомендации, описанные здесь."
                ),
            },
        ]
        return f"""{example} {self.text}"""

    def parse(self, response_data: Dict, **kwargs) -> Any:
        """Parse links field with formatting."""
        raw_links = response_data.get("links", [])
        if not isinstance(raw_links, list):
            return []

        created_paths = self._collect_created_paths(response_data)
        normalized_links: List[Dict[str, Any]] = []
        seen_keys: Set[Tuple] = set()

        for raw_link in raw_links:
            normalized = self._normalize_raw_link(raw_link)
            if not normalized:
                continue

            filtered_targets = self._filter_new_targets(normalized["targets"], created_paths)
            if not filtered_targets:
                continue

            normalized_link = {
                "description": normalized["description"],
                "granularity": normalized["granularity"],
                "targets": filtered_targets,
            }

            dedup_key = self._build_dedup_key(normalized_link)
            if dedup_key in seen_keys:
                continue

            seen_keys.add(dedup_key)
            normalized_links.append(normalized_link)

        return normalized_links

    def _collect_created_paths(self, response_data: Dict) -> Set[str]:
        """Collect normalized paths of items created in the current run."""
        created_paths: Set[str] = set()
        for key in ("created", "files_created", "folders_created"):
            value = response_data.get(key)
            if isinstance(value, list):
                candidates = value
            elif isinstance(value, str):
                candidates = [value]
            else:
                continue

            for candidate in candidates:
                normalized = self._normalize_path(candidate)
                if normalized:
                    created_paths.add(normalized)

        return created_paths

    def _normalize_raw_link(self, link: Any) -> Optional[Dict[str, Any]]:
        """Normalize raw link entries to a unified structure."""
        if isinstance(link, dict):
            description = str(link.get("description", "") or "").strip()
            granularity_raw = (
                link.get("granularity")
                or link.get("detail_level")
                or link.get("level")
                or link.get("mode")
                or link.get("summary")
            )
            granularity = str(granularity_raw or "auto").strip().lower()
            if granularity in {"summary", "aggregate", "aggregated", "group"}:
                granularity = "summary"
            elif granularity in {"detailed", "detail", "precise", "specific"}:
                granularity = "detailed"
            else:
                granularity = "auto"

            targets: List[Dict[str, Any]] = []

            single_mappings = [
                ("file", "file"),
                ("folder", "folder"),
                ("path", link.get("type")),
                ("target", link.get("target_type")),
            ]
            for key, target_type in single_mappings:
                if key in link:
                    target = self._normalize_target(link[key], target_type)
                    if target:
                        targets.append(target)

            multi_mappings = [
                ("files", "file"),
                ("folders", "folder"),
                ("paths", link.get("type")),
                ("targets", None),
                ("items", None),
                ("entities", None),
            ]
            for key, default_type in multi_mappings:
                if key not in link:
                    continue
                value = link[key]
                if isinstance(value, list):
                    for item in value:
                        target = self._normalize_target(item, default_type)
                        if target:
                            targets.append(target)
                else:
                    target = self._normalize_target(value, default_type)
                    if target:
                        targets.append(target)

            if not targets:
                return None

            unique_targets = []
            seen_targets: Set[Tuple[str, str, str]] = set()
            for target in targets:
                key = (
                    target.get("type", "file"),
                    self._normalize_path(target.get("path")),
                    (target.get("anchor") or "").strip(),
                )
                if not key[1] or key in seen_targets:
                    continue
                seen_targets.add(key)
                unique_targets.append(target)

            if not unique_targets:
                return None

            return {
                "description": description,
                "granularity": granularity,
                "targets": unique_targets,
            }

        if isinstance(link, str):
            target = self._normalize_target(link, "file")
            if not target:
                return None
            return {"description": "", "granularity": "auto", "targets": [target]}

        return None

    def _normalize_target(self, item: Any, default_type: Optional[str]) -> Optional[Dict[str, Any]]:
        """Normalize individual target definitions."""
        if item is None:
            return None

        if isinstance(item, dict):
            target_type = item.get("type") or item.get("scope") or default_type or "file"
            path = item.get("path") or item.get("file") or item.get("folder")
            if path is None and isinstance(item.get("target"), str):
                path = item["target"]
            anchor = item.get("anchor") or item.get("fragment") or item.get("section")
            label = item.get("label") or item.get("title") or item.get("name")
            return self._finalize_target(path, target_type, anchor, label)

        return self._finalize_target(item, default_type, None, None)

    def _finalize_target(
        self,
        path: Any,
        target_type: Optional[str],
        anchor: Optional[str],
        label: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Finalize target normalization."""
        if path is None:
            return None

        raw_path = str(path).strip()
        if not raw_path:
            return None

        extracted_anchor = None
        if "#" in raw_path:
            raw_path, extracted_anchor = raw_path.split("#", 1)
            extracted_anchor = extracted_anchor.strip()

        anchor_value = (anchor or extracted_anchor or "").strip()
        if anchor_value.startswith("#"):
            anchor_value = anchor_value[1:]
        anchor_value = anchor_value or None

        normalized_path = self._normalize_path(raw_path)
        if not normalized_path:
            return None

        normalized_type = (target_type or "file").lower()
        if normalized_type not in {"file", "folder", "entity", "section"}:
            normalized_type = "file"

        normalized_label = label.strip() if isinstance(label, str) and label.strip() else None

        return {
            "path": normalized_path,
            "type": normalized_type,
            "anchor": anchor_value,
            "label": normalized_label,
        }

    def _normalize_path(self, path: Any) -> str:
        """Normalize relative paths for comparison."""
        if not isinstance(path, str):
            return ""
        value = path.strip()
        if not value:
            return ""
        if "#" in value:
            value = value.split("#", 1)[0]
        while value.startswith("./"):
            value = value[2:]
        return value.rstrip()

    def _filter_new_targets(
        self, targets: List[Dict[str, Any]], created_paths: Set[str]
    ) -> List[Dict[str, Any]]:
        """Filter out targets that refer to newly created items."""
        filtered_targets = []
        seen_keys: Set[Tuple[str, str, str, str]] = set()

        for target in targets:
            path = target.get("path")
            normalized_path = self._normalize_path(path)
            if not normalized_path or normalized_path in created_paths:
                continue

            anchor = (target.get("anchor") or "").strip()
            label = (target.get("label") or "").strip()
            target_type = target.get("type", "file")

            dedup_key = (target_type, normalized_path, anchor, label)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            filtered_targets.append(
                {
                    "path": normalized_path,
                    "type": target_type,
                    "anchor": anchor or None,
                    "label": label or None,
                }
            )

        return filtered_targets

    def _build_dedup_key(self, link: Dict[str, Any]) -> Tuple:
        """Build a deduplication key for normalized link entries."""
        targets_key = tuple(
            sorted(
                (
                    target.get("type", "file"),
                    target.get("path", ""),
                    target.get("anchor") or "",
                    target.get("label") or "",
                )
                for target in link.get("targets", [])
            )
        )
        return (
            targets_key,
            link.get("granularity", "auto"),
            link.get("description", "").strip(),
        )

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

        lines = ["<b>🔗 Связанные сущности:</b>"]
        for link in value:
            normalized = (
                link
                if isinstance(link, dict) and link.get("targets")
                else self._normalize_raw_link(link)
            )
            if not isinstance(normalized, dict):
                escaped_link = self._escape_html(str(link))
                lines.append(f"- {escaped_link}")
                continue

            targets = normalized.get("targets") or []
            if not targets:
                continue

            description = self._escape_html(normalized.get("description", ""))
            targets_html = self._format_targets_html(targets)
            granularity_suffix = self._granularity_suffix_html(normalized.get("granularity"))

            if description:
                lines.append(f"- {targets_html}: {description}{granularity_suffix}")
            else:
                lines.append(f"- {targets_html}{granularity_suffix}")

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

        lines = ["🔗 Связанные сущности:"]
        for link in value:
            normalized = (
                link
                if isinstance(link, dict) and link.get("targets")
                else self._normalize_raw_link(link)
            )
            if not isinstance(normalized, dict):
                escaped_link = escape_markdown(str(link))
                lines.append(f"- {escaped_link}")
                continue

            targets = normalized.get("targets") or []
            if not targets:
                continue

            description = normalized.get("description", "")
            targets_md = self._format_targets_md(targets)
            granularity_suffix = self._granularity_suffix_md(normalized.get("granularity"))

            if description:
                escaped_description = escape_markdown(description)
                lines.append(f"- {targets_md}: {escaped_description}{granularity_suffix}")
            else:
                lines.append(f"- {targets_md}{granularity_suffix}")
        return "\n".join(lines)

    def _format_targets_html(self, targets: List[Dict[str, Any]]) -> str:
        """Format targets for HTML output."""
        formatted_targets = []
        for target in targets:
            path = target.get("path", "")
            if not path:
                continue

            anchor = target.get("anchor")
            label = target.get("label")
            display_path = f"{path}#{anchor}" if anchor else path
            display_text = label if label else display_path
            if label and label.strip() != display_path:
                display_text = f"{label} ({display_path})"

            escaped_display = self._escape_html(display_text)

            if self.github_url:
                url = f"{self.github_url}/{path}"
                url = _fix_duplicate_topics_in_url(url)
                if anchor:
                    url = f"{url}#{anchor}"
                escaped_url = self._escape_html(url)
                formatted_targets.append(f'<a href="{escaped_url}">{escaped_display}</a>')
            else:
                formatted_targets.append(escaped_display)

        return ", ".join(formatted_targets)

    def _format_targets_md(self, targets: List[Dict[str, Any]]) -> str:
        """Format targets for Markdown output."""
        formatted_targets = []
        for target in targets:
            path = target.get("path", "")
            if not path:
                continue

            anchor = target.get("anchor")
            label = target.get("label")
            display_path = f"{path}#{anchor}" if anchor else path
            display_text = label if label else display_path
            if label and label.strip() != display_path:
                display_text = f"{label} ({display_path})"

            escaped_display = escape_markdown(display_text)
            if self.github_url:
                url = f"{self.github_url}/{path}"
                url = _fix_duplicate_topics_in_url(url)
                if anchor:
                    url = f"{url}#{anchor}"
                escaped_url = escape_markdown_url(url)
                formatted_targets.append(f"[{escaped_display}]({escaped_url})")
            else:
                formatted_targets.append(escaped_display)

        return ", ".join(formatted_targets)

    def _granularity_suffix_html(self, granularity: Optional[str]) -> str:
        """Return HTML suffix for granularity hints."""
        if granularity == "summary":
            return " <i>(сводная связь)</i>"
        if granularity == "detailed":
            return " <i>(детализированная связь)</i>"
        return ""

    def _granularity_suffix_md(self, granularity: Optional[str]) -> str:
        """Return Markdown suffix for granularity hints."""
        if granularity == "summary":
            return " (сводная связь)"
        if granularity == "detailed":
            return " (детализированная связь)"
        return ""


class InsiteField(BaseField):
    """Answer field for response format."""

    def __init__(self):
        super().__init__(
            "insite",
            "Текстовое поле (str). Проанализируй контент сообщения, найденные тобой связи, информацию в базе знаний."
            "И выведи по настоящему интересные инсайты:"
            "- потенциальные мощные прорывы"
            "- применение нескольких технологий вместе, которые дополняют друг друга"
            "- Каждый инсайт должен быть подкреплён чёткой причинно-следственной логикой:"
            "почему именно эта комбинация работает, какие ограничения она снимает, какие новые степени свободы открывает.",
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
