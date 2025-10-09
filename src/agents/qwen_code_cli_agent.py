"""
Qwen Code CLI Agent
Python wrapper for qwen-code CLI tool with autonomous agent capabilities
"""

import asyncio
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from config.agent_prompts import (
    CATEGORY_KEYWORDS,
    CONTENT_PROCESSING_PROMPT_TEMPLATE,
    DEFAULT_CATEGORY,
    MAX_SUMMARY_LENGTH,
    MAX_TAG_COUNT,
    MAX_TITLE_LENGTH,
    MIN_KEYWORD_LENGTH,
    QWEN_CODE_CLI_AGENT_INSTRUCTION,
    STOP_WORDS,
    URLS_SECTION_TEMPLATE,
)

from .base_agent import BaseAgent, KBStructure


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
        timeout: int = 300,  # 5 minutes default timeout
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

        # Get working directory - handle case where cwd doesn't exist
        if working_directory:
            self.working_directory = working_directory
        else:
            try:
                self.working_directory = os.getcwd()
            except (FileNotFoundError, OSError):
                # Fallback to a default location if cwd doesn't exist
                self.working_directory = str(Path.home())

        self.timeout = timeout

        # Tool settings
        self.enable_web_search = enable_web_search
        self.enable_git = enable_git
        self.enable_github = enable_github

        # MCP support via qwen CLI native mechanism
        # Qwen CLI has built-in MCP client and can connect to MCP servers
        # via .qwen/settings.json configuration (not via Python DynamicMCPTool)
        # See: https://github.com/QwenLM/qwen-code/blob/main/docs/cli/configuration.md
        self.enable_mcp = config.get("enable_mcp", False) if config else False
        self.enable_mcp_memory = config.get("enable_mcp_memory", False) if config else False
        self.user_id = config.get("user_id") if config else None
        self._mcp_tools_description: Optional[str] = None

        # Setup MCP configuration if enabled
        if self.enable_mcp or self.enable_mcp_memory:
            logger.info(
                "[QwenCodeCLIAgent] MCP enabled. Qwen CLI uses its own MCP client. "
                "Generating .qwen/settings.json configuration..."
            )
            self._setup_qwen_mcp_config()

        # Check if qwen CLI is available
        self._check_cli_available()

        logger.info(f"QwenCodeCLIAgent initialized")
        logger.info(f"Working directory: {self.working_directory}")
        logger.info(f"CLI path: {self.qwen_cli_path}")

    def _setup_qwen_mcp_config(self) -> None:
        """
        Setup qwen CLI MCP configuration

        Generates .qwen/settings.json with our MCP servers configuration.
        This allows qwen CLI to connect to our MCP servers.

        Note: Uses HTTP/SSE transport by default (use_http=True).
        For STDIO mode, pass use_http=False to setup_qwen_mcp_config().
        """
        try:
            from .mcp.qwen_config_generator import setup_qwen_mcp_config

            # Determine where to save config
            kb_path = Path(self.working_directory) if self.working_directory else None

            # Generate and save configuration (HTTP/SSE mode by default)
            saved_paths = setup_qwen_mcp_config(
                user_id=self.user_id,
                kb_path=kb_path,
                global_config=True,  # Always save to global ~/.qwen/settings.json
            )

            logger.info(f"[QwenCodeCLIAgent] MCP configuration saved to: {saved_paths}")
            logger.info(
                "[QwenCodeCLIAgent] MCP servers configured: mem-agent (memory storage/retrieval) [HTTP/SSE mode]"
            )

        except Exception as e:
            logger.error(f"[QwenCodeCLIAgent] Failed to setup MCP config: {e}", exc_info=True)
            logger.warning(
                "[QwenCodeCLIAgent] MCP may not work properly. "
                "You can manually configure .qwen/settings.json"
            )

    def _check_cli_available(self) -> None:
        """
        Check if qwen CLI is available and properly configured

        Raises:
            RuntimeError: If qwen CLI is not found or not working
        """
        logger.debug(f"[QwenCodeCLIAgent._check_cli_available] Checking qwen CLI availability...")
        logger.debug(f"[QwenCodeCLIAgent._check_cli_available] CLI path: {self.qwen_cli_path}")

        try:
            cmd = [self.qwen_cli_path, "--version"]
            logger.debug(
                f"[QwenCodeCLIAgent._check_cli_available] Running command: {' '.join(cmd)}"
            )

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            logger.debug(
                f"[QwenCodeCLIAgent._check_cli_available] Return code: {result.returncode}"
            )
            logger.debug(f"[QwenCodeCLIAgent._check_cli_available] STDOUT: {result.stdout.strip()}")
            logger.debug(f"[QwenCodeCLIAgent._check_cli_available] STDERR: {result.stderr.strip()}")

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
        logger.debug(
            f"[QwenCodeCLIAgent] Starting process with content keys: {list(content.keys())}"
        )

        if not self.validate_input(content):
            logger.error(f"[QwenCodeCLIAgent] Invalid input content: {content}")
            raise ValueError("Invalid input content: must be a dict with 'text' key")

        logger.info(
            "[QwenCodeCLIAgent] Starting autonomous content processing with qwen-code CLI..."
        )
        logger.debug(f"[QwenCodeCLIAgent] Content preview: {content.get('text', '')[:100]}...")

        try:
            # Step 1: Prepare prompt for qwen-code (with MCP tools info)
            logger.debug("[QwenCodeCLIAgent] STEP 1: Preparing prompt for qwen-code")
            prompt = await self._prepare_prompt_async(content)
            logger.debug(f"[QwenCodeCLIAgent] Prepared prompt length: {len(prompt)} characters")

            # Step 2: Execute qwen-code CLI
            logger.debug("[QwenCodeCLIAgent] STEP 2: Executing qwen-code CLI")
            result_text = await self._execute_qwen_cli(prompt)
            logger.debug(
                f"[QwenCodeCLIAgent] Received result length: {len(result_text)} characters"
            )

            # Step 3: Parse agent response using BaseAgent method
            logger.debug("[QwenCodeCLIAgent] STEP 3: Parsing agent response with standard parser")
            logger.debug(
                f"[QwenCodeCLIAgent] Result text preview (first 500 chars): {result_text[:500]}"
            )
            logger.debug(
                f"[QwenCodeCLIAgent] Result text preview (last 500 chars): {result_text[-500:]}"
            )

            try:
                agent_result = self.parse_agent_response(result_text)
                logger.info(f"[QwenCodeCLIAgent] Parsed result: {agent_result.summary}")
                logger.debug(f"[QwenCodeCLIAgent] Files created: {agent_result.files_created}")
                logger.debug(f"[QwenCodeCLIAgent] Folders created: {agent_result.folders_created}")
            except Exception as parse_error:
                logger.error(
                    f"[QwenCodeCLIAgent] Failed to parse agent response: {parse_error}",
                    exc_info=True,
                )
                logger.debug(f"[QwenCodeCLIAgent] Full response text: {result_text}")
                raise

            # Step 4: Extract KB structure from response
            logger.debug("[QwenCodeCLIAgent] STEP 4: Extracting KB structure from response")
            kb_structure = self.extract_kb_structure_from_response(
                result_text, default_category="general"
            )
            logger.info(f"[QwenCodeCLIAgent] KB structure: {kb_structure.to_dict()}")

            # Step 5: Extract title from markdown
            logger.debug("[QwenCodeCLIAgent] STEP 5: Extracting title from markdown")
            title = self._extract_title_from_markdown(agent_result.markdown)

            # Step 6: Extract TODO plan from markdown
            todo_plan = self._extract_todo_plan(result_text)
            
            # Step 7: Build final metadata
            metadata = {
                "processed_at": datetime.now().isoformat(),
                "agent": "QwenCodeCLIAgent",
                "version": "2.0.0",
                "instruction_used": bool(self.instruction != self.DEFAULT_INSTRUCTION),
                "tools_enabled": {
                    "web_search": self.enable_web_search,
                    "git": self.enable_git,
                    "github": self.enable_github,
                },
                # Добавляем информацию о файлах из AgentResult
                "files_created": agent_result.files_created,
                "files_edited": agent_result.files_edited,
                "folders_created": agent_result.folders_created,
                "todo_plan": todo_plan,  # Add extracted TODO plan
                **agent_result.metadata,  # Добавляем метаданные из ответа агента
            }

            # Validate we have content
            if not agent_result.markdown.strip():
                logger.error("No markdown content generated")
                raise ValueError("Processing failed: no markdown content generated")

            result = {
                "markdown": agent_result.markdown,
                "metadata": metadata,
                "title": title,
                "kb_structure": kb_structure,
                "answer": agent_result.answer,  # Include answer for ask mode
            }

            logger.info(f"[QwenCodeCLIAgent] Successfully processed content: title='{title}'")
            logger.info(f"[QwenCodeCLIAgent] Summary: {agent_result.summary}")
            logger.debug(f"[QwenCodeCLIAgent] Markdown preview: {agent_result.markdown[:200]}...")
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

    async def get_mcp_tools_description(self) -> str:
        """
        Get description of available MCP tools

        Returns:
            Formatted description of MCP tools for use in prompts
        """
        # Return cached description if available
        if self._mcp_tools_description is not None:
            return self._mcp_tools_description

        # Only generate if MCP is enabled
        if not (self.enable_mcp or self.enable_mcp_memory):
            self._mcp_tools_description = ""
            return ""

        try:
            from .mcp import format_mcp_tools_for_prompt, get_mcp_tools_description

            # Get tools description
            tools_desc = await get_mcp_tools_description(user_id=self.user_id)

            # Format for user prompt (qwen CLI will receive this in input)
            formatted = format_mcp_tools_for_prompt(tools_desc, include_in_system=False)

            # Cache the result
            self._mcp_tools_description = formatted

            if formatted:
                logger.info(
                    f"[QwenCodeCLIAgent] MCP tools description generated ({len(formatted)} chars)"
                )

            return formatted

        except Exception as e:
            logger.error(f"[QwenCodeCLIAgent] Failed to get MCP tools description: {e}")
            self._mcp_tools_description = ""
            return ""

    async def _prepare_prompt_async(self, content: Dict) -> str:
        """
        Prepare prompt for qwen-code CLI using template from config (async version)

        Args:
            content: Content dictionary

        Returns:
            Formatted prompt string
        """
        # If content already has a pre-built prompt (e.g., from /ask mode), use it directly
        if "prompt" in content:
            base_prompt = content["prompt"]
        else:
            text = content.get("text", "")
            urls = content.get("urls", [])

            # Build URLs section if URLs present
            urls_section = ""
            if urls:
                url_list = "\n".join([f"- {url}" for url in urls])
                urls_section = URLS_SECTION_TEMPLATE.format(url_list=url_list)

            # Use template from config
            base_prompt = CONTENT_PROCESSING_PROMPT_TEMPLATE.format(
                instruction=self.instruction, text=text, urls_section=urls_section
            )

        # Add MCP tools description if available
        mcp_description = await self.get_mcp_tools_description()
        if mcp_description:
            return f"{base_prompt}{mcp_description}"

        return base_prompt

    def _prepare_prompt(self, content: Dict) -> str:
        """
        Prepare prompt for qwen-code CLI using template from config

        Args:
            content: Content dictionary

        Returns:
            Formatted prompt string
        """
        # If content already has a pre-built prompt (e.g., from /ask mode), use it directly
        if "prompt" in content:
            return content["prompt"]

        text = content.get("text", "")
        urls = content.get("urls", [])

        # Build URLs section if URLs present
        urls_section = ""
        if urls:
            url_list = "\n".join([f"- {url}" for url in urls])
            urls_section = URLS_SECTION_TEMPLATE.format(url_list=url_list)

        # Use template from config
        return CONTENT_PROCESSING_PROMPT_TEMPLATE.format(
            instruction=self.instruction, text=text, urls_section=urls_section
        )

    async def _execute_qwen_cli(self, prompt: str) -> str:
        """
        Execute qwen-code CLI with the given prompt

        Args:
            prompt: Prompt to send to qwen-code

        Returns:
            CLI output as string
        """
        import time

        logger.info("[QwenCodeCLIAgent._execute_qwen_cli] Executing qwen-code CLI...")
        logger.debug(
            f"[QwenCodeCLIAgent._execute_qwen_cli] Working directory: {self.working_directory}"
        )
        logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] Timeout: {self.timeout}s")

        # Create temporary file for prompt
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp_file:
            tmp_file.write(prompt)
            tmp_file_path = tmp_file.name

        logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] Temp file created: {tmp_file_path}")

        try:
            # Prepare environment
            env = os.environ.copy()

            # Log relevant environment variables (without sensitive data)
            logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] Environment variables:")
            for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "PATH"]:
                if key in env:
                    value = env[key]
                    if "KEY" in key or "TOKEN" in key:
                        # Mask sensitive values
                        value = value[:8] + "..." if len(value) > 8 else "***"
                    logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli]   {key}={value}")

            # Build command
            # Use non-interactive mode and pass prompt via stdin
            cmd = [self.qwen_cli_path]

            # Log command details
            logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === CLI EXECUTION TRACE START ===")
            logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] Command: {' '.join(cmd)}")
            logger.debug(
                f"[QwenCodeCLIAgent._execute_qwen_cli] Working dir: {self.working_directory}"
            )

            # Read prompt from file
            with open(tmp_file_path, "r", encoding="utf-8") as f:
                prompt_text = f.read()

            # Log prompt details (full in DEBUG mode)
            logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === STDIN (PROMPT) ===")
            logger.debug(
                f"[QwenCodeCLIAgent._execute_qwen_cli] Prompt length: {len(prompt_text)} characters"
            )
            logger.debug(
                f"[QwenCodeCLIAgent._execute_qwen_cli] Prompt preview (first 500 chars):\n{prompt_text[:500]}"
            )
            if len(prompt_text) > 500:
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] Prompt preview (last 200 chars):\n{prompt_text[-200:]}"
                )
            logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === FULL PROMPT ===")
            logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli]\n{prompt_text}")
            logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === END FULL PROMPT ===")

            # Execute qwen CLI in non-interactive mode
            # We'll use subprocess with input to send the prompt
            start_time = time.time()
            logger.debug(
                f"[QwenCodeCLIAgent._execute_qwen_cli] Starting subprocess at {start_time}"
            )

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory,
                env=env,
            )

            logger.debug(
                f"[QwenCodeCLIAgent._execute_qwen_cli] Process created with PID: {process.pid}"
            )

            try:
                # Send prompt and get response
                logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] Sending prompt to stdin...")
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt_text.encode("utf-8")), timeout=self.timeout
                )

                execution_time = time.time() - start_time
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] Process completed in {execution_time:.2f}s"
                )
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] Process return code: {process.returncode}"
                )

                # Log stderr output
                stderr_text = stderr.decode().strip()
                if stderr_text:
                    logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === STDERR OUTPUT ===")
                    logger.debug(
                        f"[QwenCodeCLIAgent._execute_qwen_cli] STDERR length: {len(stderr_text)} characters"
                    )
                    logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli]\n{stderr_text}")
                    logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === END STDERR OUTPUT ===")
                else:
                    logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] STDERR is empty")

                # Decode stdout
                result = stdout.decode("utf-8").strip()

                # Log stdout output
                logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === STDOUT OUTPUT ===")
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] STDOUT length: {len(result)} characters"
                )
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] STDOUT preview (first 500 chars):\n{result[:500]}"
                )
                if len(result) > 500:
                    logger.debug(
                        f"[QwenCodeCLIAgent._execute_qwen_cli] STDOUT preview (last 200 chars):\n{result[-200:]}"
                    )
                logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === FULL STDOUT ===")
                logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli]\n{result}")
                logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] === END FULL STDOUT ===")

                # Check for errors
                if process.returncode != 0:
                    error_msg = stderr_text
                    logger.warning(
                        f"[QwenCodeCLIAgent._execute_qwen_cli] Qwen CLI returned non-zero exit code {process.returncode}"
                    )
                    logger.warning(
                        f"[QwenCodeCLIAgent._execute_qwen_cli] Qwen CLI stderr: {error_msg}"
                    )

                    # If we have an error message, include it in the result for debugging
                    if error_msg and not result:
                        logger.error(f"Qwen CLI failed with: {error_msg}")
                        raise RuntimeError(f"Qwen CLI execution failed: {error_msg}")

                if not result:
                    logger.warning(
                        "[QwenCodeCLIAgent._execute_qwen_cli] Empty result from qwen CLI, using fallback processing"
                    )
                    # Fallback to simple processing
                    try:
                        result = self._fallback_processing(prompt)
                    except Exception as fallback_error:
                        logger.error(f"Fallback processing also failed: {fallback_error}")
                        raise RuntimeError(
                            f"Both qwen CLI and fallback processing failed. "
                            f"CLI error: empty result, Fallback error: {fallback_error}"
                        )

                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] === CLI EXECUTION TRACE END ==="
                )
                return result

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time = time.time() - start_time
                logger.error(
                    f"Qwen CLI timeout after {execution_time:.2f}s (limit: {self.timeout}s)"
                )
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] === CLI EXECUTION TRACE END (TIMEOUT) ==="
                )
                raise TimeoutError(f"Qwen CLI execution timeout after {self.timeout}s")

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] Temp file deleted: {tmp_file_path}"
                )
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
        title = BaseAgent.generate_title(text)
        category = BaseAgent.detect_category(text)
        tags = BaseAgent.extract_keywords(text, top_n=5)

        markdown = f"""# {title}

## Metadata

- **Category**: {category}
- **Tags**: {', '.join(tags)}
- **Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Content

{text}

## Summary

{BaseAgent.generate_summary(text)}
"""
        return markdown

    def _extract_title_from_markdown(self, markdown: str) -> str:
        """Extract title from markdown (first # heading)"""
        lines = markdown.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                if len(title) > MAX_TITLE_LENGTH:
                    return title[:MAX_TITLE_LENGTH] + "..."
                return title

        # Fallback: first non-empty line
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 10:
                if len(line) > MAX_TITLE_LENGTH:
                    return line[:MAX_TITLE_LENGTH] + "..."
                return line

        return "Untitled Note"
    
    def _extract_todo_plan(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Extract TODO plan from markdown
        
        Looks for ## TODO Plan section and extracts tasks in format:
        - [x] Completed task
        - [ ] Pending task
        
        Args:
            markdown: Markdown content
            
        Returns:
            List of task dictionaries with 'task' and 'status' keys
        """
        tasks = []
        lines = markdown.split("\n")
        in_todo_section = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if we're entering TODO Plan section
            if line_stripped.startswith("## TODO Plan"):
                in_todo_section = True
                continue
            
            # Check if we're leaving TODO Plan section (new section starts)
            if in_todo_section and line_stripped.startswith("#"):
                break
            
            # Extract task if in TODO section
            if in_todo_section and line_stripped.startswith("-"):
                # Extract status and task text
                if "[x]" in line_stripped or "[X]" in line_stripped:
                    status = "completed"
                    task_text = line_stripped.replace("- [x]", "").replace("- [X]", "").strip()
                elif "[ ]" in line_stripped:
                    status = "pending"
                    task_text = line_stripped.replace("- [ ]", "").strip()
                else:
                    # Plain list item without checkbox
                    status = "unknown"
                    task_text = line_stripped[1:].strip()
                
                if task_text:
                    tasks.append({
                        "task": task_text,
                        "status": status
                    })
        
        return tasks
    
    # Backward compatibility methods for tests
    def _extract_title(self, text: str, max_length: int = MAX_TITLE_LENGTH) -> str:
        """Extract title from text (backward compatibility)"""
        return BaseAgent.generate_title(text, max_length=max_length)
    
    def _detect_category(self, text: str) -> str:
        """Detect category from text (backward compatibility)"""
        return BaseAgent.detect_category(text)
    
    def _extract_tags(self, text: str, max_tags: int = MAX_TAG_COUNT) -> List[str]:
        """Extract tags from text (backward compatibility)"""
        return BaseAgent.extract_keywords(text, top_n=max_tags)
    
    def _generate_summary(self, text: str, max_length: int = MAX_SUMMARY_LENGTH) -> str:
        """Generate summary from text (backward compatibility)"""
        return BaseAgent.generate_summary(text, max_length=max_length)
    
    def _parse_qwen_result(self, result_text: str) -> Dict[str, Any]:
        """Parse qwen CLI result (backward compatibility)"""
        # Parse using the standard BaseAgent parser
        agent_result = self.parse_agent_response(result_text)
        
        # Extract KB structure
        kb_structure = self.extract_kb_structure_from_response(result_text, default_category="general")
        
        # Build result dict compatible with old format
        return {
            "title": self._extract_title_from_markdown(agent_result.markdown),
            "category": kb_structure.category,
            "subcategory": kb_structure.subcategory,
            "tags": kb_structure.tags,
            "todo_plan": agent_result.metadata.get("todo_plan", []),
            "markdown": agent_result.markdown,
        }

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

    def set_working_directory(self, working_directory: str) -> None:
        """
        Update working directory for qwen CLI execution

        Args:
            working_directory: Path to working directory
        """
        self.working_directory = working_directory
        logger.info(f"Working directory updated to: {self.working_directory}")

    def get_working_directory(self) -> str:
        """Get current working directory"""
        return self.working_directory

    @staticmethod
    def check_installation() -> bool:
        """
        Check if qwen-code CLI is installed

        Returns:
            True if installed, False otherwise
        """
        try:
            result = subprocess.run(
                ["qwen", "--version"], capture_output=True, text=True, timeout=10
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
