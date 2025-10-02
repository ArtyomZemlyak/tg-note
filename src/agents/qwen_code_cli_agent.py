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
    
    DEFAULT_INSTRUCTION = """You are an autonomous knowledge base agent.
Your task is to analyze content, extract key information, and create structured notes.

Process:
1. Analyze the provided content thoroughly
2. Create a TODO plan for processing (use clear markdown checklist)
3. Execute the plan step by step
4. Extract key topics, entities, and relationships
5. Structure the information with proper hierarchy
6. Generate well-formatted markdown content

Guidelines:
- Work autonomously without asking questions
- Be thorough and extract all important information
- Categorize content appropriately (AI, tech, science, etc.)
- Generate clear, concise summaries
- Include relevant metadata and tags
"""
    
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
        """Check if qwen CLI is available"""
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
                logger.warning(f"Qwen CLI check returned non-zero: {result.stderr}")
        except FileNotFoundError:
            logger.error(
                f"Qwen CLI not found at '{self.qwen_cli_path}'. "
                f"Please install: npm install -g @qwen-code/qwen-code@latest"
            )
            raise RuntimeError(
                f"Qwen CLI not found. Install with: npm install -g @qwen-code/qwen-code@latest"
            )
        except Exception as e:
            logger.error(f"Error checking qwen CLI: {e}")
            raise
    
    async def process(self, content: Dict) -> Dict:
        """
        Process content autonomously using qwen-code CLI
        
        Args:
            content: Content dictionary with text, urls, etc.
        
        Returns:
            Processed content dictionary with markdown, metadata, and KB structure
        """
        if not self.validate_input(content):
            raise ValueError("Invalid input content")
        
        logger.info("Starting autonomous content processing with qwen-code CLI...")
        
        try:
            # Step 1: Prepare prompt for qwen-code
            prompt = self._prepare_prompt(content)
            
            # Step 2: Execute qwen-code CLI
            result_text = await self._execute_qwen_cli(prompt)
            
            # Step 3: Parse result
            parsed_result = self._parse_qwen_result(result_text)
            
            # Step 4: Extract components
            markdown_content = parsed_result.get("markdown", result_text)
            title = parsed_result.get("title", self._extract_title(result_text))
            category = parsed_result.get("category", self._detect_category(content["text"]))
            tags = parsed_result.get("tags", self._extract_tags(content["text"]))
            
            # Step 5: Determine KB structure
            kb_structure = KBStructure(
                category=category,
                subcategory=parsed_result.get("subcategory"),
                tags=tags
            )
            
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
            
            return {
                "markdown": markdown_content,
                "metadata": metadata,
                "title": title,
                "kb_structure": kb_structure
            }
        
        except Exception as e:
            logger.error(f"Error processing content: {e}", exc_info=True)
            raise
    
    def _prepare_prompt(self, content: Dict) -> str:
        """
        Prepare prompt for qwen-code CLI
        
        Args:
            content: Content dictionary
        
        Returns:
            Formatted prompt string
        """
        text = content.get("text", "")
        urls = content.get("urls", [])
        
        prompt_parts = [
            self.instruction,
            "",
            "# Input Content",
            "",
            "## Text Content",
            text,
            ""
        ]
        
        if urls:
            prompt_parts.extend([
                "## URLs",
                *[f"- {url}" for url in urls],
                ""
            ])
        
        prompt_parts.extend([
            "# Task",
            "",
            "1. Create a TODO checklist for processing this content",
            "2. Analyze the content and extract key information",
            "3. Determine the category (ai, tech, biology, physics, science, business, general)",
            "4. Extract relevant tags (3-5 keywords)",
            "5. Generate a structured markdown document with:",
            "   - Title (clear and descriptive)",
            "   - Metadata section (category, tags)",
            "   - Summary (2-3 sentences)",
            "   - Main content (well-structured)",
            "   - Links section (if URLs present)",
            "   - Key takeaways",
            "",
            "Format your response as valid markdown. Start with a clear title (# Title).",
            "Include a metadata section in the format:",
            "```metadata",
            "category: <category>",
            "tags: tag1, tag2, tag3",
            "```",
            "",
            "Work autonomously and provide complete output without asking questions."
        ])
        
        return "\n".join(prompt_parts)
    
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
                    logger.warning(f"Qwen CLI returned non-zero: {stderr.decode()}")
                
                result = stdout.decode('utf-8').strip()
                
                if not result:
                    logger.warning("Empty result from qwen CLI")
                    # Fallback to simple processing
                    result = self._fallback_processing(prompt)
                
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
        
        # Generate basic markdown
        title = self._extract_title(text)
        category = self._detect_category(text)
        tags = self._extract_tags(text)
        
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
            Parsed result dictionary
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
            start = result_text.find("```metadata") + 11
            end = result_text.find("```", start)
            if end > start:
                metadata_block = result_text[start:end].strip()
                for line in metadata_block.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key == "category":
                            parsed["category"] = value
                        elif key == "subcategory":
                            parsed["subcategory"] = value
                        elif key == "tags":
                            parsed["tags"] = [t.strip() for t in value.split(",")]
        
        # Extract TODO plan (look for checklist)
        todo_items = []
        for line in result_text.split("\n"):
            if line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
                todo_items.append(line.strip())
        
        if todo_items:
            parsed["todo_plan"] = todo_items
        
        return parsed
    
    def _extract_title(self, text: str) -> str:
        """Extract title from text"""
        lines = text.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 10:
                # Take first meaningful line
                if len(line) > 60:
                    return line[:60] + "..."
                return line
        
        return "Untitled Note"
    
    def _detect_category(self, text: str) -> str:
        """Detect content category"""
        text_lower = text.lower()
        
        categories = {
            "ai": ["ai", "artificial intelligence", "machine learning", "neural network", 
                   "deep learning", "llm", "gpt", "transformer"],
            "tech": ["programming", "code", "software", "development", "python", 
                    "javascript", "api", "database"],
            "biology": ["biology", "gene", "dna", "protein", "cell"],
            "physics": ["physics", "quantum", "particle", "relativity"],
            "science": ["science", "research", "experiment", "study"],
            "business": ["business", "market", "economy", "finance"]
        }
        
        scores = {}
        for category, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score
        
        return max(scores, key=scores.get) if scores else "general"
    
    def _extract_tags(self, text: str, max_tags: int = 5) -> List[str]:
        """Extract tags from text"""
        # Simple keyword extraction
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        words = text.lower().split()
        
        word_freq = {}
        for word in words:
            word = word.strip(".,!?;:()[]{}\"'")
            if len(word) > 3 and word not in stop_words:
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
