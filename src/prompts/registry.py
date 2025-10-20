"""
Versioned Prompt Registry

Filesystem-based prompt loader with versioning and locale support.

Directory structure under config/prompts:
- Key is dot-separated (e.g., "qwen_code_cli.instruction").
- All segments except the last become subdirectories.
- File name pattern: <name>.<locale>.v<semver>.md

Examples:
- key="qwen_code_cli.instruction", locale="ru" ->
  config/prompts/qwen_code_cli/instruction.ru.v1.md

- key="content_processing.template", locale="ru" ->
  config/prompts/content_processing/template.ru.v1.md

If version is not provided, the registry selects the highest available version.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def _parse_version_string(version_str: str) -> Tuple[int, ...]:
    """Parse version like 'v1', 'v1.2', 'v2.0.3' into a tuple for comparison."""
    try:
        if not version_str.startswith("v"):
            return ()
        parts = version_str[1:].split(".")
        numbers: List[int] = []
        for p in parts:
            numbers.append(int(p))
        while len(numbers) < 3:
            numbers.append(0)
        return tuple(numbers[:3])
    except Exception:
        return ()


@dataclass(frozen=True)
class PromptIdentifier:
    key: str
    locale: str
    version: Optional[str] = None  # e.g., 'v1', 'v1.0', 'v2.1.3'

    @property
    def dir_segments(self) -> Tuple[str, ...]:
        parts = self.key.split(".")
        if len(parts) < 2:
            return ()
        return tuple(parts[:-1])

    @property
    def name(self) -> str:
        return self.key.split(".")[-1]


class PromptRegistry:
    """Filesystem-based prompt loader with versioning and locale support."""

    def __init__(self, base_dirs: Optional[Iterable[Path]] = None):
        default_base = Path("config") / "prompts"
        bases = list(base_dirs) if base_dirs is not None else [default_base]
        # Keep order for search precedence; deduplicate
        seen = {}
        for b in bases:
            seen[str(b)] = b
        self._base_dirs: Tuple[Path, ...] = tuple(seen.values())

    @staticmethod
    def _candidate_files(base_dir: Path, ident: PromptIdentifier) -> List[Path]:
        dir_path = base_dir
        for seg in ident.dir_segments:
            dir_path = dir_path / seg

        if not dir_path.exists() or not dir_path.is_dir():
            return []

        prefix = f"{ident.name}.{ident.locale}.v"
        return [
            p
            for p in dir_path.iterdir()
            if p.is_file() and p.name.startswith(prefix) and p.suffix == ".md"
        ]

    @staticmethod
    def _extract_version_from_filename(filename: str) -> Optional[str]:
        parts = filename.split(".")
        if len(parts) < 4:
            return None
        return parts[-2]

    def _select_best_file(
        self, candidates: List[Path], requested_version: Optional[str]
    ) -> Optional[Path]:
        if not candidates:
            return None

        if requested_version:
            for f in candidates:
                v = self._extract_version_from_filename(f.name)
                if v == requested_version:
                    return f
        # Fall back to highest version
        candidates.sort(
            key=lambda f: _parse_version_string(self._extract_version_from_filename(f.name) or ""),
            reverse=True,
        )
        return candidates[0]

    @lru_cache(maxsize=256)
    def get(self, key: str, *, locale: str, version: Optional[str] = None) -> str:
        """
        Load prompt text by key, locale, and optional version.
        """
        ident = PromptIdentifier(key=key, locale=locale, version=version)

        for base in self._base_dirs:
            candidates = self._candidate_files(base, ident)
            chosen = self._select_best_file(candidates, requested_version=version)
            if chosen and chosen.exists():
                return chosen.read_text(encoding="utf-8")

        searched_paths = []
        for base in self._base_dirs:
            dir_path = base
            for seg in ident.dir_segments:
                dir_path = dir_path / seg
            searched_paths.append(str(dir_path))

        raise FileNotFoundError(
            f"Prompt not found for key='{key}', locale='{locale}', version='{version}'. "
            f"Searched in: {', '.join(searched_paths)}"
        )


# Singleton used across the project
prompt_registry = PromptRegistry()
