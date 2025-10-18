"""
MkDocs Configurator for Knowledge Bases
Configures mkdocs for GitHub-based knowledge bases

AICODE-NOTE: This module provides functionality to automatically configure MkDocs
for GitHub-based knowledge bases. It creates all necessary files for building
and deploying static documentation to GitHub Pages, including:
- mkdocs.yml configuration with Material theme
- docs/ directory structure with categories
- GitHub Actions workflow for automatic deployment
- requirements-docs.txt with dependencies
"""

from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

try:
    from git import Repo

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None


class MkDocsConfigurator:
    """Configures MkDocs for GitHub-based knowledge bases"""

    MKDOCS_YML_TEMPLATE = """site_name: {kb_name} Documentation
site_description: Knowledge Base Documentation
site_author: Knowledge Base Owner
site_url: https://{github_username}.github.io/{repo_name}/

repo_name: {github_username}/{repo_name}
repo_url: {github_url}
edit_uri: edit/main/docs/

docs_dir: docs

theme:
  name: material
  language: en
  palette:
    # Palette toggle for light mode
    - scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    # Palette toggle for dark mode
    - scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.instant
    - navigation.tracking
    - navigation.tabs
    - navigation.tabs.sticky
    - navigation.sections
    - navigation.expand
    - navigation.top
    - navigation.footer
    - search.suggest
    - search.highlight
    - search.share
    - toc.follow
    - content.code.copy
    - content.code.annotate
    - content.tabs.link

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
      pygments_lang_class: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - admonition
  - pymdownx.details
  - pymdownx.tasklist:
      custom_checkbox: true
  - attr_list
  - md_in_html
  - toc:
      permalink: true

plugins:
  - search
  - tags

extra:
  social:
    - icon: fontawesome/brands/github
      link: {github_url}
      name: GitHub Repository

nav:
  - Home: index.md
  - Categories:
    - Personal: personal/index.md
    - Work: work/index.md
    - Projects: projects/index.md
    - Learning: learning/index.md
    - References: references/index.md

copyright: Copyright &copy; {year} Knowledge Base Owner
"""

    GITHUB_WORKFLOW_TEMPLATE = """name: Deploy Documentation

on:
  push:
    branches:
      - main
    paths:
      - docs/**
      - mkdocs.yml
      - .github/workflows/docs.yml
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements-docs.txt

      - name: Build documentation
        run: mkdocs build --clean --strict --site-dir site

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    runs-on: ubuntu-latest
    needs: build
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""

    REQUIREMENTS_DOCS_TEMPLATE = """# MkDocs and plugins
mkdocs>=1.5.3
mkdocs-material>=9.5.3
pymdown-extensions>=10.7
"""

    DOCS_INDEX_TEMPLATE = """# {kb_name} Documentation

Welcome to the {kb_name} knowledge base documentation!

## About

This knowledge base is automatically built from markdown files and deployed using MkDocs and GitHub Pages.

## Structure

The knowledge base is organized into the following categories:

- **Personal** - Personal notes and thoughts
- **Work** - Work-related documents and notes
- **Projects** - Project documentation and notes
- **Learning** - Learning materials and notes
- **References** - Reference materials and links

## Navigation

Use the navigation menu above to browse through different sections of the knowledge base.

## How to Use

1. Browse categories using the navigation menu
2. Use the search function to find specific topics
3. Click on links to navigate between related pages

---

*This documentation was automatically generated using MkDocs Material theme.*
"""

    CATEGORY_INDEX_TEMPLATE = """# {category_name}

This section contains {category_description}.

## Contents

Browse the files in this category using the file tree in the left sidebar.

