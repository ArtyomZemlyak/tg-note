"""
Qwen Code CLI Agent
Python wrapper for qwen-code CLI tool with autonomous agent capabilities

This agent uses the promptic library for prompt management.
All prompts are loaded via promptic.render() with version support:

    from promptic import render
    prompt = render("config/prompts/content_processing", version="latest")
"""

import asyncio
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger
from promptic import render

from config.constants import MAX_TITLE_LENGTH

from .base_agent import BaseAgent


class QwenCodeCLIAgent(BaseAgent):
    """
    Agent that uses qwen-code CLI for autonomous processing

    Features:
    - Direct integration with qwen-code CLI
    - Autonomous mode (no user interaction)
    - TODO plan generation via qwen-code
    - Built-in tool support (web search, git, github, shell commands)
    - Configurable instruction system
    - Unified prompt management via promptic service

    AICODE-NOTE: All prompts are now obtained via the promptic service
    using a single render() call with version and variable support.
    """

    # Default instruction is loaded on first access (class-level property)
    # AICODE-NOTE: Using a cached property-like approach to avoid loading at import time
    _default_instruction_cache = None

    @classmethod
    def get_default_instruction(cls) -> str:
        """Get the default instruction (cached)."""
        if cls._default_instruction_cache is None:
            prompts_dir = Path(__file__).parent.parent.parent / "config" / "prompts"

            # Get media instruction
            media_instr = render(str(prompts_dir / "media"), version="latest")

            # Get response formatter prompt
            from src.bot.response_formatter import ResponseFormatter

            response_formatter = ResponseFormatter()
            response_format_json = response_formatter.generate_prompt_text()
            response_formatter_prompt = render(
                str(prompts_dir / "response_formatter"), version="latest"
            )
            response_formatter_prompt = response_formatter_prompt.replace(
                "{response_format}", response_format_json
            )

            # Get qwen code cli instruction
            instruction = render(str(prompts_dir / "qwen_code_cli"), version="latest")
            instruction = instruction.replace("{instruction_media}", media_instr)
            instruction = instruction.replace("{response_format}", response_formatter_prompt)
            cls._default_instruction_cache = instruction
        return cls._default_instruction_cache

    @property
    def DEFAULT_INSTRUCTION(self) -> str:
        """Property for backward compatibility with code that accesses DEFAULT_INSTRUCTION."""
        return self.get_default_instruction()

    def __init__(
        self,
        config: Optional[Dict] = None,
        instruction: Optional[str] = None,
        qwen_cli_path: str = "qwen",
        working_directory: Optional[str] = None,
        enable_web_search: bool = True,
        enable_git: bool = True,
        enable_github: bool = True,
        timeout: int = 999999,  # Default timeout in seconds (~11.5 days)
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

        # AICODE-NOTE: Get the complete agent instruction using promptic service
        # This renders the instruction with all components (media instruction, response formatter)
        # in a single call using file-first architecture and versioning
        self.instruction = instruction or self.get_default_instruction()
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

        Docker mode: Config is generated by MCP Hub on startup (bot is pure client).
        Standalone mode: Generates .qwen/settings.json with our MCP servers configuration.

        Note: Uses HTTP/SSE transport by default (use_http=True).
        For STDIO mode, pass use_http=False to setup_qwen_mcp_config().
        """
        # AICODE-NOTE: In Docker mode, config is generated by MCP Hub service
        # Bot container should NOT generate configs - it's a pure client
        mcp_hub_url = os.getenv("MCP_HUB_URL")

        if mcp_hub_url:
            logger.info(
                f"[QwenCodeCLIAgent] Docker mode detected (MCP_HUB_URL={mcp_hub_url}). "
                f"MCP configuration is managed by MCP Hub service. "
                f"Bot is a pure client - skipping config generation."
            )
            # Config should already be available from MCP Hub
            # If not, user needs to ensure MCP Hub is running and generating configs
            return

        # Standalone mode - generate config locally
        try:
            from src.mcp.qwen_config_generator import setup_qwen_mcp_config

            # Generate and save configuration to global ~/.qwen/settings.json (HTTP/SSE mode by default)
            saved_path = setup_qwen_mcp_config(
                user_id=self.user_id,
            )

            logger.info(f"[QwenCodeCLIAgent] MCP configuration saved to: {saved_path}")
            logger.info(
                "[QwenCodeCLIAgent] MCP servers configured: memory (memory storage/retrieval) [HTTP/SSE mode]"
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
        # Check if log_callback is in content
        has_log_callback = "log_callback" in content
        log_callback_value = content.get("log_callback")
        logger.info(
            f"[QwenCodeCLIAgent] Content check: has_log_callback={has_log_callback}, "
            f"log_callback is None={log_callback_value is None}, "
            f"log_callback type={type(log_callback_value).__name__ if log_callback_value else 'None'}"
        )

        if not self.validate_input(content):
            logger.error(f"[QwenCodeCLIAgent] Invalid input content: {content}")
            raise ValueError("Invalid input content: must be a dict with 'text' key")

        logger.info(
            "[QwenCodeCLIAgent] Starting autonomous content processing with qwen-code CLI..."
        )
        logger.debug(f"[QwenCodeCLIAgent] Content preview: {content.get('text', '')[:50]}...")

        try:
            # Step 1: Prepare prompt for qwen-code (with MCP tools info)
            logger.debug("[QwenCodeCLIAgent] STEP 1: Preparing prompt for qwen-code")
            prompt = await self._prepare_prompt_async(content)
            logger.debug(f"[QwenCodeCLIAgent] Prepared prompt length: {len(prompt)} characters")

            # Step 2: Execute qwen-code CLI
            logger.debug("[QwenCodeCLIAgent] STEP 2: Executing qwen-code CLI")
            # Extract log_callback, error_callback and related parameters from content if provided
            log_callback = content.get("log_callback")
            error_callback = content.get("error_callback")
            log_chars = content.get("log_chars", 1000)
            update_interval = content.get("log_update_interval", 30.0)

            logger.info(
                f"[QwenCodeCLIAgent] Before _execute_qwen_cli: "
                f"log_callback={log_callback is not None}, "
                f"log_callback type={type(log_callback).__name__ if log_callback else 'None'}, "
                f"log_chars={log_chars}, update_interval={update_interval}"
            )

            if log_callback:
                logger.info(
                    f"[QwenCodeCLIAgent] log_callback provided: log_chars={log_chars}, "
                    f"update_interval={update_interval}s"
                )
            else:
                logger.warning("[QwenCodeCLIAgent] No log_callback provided, using standard mode")

            error_callback = content.get("error_callback")
            result_text = await self._execute_qwen_cli(
                prompt,
                log_callback=log_callback,
                log_chars=log_chars,
                update_interval=update_interval,
                error_callback=error_callback,
            )
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

            # Parse response using ResponseFormatter
            from src.bot.response_formatter import ResponseFormatter

            formatter = ResponseFormatter()
            parsed_result = formatter.parse(result_text)

            # Convert to markdown using ResponseFormatter
            markdown_result = formatter.to_html(parsed_result)

            logger.info(f"[QwenCodeCLIAgent] Parsed result: {parsed_result.get('summary', '')}")
            logger.debug(
                f"[QwenCodeCLIAgent] Files created: {parsed_result.get('files_created', [])}"
            )
            logger.debug(
                f"[QwenCodeCLIAgent] Folders created: {parsed_result.get('folders_created', [])}"
            )

            # Step 4: Extract KB structure from response
            logger.debug("[QwenCodeCLIAgent] STEP 4: Extracting KB structure from response")
            kb_structure = self.extract_kb_structure_from_response(
                result_text, default_category="general"
            )
            logger.info(f"[QwenCodeCLIAgent] KB structure: {kb_structure.to_dict()}")

            # Step 5: Extract title from markdown
            logger.debug("[QwenCodeCLIAgent] STEP 5: Extracting title from markdown")
            # TODO: Properly handle title
            if "summary" in parsed_result:
                title = parsed_result["summary"]
            else:
                title = markdown_result[:50]

            # Step 6: Extract TODO plan from markdown
            todo_plan = self._extract_todo_plan(result_text)

            # Step 7: Build final metadata
            # Составляется только из известных значений, из parsed_result ничего не вытаскивается
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
                "todo_plan": todo_plan,  # Add extracted TODO plan
            }

            # Validate we have content
            if not markdown_result.strip():
                logger.error("No markdown content generated")
                raise ValueError("Processing failed: no markdown content generated")

            result = {
                "markdown": markdown_result,
                "parsed_result": parsed_result,
                "metadata": metadata,
                "title": title,
                "kb_structure": kb_structure,
            }

            logger.info(f"[QwenCodeCLIAgent] Successfully processed content: title='{title}'")
            logger.info(f"[QwenCodeCLIAgent] Summary: {parsed_result.get('summary', '')}")
            logger.debug(f"[QwenCodeCLIAgent] Markdown preview: {markdown_result[:50]}...")
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

    async def _prepare_prompt_async(self, content: Dict) -> str:
        """
        Get pre-built prompt from content dictionary.

        AICODE-NOTE: This method expects the prompt to be already built by the service layer
        (note_creation_service, question_answering_service, or agent_task_service).
        Services are responsible for:
        1. Rendering prompts with all variables using PromptService.render_prompt()
        2. Prompts are automatically exported to data/prompts/ during rendering (with export_to)
        3. Passing complete prompt via content["prompt"]

        The agent receives the main prompt string via stdin, and can read additional
        exported files from data/prompts/ using @ref() links preserved in file_first mode.

        Args:
            content: Content dictionary with pre-built "prompt" field

        Returns:
            Pre-built prompt string

        Raises:
            ValueError: If prompt is missing (services must provide it)
        """
        # Services must provide ready prompt
        if "prompt" not in content:
            raise ValueError(
                "Missing 'prompt' in content. Services must build complete prompt "
                "before passing to agent."
            )

        return content["prompt"]

    def _prepare_prompt(self, content: Dict) -> str:
        """
        Get pre-built prompt from content dictionary (sync version for tests).

        AICODE-NOTE: Mirrors async variant - expects prompt from services.

        Args:
            content: Content dictionary with pre-built "prompt" field

        Returns:
            Pre-built prompt string

        Raises:
            ValueError: If prompt is missing
        """
        if "prompt" not in content:
            raise ValueError(
                "Missing 'prompt' in content. Services must build complete prompt "
                "before passing to agent."
            )

        return content["prompt"]

    async def _execute_qwen_cli(
        self,
        prompt: str,
        log_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        log_chars: int = 1000,
        update_interval: float = 30.0,
        error_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        """
        Execute qwen-code CLI with the given prompt

        Supports two modes:
        1. Standard mode (log_callback=None): Uses process.communicate() for blocking execution
        2. Streaming mode (log_callback provided): Streams stdout/stderr and calls callback periodically

        Args:
            prompt: Prompt to send to qwen-code
            log_callback: Optional async callback function to receive log snippets (last N chars)
            log_chars: Number of characters to send in each log update (default: 1000)
            update_interval: Interval in seconds between log updates (default: 30.0)

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
            # AICODE-NOTE: Disable buffering for stdout/stderr to enable real-time streaming
            env["PYTHONUNBUFFERED"] = "1"
            # For Node.js processes (qwen-code-cli), set NODE_NO_WARNINGS to avoid noise
            if "NODE_NO_WARNINGS" not in env:
                env["NODE_NO_WARNINGS"] = "1"

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

            # AICODE-NOTE: Add --include-directories to allow access to ../media and data/prompts
            # when KB_TOPICS_ONLY=true restricts agent to topics/ folder
            # This allows agent to read media metadata files and prompt files without changing working directory
            additional_dirs = []

            media_dir = Path(self.working_directory).parent / "media"
            if media_dir.exists():
                additional_dirs.append(str(media_dir.absolute()))
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] Added media directory: {media_dir}"
                )

            # Add data/prompts directory for exported prompts (use absolute path)
            # Resolve from project root (3 levels up from src/agents/)
            project_root = Path(__file__).parent.parent.parent
            prompts_dir = project_root / "data" / "prompts"
            if prompts_dir.exists():
                prompts_abs = prompts_dir.absolute()
                additional_dirs.append(str(prompts_abs))
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] Added prompts directory: {prompts_abs}"
                )
            else:
                logger.warning(
                    f"[QwenCodeCLIAgent._execute_qwen_cli] Prompts directory not found: {prompts_dir}"
                )

            if additional_dirs:
                cmd.extend(["--include-directories", ",".join(additional_dirs)])

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
                # Choose execution mode based on log_callback
                if log_callback is not None:
                    # Streaming mode: read stdout/stderr asynchronously and call callback periodically
                    logger.info(
                        f"[QwenCodeCLIAgent._execute_qwen_cli] Using streaming mode with log_callback "
                        f"(log_chars={log_chars}, update_interval={update_interval}s)"
                    )
                    result = await self._execute_with_streaming(
                        process,
                        prompt_text,
                        start_time,
                        log_callback,
                        log_chars,
                        update_interval,
                        error_callback=error_callback,
                    )
                else:
                    # Standard mode: use communicate() for blocking execution
                    logger.debug(
                        f"[QwenCodeCLIAgent._execute_qwen_cli] Using standard mode (no streaming)"
                    )
                    # Send prompt and get response
                    logger.debug(f"[QwenCodeCLIAgent._execute_qwen_cli] Sending prompt to stdin...")
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input=prompt_text.encode("utf-8")), timeout=self.timeout
                    )
                    result = self._process_stdout_stderr(
                        stdout, stderr, process, prompt, start_time
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

    def _process_stdout_stderr(
        self,
        stdout: bytes,
        stderr: bytes,
        process: asyncio.subprocess.Process,
        prompt: str,
        start_time: Optional[float] = None,
    ) -> str:
        """
        Process stdout and stderr from subprocess execution.

        Args:
            stdout: Standard output bytes
            stderr: Standard error bytes
            process: Subprocess process object
            prompt: Original prompt (for fallback processing)
            start_time: Optional start time for execution time calculation

        Returns:
            Processed result string

        Raises:
            RuntimeError: If process failed or result is empty
        """
        if start_time is not None:
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
            logger.warning(f"[QwenCodeCLIAgent._execute_qwen_cli] Qwen CLI stderr: {error_msg}")

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

        return result

    async def _execute_with_streaming(
        self,
        process: asyncio.subprocess.Process,
        prompt_text: str,
        start_time: float,
        log_callback: Callable[[str], Awaitable[None]],
        log_chars: int = 1000,
        update_interval: float = 30.0,
        error_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        """
        Execute subprocess with streaming stdout/stderr and periodic log updates.

        Args:
            process: Subprocess process object
            prompt_text: Prompt text to send to stdin
            start_time: Start time for execution tracking
            log_callback: Async callback function to receive log snippets
            log_chars: Number of characters to send in each update
            update_interval: Interval in seconds between updates
            error_callback: Optional async callback function to receive error messages

        Returns:
            Combined stdout and stderr output as string

        Raises:
            TimeoutError: If process exceeds timeout
        """
        stdout_buffer = []
        stderr_buffer = []

        async def read_stream(stream, buffer, stream_name):
            """Read from stream and append to buffer."""
            try:
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_with_streaming] Starting to read {stream_name}"
                )
                chunk_count = 0
                while True:
                    chunk = await stream.read(4096)
                    if not chunk:
                        logger.debug(
                            f"[QwenCodeCLIAgent._execute_with_streaming] {stream_name} closed (read {chunk_count} chunks)"
                        )
                        break
                    chunk_count += 1
                    decoded = chunk.decode("utf-8", errors="replace")
                    buffer.append(decoded)
                    # AICODE-NOTE: Removed per-chunk logging to reduce log spam
            except Exception as e:
                error_msg = f"Error reading {stream_name}: {e}"
                logger.warning(error_msg, exc_info=True)
                # Send error to error_callback if available
                if error_callback:
                    try:
                        await error_callback(error_msg)
                    except Exception as callback_error:
                        logger.warning(f"Error in error_callback: {callback_error}")

        async def periodic_log_updates():
            """Periodically send log updates via callback."""
            try:
                update_count = 0
                last_stderr_sent = [""]  # Track last sent stderr to avoid duplicates
                while True:
                    await asyncio.sleep(update_interval)
                    update_count += 1

                    # Separate stdout (logs) and stderr (errors)
                    stdout_text = "".join(stdout_buffer)
                    stderr_text = "".join(stderr_buffer)
                    stdout_len = len(stdout_text)
                    stderr_len = len(stderr_text)

                    logger.debug(
                        f"[QwenCodeCLIAgent._execute_with_streaming] Log update #{update_count}: "
                        f"stdout={stdout_len} chars, stderr={stderr_len} chars"
                    )

                    # Send stdout to log_callback (only stdout, not stderr)
                    if stdout_text:
                        # Get last N characters from stdout only
                        log_snippet = (
                            stdout_text[-log_chars:]
                            if len(stdout_text) > log_chars
                            else stdout_text
                        )
                        logger.debug(
                            f"[QwenCodeCLIAgent._execute_with_streaming] Sending log snippet: {len(log_snippet)} chars"
                        )
                        try:
                            await log_callback(log_snippet)
                            logger.debug(
                                f"[QwenCodeCLIAgent._execute_with_streaming] Log callback executed successfully"
                            )
                        except Exception as e:
                            logger.warning(f"Error in log_callback: {e}", exc_info=True)

                    # Send stderr to error_callback (only if it changed)
                    if stderr_text and stderr_text != last_stderr_sent[0] and error_callback:
                        # Get new stderr content (what was added since last send)
                        new_stderr = stderr_text[len(last_stderr_sent[0]) :]
                        if new_stderr.strip():
                            logger.debug(
                                f"[QwenCodeCLIAgent._execute_with_streaming] Sending error snippet: {len(new_stderr)} chars"
                            )
                            try:
                                await error_callback(new_stderr)
                                last_stderr_sent[0] = stderr_text
                                logger.debug(
                                    f"[QwenCodeCLIAgent._execute_with_streaming] Error callback executed successfully"
                                )
                            except Exception as e:
                                logger.warning(f"Error in error_callback: {e}", exc_info=True)
                    elif not stdout_text and not stderr_text:
                        logger.debug(
                            f"[QwenCodeCLIAgent._execute_with_streaming] No logs to send yet (update #{update_count})"
                        )
            except asyncio.CancelledError:
                # Task was cancelled, this is expected
                logger.debug(
                    f"[QwenCodeCLIAgent._execute_with_streaming] Periodic log updates cancelled"
                )
                pass

        # Start reading streams and periodic updates
        tasks = []
        if process.stdout:
            logger.debug(f"[QwenCodeCLIAgent._execute_with_streaming] Creating stdout reader task")
            stdout_task = asyncio.create_task(read_stream(process.stdout, stdout_buffer, "stdout"))
            tasks.append(stdout_task)
        else:
            logger.warning(f"[QwenCodeCLIAgent._execute_with_streaming] process.stdout is None!")
        if process.stderr:
            logger.debug(f"[QwenCodeCLIAgent._execute_with_streaming] Creating stderr reader task")
            stderr_task = asyncio.create_task(read_stream(process.stderr, stderr_buffer, "stderr"))
            tasks.append(stderr_task)
        else:
            logger.warning(f"[QwenCodeCLIAgent._execute_with_streaming] process.stderr is None!")
        logger.debug(
            f"[QwenCodeCLIAgent._execute_with_streaming] Creating periodic log update task"
        )
        log_update_task = asyncio.create_task(periodic_log_updates())
        tasks.append(log_update_task)
        logger.info(
            f"[QwenCodeCLIAgent._execute_with_streaming] Started {len(tasks)} background tasks"
        )

        # Send initial test message to verify callback works
        try:
            logger.debug(
                "[QwenCodeCLIAgent._execute_with_streaming] Sending initial test log message"
            )
            await log_callback("Начинаю выполнение...")
        except Exception as e:
            logger.warning(f"Failed to send initial test log message: {e}")

        # Send prompt to stdin
        logger.debug(f"[QwenCodeCLIAgent._execute_with_streaming] Sending prompt to stdin...")
        if process.stdin:
            try:
                process.stdin.write(prompt_text.encode("utf-8"))
                await process.stdin.drain()
            finally:
                process.stdin.close()
                await process.stdin.wait_closed()

        try:
            # Wait for process to complete
            await asyncio.wait_for(process.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            execution_time = time.time() - start_time
            error_msg = f"Qwen CLI timeout after {execution_time:.2f}s (limit: {self.timeout}s)"
            logger.error(error_msg)
            # Send error to error_callback if available
            if error_callback:
                try:
                    await error_callback(error_msg)
                except Exception as callback_error:
                    logger.warning(f"Error in error_callback: {callback_error}")
            raise TimeoutError(f"Qwen CLI execution timeout after {self.timeout}s")
        finally:
            # Cancel and wait for all tasks
            for task in tasks:
                task.cancel()

            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"Error waiting for tasks: {e}")

        # Combine final output
        combined_output = "".join(stdout_buffer) + "".join(stderr_buffer)
        result = combined_output.strip()

        # Process result (check errors, fallback, etc.)
        # Create a mock stderr bytes for compatibility with _process_stdout_stderr
        stderr_bytes = "".join(stderr_buffer).encode("utf-8")
        stdout_bytes = "".join(stdout_buffer).encode("utf-8")

        # Check for process errors and send to error_callback if available
        # AICODE-NOTE: Send final stderr if process failed (stderr might have been sent during execution, but send final status)
        if process.returncode != 0:
            stderr_text = "".join(stderr_buffer).strip()
            if stderr_text and error_callback:
                try:
                    # Only send if we haven't sent this exact error already
                    error_msg = f"Process exited with code {process.returncode}"
                    if stderr_text:
                        error_msg += f": {stderr_text[-500:]}"  # Last 500 chars of stderr
                    await error_callback(error_msg)
                except Exception as callback_error:
                    logger.warning(f"Error in error_callback: {callback_error}")

        # Use the same processing logic
        return self._process_stdout_stderr(
            stdout_bytes, stderr_bytes, process, prompt_text, start_time
        )

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
                    tasks.append({"task": task_text, "status": status})

        return tasks

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
