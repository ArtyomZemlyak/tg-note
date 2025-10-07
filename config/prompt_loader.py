"""
Prompt Loader
Load and manage versioned prompts from YAML files
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger


class PromptLoader:
    """
    Load and manage versioned agent prompts from YAML files
    
    Features:
    - Version management
    - Hot reloading
    - Template rendering
    - Configuration access
    - Fallback to defaults
    
    Usage:
        # Load default (latest) version
        loader = PromptLoader()
        
        # Load specific version
        loader = PromptLoader(version="v1")
        
        # Get instruction
        instruction = loader.get_instruction("qwen_code_cli_agent")
        
        # Get template
        template = loader.get_template("qwen_code_agent", "content_processing")
        
        # Get configuration
        categories = loader.get_config("category_keywords")
    """
    
    def __init__(
        self,
        version: Optional[str] = None,
        prompts_dir: Optional[Path] = None
    ):
        """
        Initialize prompt loader
        
        Args:
            version: Version to load (e.g., "v1", "v2"). If None, uses latest.
            prompts_dir: Custom prompts directory. If None, uses default.
        """
        self.prompts_dir = prompts_dir or Path(__file__).parent / "prompts"
        self.version = version or self._get_latest_version()
        self.version_dir = self.prompts_dir / self.version
        
        # Cache for loaded prompts and config
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._config_cache: Optional[Dict[str, Any]] = None
        
        # Validate version exists
        if not self.version_dir.exists():
            raise ValueError(
                f"Prompt version '{self.version}' not found at {self.version_dir}"
            )
        
        logger.info(f"PromptLoader initialized with version: {self.version}")
    
    def _get_latest_version(self) -> str:
        """
        Get the latest version available
        
        Returns:
            Latest version string (e.g., "v2")
        """
        if not self.prompts_dir.exists():
            raise RuntimeError(f"Prompts directory not found: {self.prompts_dir}")
        
        # Find all version directories (v1, v2, etc.)
        versions = []
        for item in self.prompts_dir.iterdir():
            if item.is_dir() and item.name.startswith("v"):
                try:
                    # Extract version number (v1 -> 1, v2 -> 2)
                    version_num = int(item.name[1:])
                    versions.append((version_num, item.name))
                except ValueError:
                    continue
        
        if not versions:
            raise RuntimeError(f"No prompt versions found in {self.prompts_dir}")
        
        # Return highest version
        versions.sort(reverse=True)
        latest = versions[0][1]
        logger.debug(f"Latest prompt version: {latest}")
        return latest
    
    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """
        Load YAML file
        
        Args:
            file_path: Path to YAML file
        
        Returns:
            Parsed YAML content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                return content or {}
        except Exception as e:
            logger.error(f"Failed to load YAML from {file_path}: {e}")
            raise
    
    def get_instruction(
        self,
        agent_name: str,
        reload: bool = False
    ) -> str:
        """
        Get agent instruction
        
        Args:
            agent_name: Name of the agent (e.g., "qwen_code_cli_agent")
            reload: Force reload from file
        
        Returns:
            Instruction string
        """
        prompt_data = self._get_prompt_data(agent_name, reload)
        instruction = prompt_data.get("instruction", "")
        
        if not instruction:
            logger.warning(f"No instruction found for agent: {agent_name}")
        
        return instruction
    
    def get_template(
        self,
        agent_name: str,
        template_name: str,
        reload: bool = False
    ) -> str:
        """
        Get prompt template
        
        Args:
            agent_name: Name of the agent
            template_name: Name of the template
            reload: Force reload from file
        
        Returns:
            Template string
        """
        prompt_data = self._get_prompt_data(agent_name, reload)
        templates = prompt_data.get("templates", {})
        template = templates.get(template_name, "")
        
        if not template:
            logger.warning(
                f"Template '{template_name}' not found for agent: {agent_name}"
            )
        
        return template
    
    def get_all_templates(
        self,
        agent_name: str,
        reload: bool = False
    ) -> Dict[str, str]:
        """
        Get all templates for an agent
        
        Args:
            agent_name: Name of the agent
            reload: Force reload from file
        
        Returns:
            Dictionary of template name -> template string
        """
        prompt_data = self._get_prompt_data(agent_name, reload)
        return prompt_data.get("templates", {})
    
    def get_metadata(
        self,
        agent_name: str,
        reload: bool = False
    ) -> Dict[str, Any]:
        """
        Get prompt metadata (version, description, language, etc.)
        
        Args:
            agent_name: Name of the agent
            reload: Force reload from file
        
        Returns:
            Metadata dictionary
        """
        prompt_data = self._get_prompt_data(agent_name, reload)
        return {
            "version": prompt_data.get("version"),
            "name": prompt_data.get("name"),
            "description": prompt_data.get("description"),
            "language": prompt_data.get("language"),
            "created_at": prompt_data.get("created_at")
        }
    
    def _get_prompt_data(
        self,
        agent_name: str,
        reload: bool = False
    ) -> Dict[str, Any]:
        """
        Get full prompt data for an agent
        
        Args:
            agent_name: Name of the agent
            reload: Force reload from file
        
        Returns:
            Full prompt data dictionary
        """
        # Check cache first
        if not reload and agent_name in self._cache:
            return self._cache[agent_name]
        
        # Load from file
        file_path = self.version_dir / f"{agent_name}.yaml"
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found for agent '{agent_name}' at {file_path}"
            )
        
        prompt_data = self._load_yaml(file_path)
        
        # Cache the data
        self._cache[agent_name] = prompt_data
        
        logger.debug(f"Loaded prompt data for agent: {agent_name}")
        return prompt_data
    
    def get_config(
        self,
        key: Optional[str] = None,
        default: Any = None,
        reload: bool = False
    ) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key (supports nested keys with dots, e.g., "markdown.max_title_length")
            default: Default value if key not found
            reload: Force reload from file
        
        Returns:
            Configuration value or entire config if key is None
        """
        # Load config if not cached or reload requested
        if self._config_cache is None or reload:
            config_file = self.version_dir / "config.yaml"
            
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_file}")
                self._config_cache = {}
            else:
                self._config_cache = self._load_yaml(config_file)
                logger.debug("Loaded configuration")
        
        # Return entire config if no key specified
        if key is None:
            return self._config_cache
        
        # Navigate nested keys
        value = self._config_cache
        for key_part in key.split('.'):
            if isinstance(value, dict) and key_part in value:
                value = value[key_part]
            else:
                return default
        
        return value
    
    def list_agents(self) -> List[str]:
        """
        List all available agent prompt files
        
        Returns:
            List of agent names
        """
        agents = []
        for file_path in self.version_dir.glob("*.yaml"):
            if file_path.name != "config.yaml":
                agents.append(file_path.stem)
        
        return sorted(agents)
    
    def list_versions(self) -> List[str]:
        """
        List all available versions
        
        Returns:
            List of version strings
        """
        versions = []
        for item in self.prompts_dir.iterdir():
            if item.is_dir() and item.name.startswith("v"):
                versions.append(item.name)
        
        return sorted(versions)
    
    def reload(self) -> None:
        """
        Reload all cached data from files
        """
        self._cache.clear()
        self._config_cache = None
        logger.info("Prompt loader cache cleared")
    
    def format_template(
        self,
        agent_name: str,
        template_name: str,
        **kwargs
    ) -> str:
        """
        Get and format a template with provided variables
        
        Args:
            agent_name: Name of the agent
            template_name: Name of the template
            **kwargs: Template variables
        
        Returns:
            Formatted template string
        """
        template = self.get_template(agent_name, template_name)
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            raise ValueError(f"Missing required template variable: {e}") from e
    
    def get_category_keywords(self) -> Dict[str, List[str]]:
        """
        Get category keywords for content classification
        
        Returns:
            Dictionary mapping category name to list of keywords
        """
        return self.get_config("category_keywords", default={})
    
    def get_default_category(self) -> str:
        """
        Get default category name
        
        Returns:
            Default category string
        """
        return self.get_config("default_category", default="general")
    
    def get_stop_words(self) -> List[str]:
        """
        Get stop words for keyword extraction
        
        Returns:
            List of stop words
        """
        return self.get_config("stop_words", default=[])
    
    def get_markdown_config(self) -> Dict[str, Any]:
        """
        Get markdown generation configuration
        
        Returns:
            Markdown configuration dictionary
        """
        return self.get_config("markdown", default={})
    
    def get_tool_safety_config(self) -> Dict[str, Any]:
        """
        Get tool safety configuration
        
        Returns:
            Tool safety configuration dictionary
        """
        return self.get_config("tools", default={})


# Global instance (singleton pattern)
_default_loader: Optional[PromptLoader] = None


def get_default_loader() -> PromptLoader:
    """
    Get or create default prompt loader instance
    
    Returns:
        Default PromptLoader instance
    """
    global _default_loader
    
    if _default_loader is None:
        _default_loader = PromptLoader()
    
    return _default_loader


def reload_default_loader() -> None:
    """
    Reload the default prompt loader (useful for hot-reloading)
    """
    global _default_loader
    
    if _default_loader is not None:
        _default_loader.reload()
    else:
        _default_loader = PromptLoader()