---
"""

    def __init__(self):
        """Initialize MkDocs configurator"""
        pass

    def is_mkdocs_configured(self, kb_path: Path) -> bool:
        """
        Check if MkDocs is already configured for this knowledge base

        Args:
            kb_path: Path to knowledge base

        Returns:
            True if mkdocs.yml exists, False otherwise
        """
        mkdocs_yml = kb_path / "mkdocs.yml"
        return mkdocs_yml.exists()

    def configure_mkdocs(self, kb_path: Path, kb_name: str, github_url: str) -> Tuple[bool, str]:
        """
        Configure MkDocs for a GitHub-based knowledge base

        Args:
            kb_path: Path to knowledge base
            kb_name: Name of the knowledge base
            github_url: GitHub repository URL

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if already configured
            if self.is_mkdocs_configured(kb_path):
                return (
                    False,
                    "MkDocs уже настроен для этой базы знаний. Найден файл mkdocs.yml",
                )

            # Extract GitHub username and repo name from URL
            github_info = self._parse_github_url(github_url)
            if not github_info:
                return False, "Не удалось извлечь информацию из GitHub URL"

            # Get current year for copyright
            from datetime import datetime

            current_year = datetime.now().year

            # Create mkdocs.yml
            mkdocs_content = self.MKDOCS_YML_TEMPLATE.format(
                kb_name=kb_name,
                github_username=github_info["username"],
                repo_name=github_info["repo_name"],
                github_url=github_url,
                year=current_year,
            )
            mkdocs_yml = kb_path / "mkdocs.yml"
            mkdocs_yml.write_text(mkdocs_content, encoding="utf-8")
            logger.info(f"Created mkdocs.yml at {mkdocs_yml}")

            # Create docs directory structure
            docs_dir = kb_path / "docs"
            docs_dir.mkdir(exist_ok=True)

            # Create main index.md
            index_content = self.DOCS_INDEX_TEMPLATE.format(kb_name=kb_name)
            (docs_dir / "index.md").write_text(index_content, encoding="utf-8")

            # Create category directories with index files
            categories = {
                "personal": "personal notes and thoughts",
                "work": "work-related documents and notes",
                "projects": "project documentation and notes",
                "learning": "learning materials and notes",
                "references": "reference materials and links",
            }

            for category, description in categories.items():
                category_dir = docs_dir / category
                category_dir.mkdir(exist_ok=True)

                category_index = self.CATEGORY_INDEX_TEMPLATE.format(
                    category_name=category.capitalize(), category_description=description
                )
                (category_dir / "index.md").write_text(category_index, encoding="utf-8")

            logger.info(f"Created docs directory structure at {docs_dir}")

            # Create .github/workflows directory
            workflows_dir = kb_path / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)

            # Create docs.yml workflow
            workflow_file = workflows_dir / "docs.yml"
            workflow_file.write_text(self.GITHUB_WORKFLOW_TEMPLATE, encoding="utf-8")
            logger.info(f"Created GitHub workflow at {workflow_file}")

            # Create requirements-docs.txt
            requirements_file = kb_path / "requirements-docs.txt"
            requirements_file.write_text(self.REQUIREMENTS_DOCS_TEMPLATE, encoding="utf-8")
            logger.info(f"Created requirements-docs.txt at {requirements_file}")

            # Create .gitignore entry for site/ directory if not exists
            gitignore_file = kb_path / ".gitignore"
            gitignore_content = ""
            if gitignore_file.exists():
                gitignore_content = gitignore_file.read_text(encoding="utf-8")

            if "site/" not in gitignore_content:
                if gitignore_content and not gitignore_content.endswith("\n"):
                    gitignore_content += "\n"
                gitignore_content += "\n# MkDocs build output\nsite/\n"
                gitignore_file.write_text(gitignore_content, encoding="utf-8")
                logger.info("Added site/ to .gitignore")

            # Commit changes if git is available
            if GIT_AVAILABLE:
                try:
                    repo = Repo(kb_path)
                    repo.index.add(
                        [
                            "mkdocs.yml",
                            "docs/",
                            ".github/",
                            "requirements-docs.txt",
                            ".gitignore",
                        ]
                    )
                    repo.index.commit("Configure MkDocs for documentation")
                    logger.info("Committed MkDocs configuration to git")
                except Exception as e:
                    logger.warning(f"Could not commit changes: {e}")

            success_message = (
                f"✅ MkDocs успешно настроен для базы знаний '{kb_name}'!\n\n"
                f"Созданы следующие файлы:\n"
                f"• mkdocs.yml - конфигурация MkDocs\n"
                f"• docs/ - директория с документацией\n"
                f"• .github/workflows/docs.yml - GitHub Actions для деплоя\n"
                f"• requirements-docs.txt - зависимости для сборки\n\n"
                f"📝 Следующие шаги:\n"
                f"1. Закоммитьте и запушьте изменения в GitHub\n"
                f"2. В настройках репозитория включите GitHub Pages:\n"
                f"   Settings → Pages → Source: GitHub Actions\n"
                f"3. После пуша документация будет автоматически собрана и опубликована\n\n"
                f"🌐 Документация будет доступна по адресу:\n"
                f"https://{github_info['username']}.github.io/{github_info['repo_name']}/"
            )

            return True, success_message

        except Exception as e:
            logger.error(f"Error configuring MkDocs: {e}", exc_info=True)
            return False, f"Ошибка при настройке MkDocs: {str(e)}"

    def _parse_github_url(self, github_url: str) -> Optional[dict]:
        """
        Parse GitHub URL to extract username and repo name

        Args:
            github_url: GitHub repository URL

        Returns:
            Dict with username and repo_name, or None if parsing fails
        """
        import re

        # Handle different URL formats:
        # https://github.com/username/repo
        # https://github.com/username/repo.git
        # git@github.com:username/repo.git
        # Convert git@ format to https
        if github_url.startswith("git@"):
            github_url = github_url.replace("git@github.com:", "https://github.com/")

        # Extract username and repo name
        pattern = r"github\.com[/:]([^/]+)/([^/\.]+)"
        match = re.search(pattern, github_url)

        if match:
            return {"username": match.group(1), "repo_name": match.group(2)}

        logger.warning(f"Could not parse GitHub URL: {github_url}")
        return None
