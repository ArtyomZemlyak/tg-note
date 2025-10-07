"""
Tests for PromptLoader
Test versioned YAML-based prompt system
"""

import pytest
from pathlib import Path
from config.prompt_loader import PromptLoader, get_default_loader, reload_default_loader


class TestPromptLoaderBasics:
    """Test basic PromptLoader functionality"""
    
    def test_initialization(self):
        """Test loader initialization"""
        loader = PromptLoader()
        assert loader is not None
        assert loader.version.startswith("v")
        assert loader.version_dir.exists()
    
    def test_initialization_with_version(self):
        """Test loader with specific version"""
        loader = PromptLoader(version="v1")
        assert loader.version == "v1"
        assert loader.version_dir.exists()
    
    def test_invalid_version_raises_error(self):
        """Test that invalid version raises error"""
        with pytest.raises(ValueError):
            PromptLoader(version="v999")
    
    def test_list_agents(self):
        """Test listing available agents"""
        loader = PromptLoader()
        agents = loader.list_agents()
        
        assert isinstance(agents, list)
        assert len(agents) > 0
        assert "qwen_code_agent" in agents
        assert "qwen_code_cli_agent" in agents
        assert "kb_query" in agents
        assert "stub_agent" in agents
    
    def test_list_versions(self):
        """Test listing available versions"""
        loader = PromptLoader()
        versions = loader.list_versions()
        
        assert isinstance(versions, list)
        assert len(versions) > 0
        assert "v1" in versions


class TestInstructionLoading:
    """Test loading agent instructions"""
    
    def test_get_instruction(self):
        """Test getting agent instruction"""
        loader = PromptLoader()
        instruction = loader.get_instruction("qwen_code_cli_agent")
        
        assert isinstance(instruction, str)
        assert len(instruction) > 0
        assert "автономный агент" in instruction.lower()
    
    def test_get_instruction_english(self):
        """Test getting English instruction"""
        loader = PromptLoader()
        instruction = loader.get_instruction("qwen_code_agent")
        
        assert isinstance(instruction, str)
        assert len(instruction) > 0
        assert "autonomous" in instruction.lower()
    
    def test_get_instruction_not_found(self):
        """Test getting non-existent instruction"""
        loader = PromptLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.get_instruction("non_existent_agent")
    
    def test_instruction_caching(self):
        """Test that instructions are cached"""
        loader = PromptLoader()
        
        # First call loads from file
        instruction1 = loader.get_instruction("qwen_code_cli_agent")
        
        # Second call should use cache
        instruction2 = loader.get_instruction("qwen_code_cli_agent")
        
        assert instruction1 == instruction2
        assert "qwen_code_cli_agent" in loader._cache


class TestTemplateLoading:
    """Test loading and formatting templates"""
    
    def test_get_template(self):
        """Test getting template"""
        loader = PromptLoader()
        template = loader.get_template("qwen_code_agent", "content_processing")
        
        assert isinstance(template, str)
        assert len(template) > 0
        assert "{instruction}" in template
        assert "{text}" in template
    
    def test_get_all_templates(self):
        """Test getting all templates for an agent"""
        loader = PromptLoader()
        templates = loader.get_all_templates("qwen_code_agent")
        
        assert isinstance(templates, dict)
        assert len(templates) > 0
        assert "content_processing" in templates
        assert "urls_section" in templates
    
    def test_format_template(self):
        """Test formatting template with variables"""
        loader = PromptLoader()
        
        formatted = loader.format_template(
            "qwen_code_agent",
            "content_processing",
            instruction="Test instruction",
            text="Test content",
            urls_section="Test URLs"
        )
        
        assert "Test instruction" in formatted
        assert "Test content" in formatted
        assert "Test URLs" in formatted
        assert "{instruction}" not in formatted  # Placeholders replaced
    
    def test_format_template_missing_variable(self):
        """Test that missing variable raises error"""
        loader = PromptLoader()
        
        with pytest.raises(ValueError):
            loader.format_template(
                "qwen_code_agent",
                "content_processing",
                instruction="Test"
                # Missing 'text' and 'urls_section'
            )


