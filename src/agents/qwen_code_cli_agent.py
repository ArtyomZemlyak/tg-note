"""
Qwen Code CLI Agent
Python wrapper for qwen-code CLI tool with autonomous agent capabilities
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, KBStructure
from config.agent_prompts import (
    QWEN_CODE_CLI_AGENT_INSTRUCTION,
    CONTENT_PROCESSING_PROMPT_TEMPLATE,
    URLS_SECTION_TEMPLATE,
    CATEGORY_KEYWORDS,
    DEFAULT_CATEGORY,
    STOP_WORDS,
    MAX_TITLE_LENGTH,
    MAX_SUMMARY_LENGTH,
    MAX_TAG_COUNT,
    MIN_KEYWORD_LENGTH,
)


logger = logging.getLogger(__name__)


class QwenCodeCLIAgent(BaseAgent):
    """
    Agent that uses qwen-code CLI for autonomous processing
    
    Features:
    - Direct integration with qwen-code CLI
    - Autonomous mode (no user interaction)
    - TODO plan generation via qwen-code
    - Built-in tool support (web search, git, github, shell commands)
    - Configurable instruction system
    """
    
    DEFAULT_INSTRUCTION = QWEN_CODE_CLI_AGENT_INSTRUCTION
    
    def __init__(
        self,
        config: Optional[Dict] = None,
        instruction: Optional[str] = None,
        qwen_cli_path: str = "qwen",
        working_directory: Optional[str] = None,
        enable_web_search: bool = True,
        enable_git: bool = True,
        enable_github: bool = True,
        timeout: int = 300  # 5 minutes default timeout
    ):
        """
        Initialize Qwen Code CLI Agent
        
        Args:
            config: Configuration dictionary
            instruction: Custom instruction for the agent
            qwen_cli_path: Path to qwen CLI executable
            working_directory: Working directory for qwen CLI
            enable_web_search: Enable web search tool
            enable_git: Enable git command tool
            enable_github: Enable GitHub API tool
            timeout: Timeout in seconds for CLI commands
        """
        super().__init__(config)
        
        self.instruction = instruction or self.DEFAULT_INSTRUCTION
        self.qwen_cli_path = qwen_cli_path
        self.working_directory = working_directory or os.getcwd()
        self.timeout = timeout
        
        # Tool settings
        self.enable_web_search = enable_web_search
        self.enable_git = enable_git
        self.enable_github = enable_github
        
        # Check if qwen CLI is available
        self._check_cli_available()
        
        logger.info(f"QwenCodeCLIAgent initialized")
        logger.info(f"Working directory: {self.working_directory}")
        logger.info(f"CLI path: {self.qwen_cli_path}")
    
    def _check_cli_available(self) -> None:
        """
        Check if qwen CLI is available and properly configured
        
        Raises:
            RuntimeError: If qwen CLI is not found or not working
        """
        try:
            result = subprocess.run(
                [self.qwen_cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Qwen CLI found: {result.stdout.strip()}")
            else:
                error_msg = result.stderr.strip()
                logger.warning(f"Qwen CLI check returned non-zero exit code {result.returncode}")
                logger.warning(f"Qwen CLI stderr: {error_msg}")
                raise RuntimeError(
                    f"Qwen CLI check failed with exit code {result.returncode}. "
                    f"Error: {error_msg}"
                )
        except FileNotFoundError:
            logger.error(
                f"Qwen CLI not found at '{self.qwen_cli_path}'. "
                f"Please install: npm install -g @qwen-code/qwen-code@latest"
            )
            raise RuntimeError(
                f"Qwen CLI not found at '{self.qwen_cli_path}'. "
                f"Install with: npm install -g @qwen-code/qwen-code@latest"
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Qwen CLI version check timed out after 10 seconds")
            raise RuntimeError("Qwen CLI version check timed out")
        except Exception as e:
            logger.error(f"Unexpected error checking qwen CLI: {e}", exc_info=True)
            raise RuntimeError(f"Failed to verify qwen CLI installation: {e}") from e
    
    async def process(self, content: Dict) -> Dict:
        """
        Process content autonomously using qwen-code CLI
        
        Args:
            content: Content dictionary with text, urls, etc.
        
        Returns:
            Processed content dictionary with markdown, metadata, and KB structure
        
        Raises:
            ValueError: If input content is invalid
            RuntimeError: If qwen CLI execution fails
            Exception: For other processing errors
        """
        if not self.validate_input(content):
            logger.error(f"Invalid input content: {content}")
            raise ValueError("Invalid input content: must be a dict with 'text' key")
        
        logger.info("Starting autonomous content processing with qwen-code CLI...")
        
        try:
            # Step 1: Prepare prompt for qwen-code
            prompt = self._prepare_prompt(content)
            logger.debug(f"Prepared prompt length: {len(prompt)} characters")
            
            # Step 2: Execute qwen-code CLI
            result_text = await self._execute_qwen_cli(prompt)
            logger.debug(f"Received result length: {len(result_text)} characters")
            
            # Step 3: Parse result
            parsed_result = self._parse_qwen_result(result_text)
            logger.info(f"Parsed result: title='{parsed_result.get('title')}', category='{parsed_result.get('category')}'")
            
            # Step 4: Extract components with fallbacks
            markdown_content = parsed_result.get("markdown", result_text)
            title = parsed_result.get("title") or self._extract_title(result_text) or "Untitled Note"
            category = parsed_result.get("category") or self._detect_category(content.get("text", "")) or "general"
            tags = parsed_result.get("tags") or self._extract_tags(content.get("text", "")) or ["untagged"]
            
            # Validate extracted components
            if not markdown_content:
                logger.error("No markdown content generated")
                raise ValueError("Processing failed: no markdown content generated")
            
            # Step 5: Determine KB structure
            kb_structure = KBStructure(
                category=category,
                subcategory=parsed_result.get("subcategory"),
                tags=tags
            )
            
            logger.info(f"Created KB structure: {kb_structure.to_dict()}")
            
            # Generate metadata
            metadata = {
                "processed_at": datetime.now().isoformat(),
                "agent": "QwenCodeCLIAgent",
                "version": "1.0.0",
                "instruction_used": bool(self.instruction != self.DEFAULT_INSTRUCTION),
                "tools_enabled": {
                    "web_search": self.enable_web_search,
                    "git": self.enable_git,
                    "github": self.enable_github
                },
                "todo_plan": parsed_result.get("todo_plan", [])
            }
            
            result = {
                "markdown": markdown_content,
                "metadata": metadata,
                "title": title,
                "kb_structure": kb_structure
            }
            
            logger.info(f"Successfully processed content: title='{title}', category='{category}'")
            return result
        
        except ValueError as ve:
            # Re-raise validation errors with context
            logger.error(f"Validation error during processing: {ve}")
            raise
        
        except RuntimeError as re:
            # Re-raise runtime errors (e.g., CLI failures) with context
            logger.error(f"Runtime error during processing: {re}")
            raise
        
        except Exception as e:
            # Log and wrap unexpected errors
            logger.error(f"Unexpected error processing content: {e}", exc_info=True)
            raise RuntimeError(f"Failed to process content: {e}") from e
    
    def _prepare_prompt(self, content: Dict) -> str:
        """
        Prepare prompt for qwen-code CLI using template from config
        
        Args:
            content: Content dictionary
        
        Returns:
            Formatted prompt string
        """
        text = content.get("text", "")
        urls = content.get("urls", [])
        
        # Build URLs section if URLs present
        urls_section = ""
        if urls:
            url_list = "\n".join([f"- {url}" for url in urls])
            urls_section = URLS_SECTION_TEMPLATE.format(url_list=url_list)
        
        # Use template from config
        return CONTENT_PROCESSING_PROMPT_TEMPLATE.format(
            instruction=self.instruction,
            text=text,
            urls_section=urls_section
        )
    
    async def _execute_qwen_cli(self, prompt: str) -> str:
        """
        Execute qwen-code CLI with the given prompt
        
        Args:
            prompt: Prompt to send to qwen-code
        
        Returns:
            CLI output as string
        """
        logger.info("Executing qwen-code CLI...")
        
        # Create temporary file for prompt
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False,
            encoding='utf-8'
        ) as tmp_file:
            tmp_file.write(prompt)
            tmp_file_path = tmp_file.name
        
        try:
            # Prepare environment
            env = os.environ.copy()
            
            # Build command
            # Use non-interactive mode and pass prompt via stdin
            cmd = [self.qwen_cli_path]
            
            # Read prompt from file
            with open(tmp_file_path, 'r', encoding='utf-8') as f:
                prompt_text = f.read()
            
            # Execute qwen CLI in non-interactive mode
            # We'll use subprocess with input to send the prompt
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory,
                env=env
            )
            
            try:
                # Send prompt and get response
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt_text.encode('utf-8')),
                    timeout=self.timeout
                )
                
                if process.returncode != 0:
                    error_msg = stderr.decode().strip()
                    logger.warning(f"Qwen CLI returned non-zero exit code {process.returncode}")
                    logger.warning(f"Qwen CLI stderr: {error_msg}")
                    
                    # If we have an error message, include it in the result for debugging
                    if error_msg and not result:
                        logger.error(f"Qwen CLI failed with: {error_msg}")
                        raise RuntimeError(f"Qwen CLI execution failed: {error_msg}")
                
                result = stdout.decode('utf-8').strip()
                
                if not result:
                    logger.warning("Empty result from qwen CLI, using fallback processing")
                    # Fallback to simple processing
                    try:
                        result = self._fallback_processing(prompt)
                    except Exception as fallback_error:
                        logger.error(f"Fallback processing also failed: {fallback_error}")
                        raise RuntimeError(
                            f"Both qwen CLI and fallback processing failed. "
                            f"CLI error: empty result, Fallback error: {fallback_error}"
                        )
                
                return result
            
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.error(f"Qwen CLI timeout after {self.timeout} seconds")
                raise TimeoutError(f"Qwen CLI execution timeout after {self.timeout}s")
        
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")
    
    def _fallback_processing(self, prompt: str) -> str:
        """
        Fallback processing when qwen CLI fails or returns empty
        
        Args:
            prompt: Original prompt
        
        Returns:
            Basic processed markdown
        """
        logger.info("Using fallback processing")
        
        # Extract text from prompt
        lines = prompt.split("\n")
        text_content = []
        in_content = False
        
        for line in lines:
            if "## Text Content" in line:
                in_content = True
                continue
            elif line.startswith("## URLs") or line.startswith("# Task"):
                in_content = False
            elif in_content and line.strip():
                text_content.append(line)
        
        text = "\n".join(text_content)
        
        # Validate text is not empty
        if not text.strip():
            logger.warning("No text content found in prompt, using minimal fallback")
            text = "No content available"
        
        # Generate basic markdown with guaranteed valid values
        title = self._extract_title(text) or "Untitled Note"
        category = self._detect_category(text) or "general"
        tags = self._extract_tags(text) or ["untagged"]
        
        markdown = f"""# {title}

