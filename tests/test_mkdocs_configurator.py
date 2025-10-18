"""
Tests for MkDocs Configurator
"""

import tempfile
from pathlib import Path

import pytest

from src.knowledge_base.mkdocs_configurator import MkDocsConfigurator


class TestMkDocsConfigurator:
    """Tests for MkDocsConfigurator class"""

    @pytest.fixture
    def configurator(self):
        """Create a configurator instance"""
        return MkDocsConfigurator()

    @pytest.fixture
    def temp_kb_path(self):
        """Create a temporary knowledge base path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_is_mkdocs_configured_false(self, configurator, temp_kb_path):
        """Test that is_mkdocs_configured returns False when mkdocs.yml doesn't exist"""
        assert not configurator.is_mkdocs_configured(temp_kb_path)

    def test_is_mkdocs_configured_true(self, configurator, temp_kb_path):
        """Test that is_mkdocs_configured returns True when mkdocs.yml exists"""
        # Create mkdocs.yml
        (temp_kb_path / "mkdocs.yml").write_text("site_name: Test")
        assert configurator.is_mkdocs_configured(temp_kb_path)

    def test_configure_mkdocs_success(self, configurator, temp_kb_path):
        """Test successful MkDocs configuration"""
        kb_name = "test-kb"
        github_url = "https://github.com/testuser/test-repo"

        success, message = configurator.configure_mkdocs(temp_kb_path, kb_name, github_url)

        assert success
        assert "успешно настроен" in message
        assert (temp_kb_path / "mkdocs.yml").exists()
        assert (temp_kb_path / "docs" / "index.md").exists()
        assert (temp_kb_path / ".github" / "workflows" / "docs.yml").exists()
        assert (temp_kb_path / "requirements-docs.txt").exists()

    def test_configure_mkdocs_already_configured(self, configurator, temp_kb_path):
        """Test that configure_mkdocs fails when already configured"""
        # Create mkdocs.yml
        (temp_kb_path / "mkdocs.yml").write_text("site_name: Test")

        kb_name = "test-kb"
        github_url = "https://github.com/testuser/test-repo"

        success, message = configurator.configure_mkdocs(temp_kb_path, kb_name, github_url)

        assert not success
        assert "уже настроен" in message

    def test_configure_mkdocs_creates_docs_structure(self, configurator, temp_kb_path):
        """Test that configure_mkdocs creates proper docs structure"""
        kb_name = "test-kb"
        github_url = "https://github.com/testuser/test-repo"

        success, _ = configurator.configure_mkdocs(temp_kb_path, kb_name, github_url)

        assert success

        # Check docs structure
        docs_dir = temp_kb_path / "docs"
        assert docs_dir.exists()
        assert (docs_dir / "index.md").exists()

        # Check category directories
        categories = ["personal", "work", "projects", "learning", "references"]
        for category in categories:
            category_dir = docs_dir / category
            assert category_dir.exists()
            assert (category_dir / "index.md").exists()

    def test_configure_mkdocs_creates_gitignore_entry(self, configurator, temp_kb_path):
        """Test that configure_mkdocs adds site/ to .gitignore"""
        kb_name = "test-kb"
        github_url = "https://github.com/testuser/test-repo"

        success, _ = configurator.configure_mkdocs(temp_kb_path, kb_name, github_url)

        assert success

        gitignore = temp_kb_path / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text()
        assert "site/" in content

    def test_configure_mkdocs_preserves_existing_gitignore(self, configurator, temp_kb_path):
        """Test that configure_mkdocs preserves existing .gitignore content"""
        # Create existing .gitignore
        existing_content = "*.pyc\n__pycache__/\n"
        (temp_kb_path / ".gitignore").write_text(existing_content)

        kb_name = "test-kb"
        github_url = "https://github.com/testuser/test-repo"

        success, _ = configurator.configure_mkdocs(temp_kb_path, kb_name, github_url)

        assert success

        gitignore = temp_kb_path / ".gitignore"
        content = gitignore.read_text()

        # Check that both old and new content exist
        assert "*.pyc" in content
        assert "__pycache__/" in content
        assert "site/" in content

    def test_parse_github_url_https(self, configurator):
        """Test parsing HTTPS GitHub URL"""
        url = "https://github.com/testuser/test-repo"
        result = configurator._parse_github_url(url)

        assert result is not None
        assert result["username"] == "testuser"
        assert result["repo_name"] == "test-repo"

    def test_parse_github_url_https_with_git(self, configurator):
        """Test parsing HTTPS GitHub URL with .git suffix"""
        url = "https://github.com/testuser/test-repo.git"
        result = configurator._parse_github_url(url)

        assert result is not None
        assert result["username"] == "testuser"
        assert result["repo_name"] == "test-repo"

    def test_parse_github_url_git_protocol(self, configurator):
        """Test parsing git@ protocol URL"""
        url = "git@github.com:testuser/test-repo.git"
        result = configurator._parse_github_url(url)

        assert result is not None
        assert result["username"] == "testuser"
        assert result["repo_name"] == "test-repo"

    def test_parse_github_url_invalid(self, configurator):
        """Test parsing invalid URL"""
        url = "https://gitlab.com/testuser/test-repo"
        result = configurator._parse_github_url(url)

        assert result is None

    def test_mkdocs_yml_content(self, configurator, temp_kb_path):
        """Test that mkdocs.yml contains correct content"""
        kb_name = "test-kb"
        github_url = "https://github.com/testuser/test-repo"

        success, _ = configurator.configure_mkdocs(temp_kb_path, kb_name, github_url)

        assert success

        mkdocs_yml = temp_kb_path / "mkdocs.yml"
        content = mkdocs_yml.read_text()

        # Check important content
        assert kb_name in content
        assert "testuser" in content
        assert "test-repo" in content
        assert "material" in content  # Theme
        assert "navigation" in content  # Features
        assert "pymdownx" in content  # Extensions

    def test_github_workflow_content(self, configurator, temp_kb_path):
        """Test that GitHub workflow contains correct content"""
        kb_name = "test-kb"
        github_url = "https://github.com/testuser/test-repo"

        success, _ = configurator.configure_mkdocs(temp_kb_path, kb_name, github_url)

        assert success

        workflow = temp_kb_path / ".github" / "workflows" / "docs.yml"
        content = workflow.read_text()

        # Check important workflow content
        assert "Deploy Documentation" in content
        assert "mkdocs build" in content
        assert "github-pages" in content
        assert "requirements-docs.txt" in content

    def test_requirements_docs_content(self, configurator, temp_kb_path):
        """Test that requirements-docs.txt contains correct packages"""
        kb_name = "test-kb"
        github_url = "https://github.com/testuser/test-repo"

        success, _ = configurator.configure_mkdocs(temp_kb_path, kb_name, github_url)

        assert success

        requirements = temp_kb_path / "requirements-docs.txt"
        content = requirements.read_text()

        # Check important packages
        assert "mkdocs" in content
        assert "mkdocs-material" in content
        assert "pymdown-extensions" in content
