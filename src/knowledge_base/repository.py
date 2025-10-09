"""
Repository Manager
Manages local and GitHub repositories for knowledge base
"""

import re
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

from config.kb_structure import GITIGNORE_CONTENT, KB_BASE_STRUCTURE, README_CONTENT

try:
    from git import GitCommandError, InvalidGitRepositoryError, Repo

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None
    GitCommandError = Exception
    InvalidGitRepositoryError = Exception


class RepositoryManager:
    """Manages KB repository (local or GitHub-based)"""

    def __init__(self, base_path: str = "./knowledge_base"):
        """
        Initialize repository manager

        Args:
            base_path: Base directory for all knowledge bases
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        if not GIT_AVAILABLE:
            logger.warning("GitPython not available, some features will be disabled")

    def init_local_kb(self, kb_name: str) -> Tuple[bool, str, Optional[Path]]:
        """
        Initialize a local knowledge base with git

        Args:
            kb_name: Name of the knowledge base

        Returns:
            Tuple of (success, message, kb_path)
        """
        # Sanitize KB name
        safe_name = self._sanitize_name(kb_name)
        kb_path = self.base_path / safe_name

        try:
            # Create directory
            kb_path.mkdir(parents=True, exist_ok=True)

            # Initialize git repository if not exists
            if not (kb_path / ".git").exists():
                if not GIT_AVAILABLE:
                    return False, "Git is not available", None

                repo = Repo.init(kb_path)

                # Create initial structure
                self._create_initial_structure(kb_path)

                # Initial commit
                repo.index.add(["*"])
                repo.index.commit("Initial commit: KB structure created")

                logger.info(f"Initialized local KB at {kb_path}")
                return True, f"Knowledge base '{kb_name}' initialized successfully", kb_path
            else:
                logger.info(f"KB already exists at {kb_path}")
                return True, f"Knowledge base '{kb_name}' already exists", kb_path

        except Exception as e:
            logger.error(f"Error initializing local KB: {e}", exc_info=True)
            return False, f"Error initializing KB: {str(e)}", None

    def clone_github_kb(
        self, github_url: str, kb_name: Optional[str] = None, credentials: Optional[dict] = None
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Clone a GitHub repository as knowledge base

        Args:
            github_url: GitHub repository URL
            kb_name: Optional custom name (defaults to repo name)
            credentials: Optional dict with 'username' and 'token'

        Returns:
            Tuple of (success, message, kb_path)
        """
        if not GIT_AVAILABLE:
            return False, "Git is not available", None

        try:
            # Extract repo name from URL if kb_name not provided
            if not kb_name:
                kb_name = self._extract_repo_name(github_url)

            safe_name = self._sanitize_name(kb_name)
            kb_path = self.base_path / safe_name

            # Check if already exists
            if kb_path.exists():
                logger.info(f"KB already exists at {kb_path}, pulling updates")
                return self.pull_updates(kb_path)

            # Build clone URL with credentials if provided
            clone_url = github_url
            if credentials and credentials.get("username") and credentials.get("token"):
                clone_url = self._inject_credentials(
                    github_url, credentials["username"], credentials["token"]
                )

            # Clone repository
            logger.info(f"Cloning {github_url} to {kb_path}")
            Repo.clone_from(clone_url, kb_path)

            return True, f"Successfully cloned '{kb_name}' from GitHub", kb_path

        except GitCommandError as e:
            logger.error(f"Git error cloning repository: {e}", exc_info=True)
            return False, f"Git error: {str(e)}", None
        except Exception as e:
            logger.error(f"Error cloning GitHub KB: {e}", exc_info=True)
            return False, f"Error cloning repository: {str(e)}", None

    def pull_updates(self, kb_path: Path) -> Tuple[bool, str, Optional[Path]]:
        """
        Pull latest updates from remote repository

        Args:
            kb_path: Path to knowledge base

        Returns:
            Tuple of (success, message, kb_path)
        """
        if not GIT_AVAILABLE:
            return False, "Git is not available", None

        try:
            repo = Repo(kb_path)

            # Check if there are uncommitted changes
            if repo.is_dirty():
                logger.warning(f"Repository at {kb_path} has uncommitted changes")
                return (
                    False,
                    "Repository has uncommitted changes. Commit or stash them first.",
                    kb_path,
                )

            # Pull from remote
            origin = repo.remote(name="origin")
            pull_info = origin.pull()

            logger.info(f"Pulled updates for {kb_path}")
            return True, "Successfully pulled latest updates", kb_path

        except InvalidGitRepositoryError:
            logger.error(f"Not a git repository: {kb_path}")
            return False, "Not a git repository", kb_path
        except Exception as e:
            logger.error(f"Error pulling updates: {e}", exc_info=True)
            return False, f"Error pulling updates: {str(e)}", kb_path

    def get_kb_path(self, kb_name: str) -> Optional[Path]:
        """
        Get path to existing knowledge base

        Args:
            kb_name: Name of the knowledge base

        Returns:
            Path if exists, None otherwise
        """
        safe_name = self._sanitize_name(kb_name)
        kb_path = self.base_path / safe_name

        if kb_path.exists():
            return kb_path
        return None

    def list_knowledge_bases(self) -> list:
        """
        List all available knowledge bases

        Returns:
            List of KB names
        """
        if not self.base_path.exists():
            return []

        return [
            d.name for d in self.base_path.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize KB name for filesystem

        Args:
            name: Original name

        Returns:
            Sanitized name
        """
        # Remove or replace invalid characters
        safe_name = re.sub(r"[^\w\s-]", "", name.lower())
        safe_name = re.sub(r"[-\s]+", "-", safe_name)
        return safe_name.strip("-")

    def _extract_repo_name(self, github_url: str) -> str:
        """
        Extract repository name from GitHub URL

        Args:
            github_url: GitHub repository URL

        Returns:
            Repository name
        """
        # Handle different URL formats
        # https://github.com/user/repo.git
        # git@github.com:user/repo.git
        # https://github.com/user/repo

        match = re.search(r"/([^/]+?)(\.git)?$", github_url)
        if match:
            return match.group(1)

        # Fallback
        return "knowledge-base"

    def _inject_credentials(self, url: str, username: str, token: str) -> str:
        """
        Inject credentials into GitHub URL

        Args:
            url: Original URL
            username: GitHub username
            token: GitHub token

        Returns:
            URL with credentials
        """
        # Convert git@ format to https if needed
        if url.startswith("git@"):
            url = url.replace("git@github.com:", "https://github.com/")

        # Inject credentials
        if "github.com" in url:
            url = url.replace("https://github.com/", f"https://{username}:{token}@github.com/")

        return url

    def _create_initial_structure(self, kb_path: Path) -> None:
        """
        Create initial KB directory structure using config

        Args:
            kb_path: Path to knowledge base
        """

        # Create structure from config
        def create_dirs(base: Path, structure: dict):
            for name, subdirs in structure.items():
                dir_path = base / name
                dir_path.mkdir(exist_ok=True)
                if isinstance(subdirs, dict) and subdirs:
                    create_dirs(dir_path, subdirs)

        create_dirs(kb_path, KB_BASE_STRUCTURE)

        # Create README using config content
        readme_path = kb_path / "README.md"
        readme_path.write_text(README_CONTENT)

        # Create .gitignore using config content
        gitignore_path = kb_path / ".gitignore"
        gitignore_path.write_text(GITIGNORE_CONTENT)