## Metadata

- **Category**: {category}
- **Tags**: {', '.join(tags)}
- **Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Content

{text}

## Summary

{self._generate_summary(text)}
"""
        return markdown
    
    def _parse_qwen_result(self, result_text: str) -> Dict[str, Any]:
        """
        Parse result from qwen-code CLI
        
        Args:
            result_text: Raw result from CLI
        
        Returns:
            Parsed result dictionary with validated values
        """
        parsed = {
            "markdown": result_text,
            "title": None,
            "category": None,
            "subcategory": None,
            "tags": [],
            "todo_plan": []
        }
        
        # Extract title (first # heading)
        for line in result_text.split("\n"):
            if line.startswith("# "):
                parsed["title"] = line[2:].strip()
                break
        
        # Extract metadata block
        if "```metadata" in result_text:
            try:
                start = result_text.find("```metadata") + 11
                end = result_text.find("```", start)
                if end > start:
                    metadata_block = result_text[start:end].strip()
                    for line in metadata_block.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip().lower()
                            value = value.strip()
                            
                            if key == "category" and value:
                                parsed["category"] = value
                            elif key == "subcategory" and value:
                                parsed["subcategory"] = value
                            elif key == "tags" and value:
                                parsed["tags"] = [t.strip() for t in value.split(",") if t.strip()]
            except Exception as e:
                logger.warning(f"Error parsing metadata block: {e}")
        
        # Extract TODO plan (look for checklist)
        try:
            todo_items = []
            for line in result_text.split("\n"):
                if line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
                    todo_items.append(line.strip())
            
            if todo_items:
                parsed["todo_plan"] = todo_items
        except Exception as e:
            logger.warning(f"Error parsing TODO plan: {e}")
        
        # Ensure we have at least default values
        if not parsed["title"]:
            logger.warning("No title found in qwen result, using default")
            parsed["title"] = "Untitled Note"
        
        if not parsed["category"]:
            logger.warning("No category found in qwen result, using 'general'")
            parsed["category"] = "general"
        
        if not parsed["tags"]:
            logger.warning("No tags found in qwen result, using default")
            parsed["tags"] = ["untagged"]
        
        return parsed
    
    def _extract_title(self, text: str) -> str:
        """Extract title from text using max length from config"""
        lines = text.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 10:
                # Take first meaningful line
                if len(line) > MAX_TITLE_LENGTH:
                    return line[:MAX_TITLE_LENGTH] + "..."
                return line
        
        return "Untitled Note"
    
    def _detect_category(self, text: str) -> str:
        """Detect content category using keywords from config"""
        text_lower = text.lower()
        
        # Use category keywords from config
        categories = CATEGORY_KEYWORDS
        
        scores = {}
        for category, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score
        
        return max(scores, key=scores.get) if scores else DEFAULT_CATEGORY
    
    def _extract_tags(self, text: str, max_tags: int = MAX_TAG_COUNT) -> List[str]:
        """Extract tags from text using stop words from config"""
        # Use stop words from config
        stop_words = STOP_WORDS
        words = text.lower().split()
        
        word_freq = {}
        for word in words:
            word = word.strip(".,!?;:()[]{}\"'")
            if len(word) > MIN_KEYWORD_LENGTH and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_tags]]
    
    def _generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate summary from text"""
        paragraphs = text.split("\n\n")
        first_para = paragraphs[0].strip() if paragraphs else text[:max_length]
        
        if len(first_para) > max_length:
            return first_para[:max_length].strip() + "..."
        
        return first_para
    
    def validate_input(self, content: Dict) -> bool:
        """Validate input content"""
        return isinstance(content, dict) and "text" in content
    
    def set_instruction(self, instruction: str) -> None:
        """Update agent instruction"""
        self.instruction = instruction
        logger.info("Agent instruction updated")
    
    def get_instruction(self) -> str:
        """Get current instruction"""
        return self.instruction
    
    @staticmethod
    def check_installation() -> bool:
        """
        Check if qwen-code CLI is installed
        
        Returns:
            True if installed, False otherwise
        """
        try:
            result = subprocess.run(
                ["qwen", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @staticmethod
    def get_installation_instructions() -> str:
        """
        Get installation instructions for qwen-code CLI
        
        Returns:
            Installation instructions
        """
        return """
To install qwen-code CLI:

1. Ensure Node.js 20+ is installed:
   curl -qL https://www.npmjs.com/install.sh | sh

2. Install qwen-code globally:
   npm install -g @qwen-code/qwen-code@latest

3. Verify installation:
   qwen --version

4. Configure authentication (choose one):
   
   a) Qwen OAuth (Recommended - 2000 requests/day):
      qwen
      # Follow authentication prompts
   
   b) OpenAI-compatible API:
      export OPENAI_API_KEY="your-api-key"
      export OPENAI_BASE_URL="your-base-url"

For more information, visit: https://github.com/QwenLM/qwen-code
"""
