"""
Example: Using PromptLoader for Flexible Prompt Management

This example demonstrates how to use the new YAML-based prompt system
with versioning and hot-reloading capabilities.
"""

from config.prompt_loader import PromptLoader


def basic_usage():
    """Basic usage of PromptLoader"""
    print("=== Basic Usage ===\n")
    
    # Load default (latest) version
    loader = PromptLoader()
    
    print(f"Current version: {loader.version}")
    print(f"Available agents: {loader.list_agents()}")
    print(f"Available versions: {loader.list_versions()}\n")
    
    # Get agent instruction
    instruction = loader.get_instruction("qwen_code_cli_agent")
    print(f"Instruction length: {len(instruction)} characters")
    print(f"First 200 chars: {instruction[:200]}...\n")


def using_templates():
    """Using templates with formatting"""
    print("=== Using Templates ===\n")
    
    loader = PromptLoader()
    
    # Get and format template
    formatted = loader.format_template(
        "qwen_code_agent",
        "content_processing",
        instruction="Custom instruction here",
        text="Some content to process",
        urls_section=""
    )
    
    print(f"Formatted template length: {len(formatted)} characters")
    print(f"Preview:\n{formatted[:300]}...\n")


def using_configuration():
    """Accessing configuration values"""
    print("=== Using Configuration ===\n")
    
    loader = PromptLoader()
    
    # Get category keywords
    categories = loader.get_category_keywords()
    print(f"Available categories: {list(categories.keys())}")
    
    # Get specific config value
    max_title = loader.get_config("markdown.max_title_length")
    print(f"Max title length: {max_title}")
    
    # Get stop words
    stop_words = loader.get_stop_words()
    print(f"Number of stop words: {len(stop_words)}")
    
    # Get tool safety config
    safe_commands = loader.get_config("tools.safe_git_commands")
    print(f"Safe git commands: {safe_commands}\n")


def versioning():
    """Working with different versions"""
    print("=== Versioning ===\n")
    
    # Load specific version
    loader_v1 = PromptLoader(version="v1")
    print(f"Loaded version: {loader_v1.version}")
    
    # Get metadata for a prompt
    metadata = loader_v1.get_metadata("qwen_code_cli_agent")
    print(f"Prompt metadata: {metadata}\n")


def hot_reloading():
    """Hot reloading prompts without restart"""
    print("=== Hot Reloading ===\n")
    
    loader = PromptLoader()
    
    # Get instruction
    instruction_before = loader.get_instruction("stub_agent")
    print(f"Before reload: {instruction_before[:100]}")
    
    # Reload from files (useful in development)
    loader.reload()
    
    # Get instruction again
    instruction_after = loader.get_instruction("stub_agent")
    print(f"After reload: {instruction_after[:100]}\n")


def agent_integration():
    """How to integrate with agents"""
    print("=== Agent Integration ===\n")
    
    loader = PromptLoader()
    
    # Example: Custom agent with specific prompt version
    class CustomAgent:
        def __init__(self, prompt_version="v1"):
            self.loader = PromptLoader(version=prompt_version)
            self.instruction = self.loader.get_instruction("qwen_code_agent")
        
        def get_template(self, name):
            return self.loader.get_template("qwen_code_agent", name)
    
    agent = CustomAgent(prompt_version="v1")
    print(f"Agent using prompt version: {agent.loader.version}")
    print(f"Instruction loaded: {len(agent.instruction)} characters\n")


def backward_compatibility():
    """Using the old API (still works!)"""
    print("=== Backward Compatibility ===\n")
    
    # Old way - still works via agent_prompts.py
    from config.agent_prompts import (
        QWEN_CODE_CLI_AGENT_INSTRUCTION,
        CONTENT_PROCESSING_PROMPT_TEMPLATE,
        CATEGORY_KEYWORDS,
        MAX_TITLE_LENGTH
    )
    
    print(f"Old API still works!")
    print(f"Instruction length: {len(QWEN_CODE_CLI_AGENT_INSTRUCTION)}")
    print(f"Max title length: {MAX_TITLE_LENGTH}")
    print(f"Categories available: {len(CATEGORY_KEYWORDS)}\n")


def main():
    """Run all examples"""
    print("=" * 60)
    print("PromptLoader Examples")
    print("=" * 60)
    print()
    
    basic_usage()
    using_templates()
    using_configuration()
    versioning()
    hot_reloading()
    agent_integration()
    backward_compatibility()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