class TestConfigurationLoading:
    """Test loading configuration"""
    
    def test_get_config_full(self):
        """Test getting full configuration"""
        loader = PromptLoader()
        config = loader.get_config()
        
        assert isinstance(config, dict)
        assert "category_keywords" in config
        assert "stop_words" in config
        assert "markdown" in config
        assert "tools" in config
    
    def test_get_config_nested(self):
        """Test getting nested configuration"""
        loader = PromptLoader()
        
        # Get nested value with dot notation
        max_title = loader.get_config("markdown.max_title_length")
        assert isinstance(max_title, int)
        assert max_title == 60
        
        # Get nested dict
        markdown_config = loader.get_config("markdown")
        assert isinstance(markdown_config, dict)
        assert "max_title_length" in markdown_config
    
    def test_get_config_with_default(self):
        """Test getting config with default value"""
        loader = PromptLoader()
        
        # Existing key
        value = loader.get_config("default_category", default="unknown")
        assert value == "general"
        
        # Non-existing key
        value = loader.get_config("non_existent_key", default="default_value")
        assert value == "default_value"
    
    def test_get_category_keywords(self):
        """Test getting category keywords"""
        loader = PromptLoader()
        keywords = loader.get_category_keywords()
        
        assert isinstance(keywords, dict)
        assert "ai" in keywords
        assert "biology" in keywords
        assert isinstance(keywords["ai"], list)
        assert len(keywords["ai"]) > 0
    
    def test_get_default_category(self):
        """Test getting default category"""
        loader = PromptLoader()
        category = loader.get_default_category()
        
        assert isinstance(category, str)
        assert category == "general"
    
    def test_get_stop_words(self):
        """Test getting stop words"""
        loader = PromptLoader()
        stop_words = loader.get_stop_words()
        
        assert isinstance(stop_words, list)
        assert len(stop_words) > 0
        assert "the" in stop_words
        assert "and" in stop_words
    
    def test_get_markdown_config(self):
        """Test getting markdown configuration"""
        loader = PromptLoader()
        config = loader.get_markdown_config()
        
        assert isinstance(config, dict)
        assert "max_title_length" in config
        assert "max_summary_length" in config
        assert config["max_title_length"] == 60
    
    def test_get_tool_safety_config(self):
        """Test getting tool safety configuration"""
        loader = PromptLoader()
        config = loader.get_tool_safety_config()
        
        assert isinstance(config, dict)
        assert "safe_git_commands" in config
        assert "dangerous_shell_patterns" in config
        assert isinstance(config["safe_git_commands"], list)


class TestMetadata:
    """Test prompt metadata"""
    
    def test_get_metadata(self):
        """Test getting prompt metadata"""
        loader = PromptLoader()
        metadata = loader.get_metadata("qwen_code_cli_agent")
        
        assert isinstance(metadata, dict)
        assert "version" in metadata
        assert "name" in metadata
        assert "description" in metadata
        assert "language" in metadata
        assert "created_at" in metadata
        
        assert metadata["name"] == "qwen_code_cli_agent"
        assert metadata["language"] == "ru"
    
    def test_metadata_english_agent(self):
        """Test metadata for English agent"""
        loader = PromptLoader()
        metadata = loader.get_metadata("qwen_code_agent")
        
        assert metadata["language"] == "en"


class TestCaching:
    """Test caching functionality"""
    
    def test_cache_is_used(self):
        """Test that cache is used"""
        loader = PromptLoader()
        
        # Load instruction
        instruction1 = loader.get_instruction("qwen_code_cli_agent")
        
        # Check cache
        assert "qwen_code_cli_agent" in loader._cache
        
        # Load again - should use cache
        instruction2 = loader.get_instruction("qwen_code_cli_agent")
        
        assert instruction1 is instruction2  # Same object
    
    def test_reload_clears_cache(self):
        """Test that reload clears cache"""
        loader = PromptLoader()
        
        # Load instruction
        loader.get_instruction("qwen_code_cli_agent")
        assert len(loader._cache) > 0
        
        # Reload
        loader.reload()
        
        # Cache should be cleared
        assert len(loader._cache) == 0
        assert loader._config_cache is None
    
    def test_reload_flag(self):
        """Test reload flag on get methods"""
        loader = PromptLoader()
        
        # Load instruction
        loader.get_instruction("qwen_code_cli_agent")
        assert "qwen_code_cli_agent" in loader._cache
        
        # Load with reload=True
        instruction = loader.get_instruction("qwen_code_cli_agent", reload=True)
        
        # Should still be in cache after reload
        assert "qwen_code_cli_agent" in loader._cache


