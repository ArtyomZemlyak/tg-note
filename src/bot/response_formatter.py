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


class MessageSeparator(BaseField):
    """Non-rendered separator to split messages."""

    def __init__(self):
        super().__init__("__separator__", "")

    def parse(self, response_data: Dict, **kwargs) -> Any:  # noqa: D401
        """Separators are not parsed."""
        return None

    def to_html(self, value: Any) -> str:
        return ""

    def to_md(self, value: Any) -> str:
        return ""

    def generate_example(self):
        return ""


class SummaryField(BaseField):
    """Summary field for response format."""

    def __init__(self):
        super().__init__(
            "summary",
            "Краткое описание о чем была работа (если идет разбор информации), или что было сделано (если была задача специальная)."
        )


class AnswerField(BaseField):
    """Answer field for response format."""

    def __init__(self):
        super().__init__(
            "answer",
            'Ответ на вопрос пользователя, если это был вопросный запрос. Поле "answer" заполняй только если пользователь задал вопрос. '
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
        raw_links = response_data.get(self.name, [])
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
        """Convert links list to HTML format."""
        return self._render_links_html(value, "🔗 Связанные сущности:")

    def _render_links_html(self, value: Any, heading: str) -> str:
        """Render links list to HTML with a custom heading."""
        if not value:
            return ""

        lines = [f"<b>{heading}</b>"]
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
        """Convert links list to markdown format."""
        return self._render_links_md(value, "🔗 Связанные сущности:")

    def _render_links_md(self, value: Any, heading: str) -> str:
        """Render links list to Markdown with a custom heading."""
        if not value:
            return ""

        lines = [heading]
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


class LinksInsiteField(LinksField):
    """Insight-focused links field for nuanced connections."""

    def __init__(self, github_url: str = None):
        BaseField.__init__(
            self,
            "links_insite",
            "# Инсайтные связи с другими файлами/папками/сущностями в базе знаний. "
            "Фокус на неожиданных совпадениях и редких деталях: специфические режимы "
            "обучения, одинаковые узкие метрики, редкие приёмы обработки данных, странные "
            "ограничения или обходы багов. Игнорируй банальные сходства (оба LLM, оба "
            "используют RL). Всегда указывай, какой конкретный механизм/гиперпараметр/"
            "артефакт совпадает или отличается, где именно это описано (файл + anchor/label), "
            "и какой эффект это даёт (метрика, латентный навык, устранённая проблема).",
        )
        self.github_url = github_url

    def generate_example(self):
        """Generate example value for insight links field."""
        example = [
            {
                "files": [
                    "topics/ai/llm/models/rnj_1.md#curriculum-stages",
                    "topics/ai/llm/models/deepseek_v3_2_key_innovations.md#curriculum-data-blend",
                ],
                "granularity": "detailed",
                "description": (
                    "Редкая общность: обе модели вводят curriculum по длине диалогов с ручными "
                    "порогами 64→256→2k токенов и заморозкой LoRA-адаптеров на первых двух этапах. "
                    "Укажи, что в обеих заметках это связывают со спадом всплесков perplexity на "
                    "чат-логах."
                ),
            },
            {
                "targets": [
                    {
                        "path": "topics/ai/llm/llm_architectures_comparison.md#routing",
                        "label": "Сравнение роутинга экспертов",
                    },
                    {"path": "topics/ai/llm/models/jamba_model.md#router-loss"},
                ],
                "granularity": "detailed",
                "description": (
                    "Неочевидное отличие: Jamba штрафует неверный роутинг через auxiliary router loss, "
                    "а в сравнении архитектур есть упоминание похожего штрафа только для длинных "
                    "промптов. Раскрой, что оба связывают это с падением токен-дропа в длинных "
                    "контекстах, но достигают эффекта разными коэффициентами."
                ),
            },
            {
                "folder": "topics/ai/rlhf/edge-cases",
                "granularity": "summary",
                "description": (
                    "Инсайт по качеству: часть выборок Rnj-1 помечена как «контекстные ловушки» с "
                    "ручным аннотированием противоречий. В папке edge-cases есть аналогичные "
                    "примеры для чат-ассистентов; попроси указать, какие типы ловушек совпадают "
                    "и чем они снижали отказ на safety-промптах."
                ),
            },
        ]
        return f"""{example} {self.text}"""

    def to_html(self, value: Any) -> str:
        """Convert insight links list to HTML format."""
        return self._render_links_html(value, "🧠 Инсайтные связи:")

    def to_md(self, value: Any) -> str:
        """Convert insight links list to Markdown format."""
        return self._render_links_md(value, "🧠 Инсайтные связи:")


class InsiteField(BaseField):
    """Answer field for response format."""

    def __init__(self):
        super().__init__(
            "insite",
            "Текстовое поле (str). Построй максимально нюансные инсайты на основе контента сообщения,"
            " найденных связей (особенно links_insite) и базы знаний. Подсвечивай конкретные механизмы,"
            " гиперпараметры, редкие режимы обучения, тонкие сбои или обходы. Формируй инсайтные гипотезы:"
            " какие нетривиальные эффекты могут возникнуть при сочетании найденных паттернов, какие"
            " ограничения снимаются, какие скрытые навыки/метрики могут вырасти. Каждый вывод — с явной"
            " причинно-следственной логикой и указанием, откуда взята деталь (файл + anchor/label).",
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

    def __init__(self, github_url: str = None, message_break_after: Optional[List[str]] = None):
        base_fields: list[BaseField] = [
            SummaryField(),
            AnswerField(),
            FilesCreatedField(github_url),
            FilesEditedField(github_url),
            FilesDeletedField(github_url),
            LinksField(github_url),
            LinksInsiteField(github_url),
            InsiteField(),
        ]
        self.fields: list[BaseField] = self._apply_message_breaks(
            base_fields, message_break_after or []
        )

    def generate_prompt_text(self) -> str:
        """
        Generate the complete prompt text for ResponseFormatter.

        Returns:
            str: Formatted prompt text
        """
        import json
        # Generate the values for placeholders
        example = {
            field.name: field.generate_example() for field in self._iter_content_fields()
        }

        prompt_text = json.dumps(example, ensure_ascii=False, indent=2)

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
                parsed_data = {
                    field.name: field.parse(data) for field in self._iter_content_fields()
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

    def to_html(self, response_data: Dict[str, Any]) -> str:
        """
        Convert response data to HTML format.

        Args:
            response_data: Parsed response data

        Returns:
            str: HTML formatted string
        """
        lines = [
            field.to_html(response_data.get(field.name, None))
            for field in self._iter_content_fields()
        ]

        return "\n\n".join([l for l in lines if l])

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
            for field in self._iter_content_fields()
        ]

        return "\n\n".join([l for l in lines if l])

    def to_messages_md(self, response_data: Dict[str, Any]) -> List[str]:
        """Convert response data to a list of markdown messages with separators."""
        return self._to_messages(response_data, mode="md")

    def to_messages_html(self, response_data: Dict[str, Any]) -> List[str]:
        """Convert response data to a list of HTML messages with separators."""
        return self._to_messages(response_data, mode="html")

    def _to_messages(self, response_data: Dict[str, Any], mode: str) -> List[str]:
        """Render messages split by separators in the configured order."""
        messages: List[str] = []
        current_parts: List[str] = []

        for field in self.fields:
            if isinstance(field, MessageSeparator):
                if current_parts:
                    messages.append("\n\n".join(current_parts))
                    current_parts = []
                continue

            renderer = field.to_md if mode == "md" else field.to_html
            rendered = renderer(response_data.get(field.name, None))
            if rendered:
                current_parts.append(rendered)

        if current_parts:
            messages.append("\n\n".join(current_parts))

        return messages

    def _apply_message_breaks(
        self, base_fields: List[BaseField], message_break_after: List[str]
    ) -> List[BaseField]:
        """Insert message separators after specified field names."""
        if not message_break_after:
            return base_fields

        breaks = set(message_break_after)
        result: List[BaseField] = []

        for field in base_fields:
            result.append(field)
            if field.name in breaks:
                result.append(MessageSeparator())

        return result

    def _iter_content_fields(self) -> List[BaseField]:
        """Return fields excluding separators."""
        return [f for f in self.fields if not isinstance(f, MessageSeparator)]