class TestGlobalInstance:
    """Test global instance functions"""
    
    def test_get_default_loader(self):
        """Test getting default loader"""
        loader = get_default_loader()
        
        assert loader is not None
        assert isinstance(loader, PromptLoader)
    
    def test_default_loader_is_singleton(self):
        """Test that default loader is singleton"""
        loader1 = get_default_loader()
        loader2 = get_default_loader()
        
        assert loader1 is loader2  # Same instance
    
    def test_reload_default_loader(self):
        """Test reloading default loader"""
        loader1 = get_default_loader()
        
        # Reload
        reload_default_loader()
        
        loader2 = get_default_loader()
        
        # Should still be same instance, but cache cleared
        assert loader2 is not None


class TestBackwardCompatibility:
    """Test backward compatibility with old API"""
    
    def test_import_old_constants(self):
        """Test that old constants can still be imported"""
        from config.agent_prompts import (
            QWEN_CODE_CLI_AGENT_INSTRUCTION,
            QWEN_CODE_AGENT_INSTRUCTION,
            STUB_AGENT_INSTRUCTION,
            CATEGORY_KEYWORDS,
            DEFAULT_CATEGORY,
            STOP_WORDS,
            MAX_TITLE_LENGTH,
            MAX_SUMMARY_LENGTH,
            SAFE_GIT_COMMANDS,
            DANGEROUS_SHELL_PATTERNS
        )
        
        # Check that they exist and have correct types
        assert isinstance(QWEN_CODE_CLI_AGENT_INSTRUCTION, str)
        assert isinstance(QWEN_CODE_AGENT_INSTRUCTION, str)
        assert isinstance(STUB_AGENT_INSTRUCTION, str)
        assert isinstance(CATEGORY_KEYWORDS, dict)
        assert isinstance(DEFAULT_CATEGORY, str)
        assert isinstance(STOP_WORDS, set)
        assert isinstance(MAX_TITLE_LENGTH, int)
        assert isinstance(MAX_SUMMARY_LENGTH, int)
        assert isinstance(SAFE_GIT_COMMANDS, list)
        assert isinstance(DANGEROUS_SHELL_PATTERNS, list)
    
    def test_old_constants_match_new(self):
        """Test that old constants match new loader values"""
        from config.agent_prompts import (
            QWEN_CODE_CLI_AGENT_INSTRUCTION,
            MAX_TITLE_LENGTH,
            DEFAULT_CATEGORY
        )
        
        loader = PromptLoader()
        
        # Compare values
        assert QWEN_CODE_CLI_AGENT_INSTRUCTION == loader.get_instruction("qwen_code_cli_agent")
        assert MAX_TITLE_LENGTH == loader.get_config("markdown.max_title_length")
        assert DEFAULT_CATEGORY == loader.get_default_category()
    
    def test_helper_functions(self):
        """Test backward compatibility helper functions"""
        from config.agent_prompts import (
            reload_prompts,
            get_prompt_version,
            list_available_agents,
            list_prompt_versions
        )
        
        # Test functions exist and work
        version = get_prompt_version()
        assert isinstance(version, str)
        
        agents = list_available_agents()
        assert isinstance(agents, list)
        assert len(agents) > 0
        
        versions = list_prompt_versions()
        assert isinstance(versions, list)
        assert len(versions) > 0
        
        # Test reload (should not raise)
        reload_prompts()


class TestErrorHandling:
    """Test error handling"""
    
    def test_missing_prompt_file(self):
        """Test handling of missing prompt file"""
        loader = PromptLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.get_instruction("non_existent_agent")
    
    def test_invalid_version(self):
        """Test handling of invalid version"""
        with pytest.raises(ValueError):
            PromptLoader(version="invalid_version")
    
    def test_missing_template(self):
        """Test handling of missing template"""
        loader = PromptLoader()
        
        # Should return empty string and log warning
        template = loader.get_template("qwen_code_agent", "non_existent_template")
        assert template == ""
    
    def test_missing_config_key(self):
        """Test handling of missing config key"""
        loader = PromptLoader()
        
        # Should return default value
        value = loader.get_config("non.existent.key", default="default")
        assert value == "default"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
