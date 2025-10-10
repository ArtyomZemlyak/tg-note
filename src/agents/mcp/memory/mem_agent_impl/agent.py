import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, Tuple, Union

from loguru import logger

from src.agents.mcp.memory.mem_agent_impl.engine import execute_sandboxed_code

# Configure logging for mem-agent
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Remove default logger and add file logging
if not logger._core.handlers:
    logger.add(
        log_dir / "mem_agent.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
    
    logger.add(
        log_dir / "mem_agent_errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
from src.agents.mcp.memory.mem_agent_impl.model import (
    create_openai_client,
    create_vllm_client,
    get_model_response,
)
from src.agents.mcp.memory.mem_agent_impl.schemas import AgentResponse, ChatMessage, Role
from src.agents.mcp.memory.mem_agent_impl.settings import (
    MAX_TOOL_TURNS,
    MEM_AGENT_BASE_URL,
    MEM_AGENT_HOST,
    MEM_AGENT_OPENAI_API_KEY,
    MEM_AGENT_PORT,
    MEMORY_PATH,
    OPENROUTER_STRONG_MODEL,
    SAVE_CONVERSATION_PATH,
)
from src.agents.mcp.memory.mem_agent_impl.utils import (
    create_memory_if_not_exists,
    extract_python_code,
    extract_reply,
    extract_thoughts,
    format_results,
    load_system_prompt,
)


class Agent:
    def __init__(
        self,
        max_tool_turns: int = MAX_TOOL_TURNS,
        memory_path: Optional[str] = None,
        use_vllm: bool = False,
        model: Optional[str] = None,
        predetermined_memory_path: bool = False,
    ):
        # Load the system prompt and add it to the conversation history
        self.system_prompt = load_system_prompt()
        self.messages: list[ChatMessage] = [
            ChatMessage(role=Role.SYSTEM, content=self.system_prompt)
        ]

        # Set the maximum number of tool turns and use_vllm flag
        self.max_tool_turns = max_tool_turns
        self.use_vllm = use_vllm

        # Set model: use provided model, or fallback to OPENROUTER_STRONG_MODEL
        if model:
            self.model = model
        else:
            self.model = OPENROUTER_STRONG_MODEL

        # Each Agent instance gets its own clients to avoid bottlenecks
        if use_vllm:
            self._client = create_vllm_client(host=MEM_AGENT_HOST, port=MEM_AGENT_PORT)
        else:
            # If no explicit API endpoint/key are provided, try to autostart a local server
            # based on platform: vLLM on Linux, MLX on macOS.
            if not MEM_AGENT_BASE_URL and not MEM_AGENT_OPENAI_API_KEY:
                self._ensure_local_server()
            self._client = create_openai_client()

        # Set memory_path: use provided path or fall back to default MEMORY_PATH
        if memory_path is not None:
            # Always place custom memory paths inside a "memory/" folder
            if predetermined_memory_path:
                self.memory_path = os.path.join("memory", memory_path)
            else:
                self.memory_path = memory_path
        else:
            # Use default MEMORY_PATH but also place it inside "memory/" folder
            self.memory_path = os.path.join("memory", MEMORY_PATH)

        # Ensure memory_path is absolute for consistency
        self.memory_path = os.path.abspath(self.memory_path)
        
        logger.info(f"Agent initialized: model={self.model}, use_vllm={use_vllm}, memory_path={self.memory_path}")

    def _ensure_local_server(self) -> None:
        """Ensure a local OpenAI-compatible server is running and export MEM_AGENT_BASE_URL.

        - Linux: start vLLM if not reachable at configured host/port
        - macOS: start MLX if not reachable at configured host/port
        """
        import platform
        import subprocess
        import time
        from urllib.error import URLError
        from urllib.request import urlopen

        system = platform.system().lower()
        logger.info(f"Ensuring local server is running (system={system})")

        # Prefer vLLM on Linux, MLX on macOS
        if system == "linux":
            host, port = MEM_AGENT_HOST, MEM_AGENT_PORT
            base_url = f"http://{host}:{port}/v1"
            logger.debug(f"Checking vLLM server at {base_url}")
            
            # Quick reachability check
            try:
                urlopen(f"{base_url}/models", timeout=0.5)
                logger.info(f"vLLM server already running at {base_url}")
                os.environ.setdefault("MEM_AGENT_BASE_URL", base_url)
                return
            except URLError as e:
                logger.debug(f"vLLM server not reachable: {e}")

            # Try to start vLLM server in background
            logger.info(f"Starting vLLM server at {host}:{port} with model {OPENROUTER_STRONG_MODEL}")
            
            # Create log file for vLLM server
            vllm_log_file = log_dir / "vllm_server.log"
            vllm_error_file = log_dir / "vllm_server_errors.log"
            
            try:
                with open(vllm_log_file, "a") as log_f, open(vllm_error_file, "a") as err_f:
                    log_f.write(f"\n=== vLLM server startup at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                    err_f.write(f"\n=== vLLM server startup at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                    
                    subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "vllm.entrypoints.openai.api_server",
                            "--host",
                            host,
                            "--port",
                            str(port),
                            "--model",
                            OPENROUTER_STRONG_MODEL,
                        ],
                        stdout=log_f,
                        stderr=err_f,
                    )
                    logger.info("vLLM server process started, waiting for it to be ready...")
                
                # Give it a brief moment to come up
                for i in range(10):
                    time.sleep(0.5)
                    try:
                        urlopen(f"{base_url}/models", timeout=0.5)
                        logger.info(f"vLLM server is ready at {base_url}")
                        os.environ.setdefault("MEM_AGENT_BASE_URL", base_url)
                        return
                    except URLError:
                        logger.debug(f"Waiting for vLLM server... ({i+1}/10)")
                        continue
                
                logger.warning(f"vLLM server did not become ready after 5 seconds. Check {vllm_error_file}")
            except Exception as e:
                # Fall back silently; create_openai_client will use defaults
                logger.error(f"Failed to start vLLM server: {e}", exc_info=True)
                logger.info("Will attempt to use OpenRouter or configured OpenAI endpoint instead")

        elif system == "darwin":
            # MLX-backed OpenAI-compatible server; use unified host/port
            host, port = MEM_AGENT_HOST, MEM_AGENT_PORT
            base_url = f"http://{host}:{port}/v1"
            logger.debug(f"Checking MLX server at {base_url}")
            
            try:
                urlopen(f"{base_url}/models", timeout=0.5)
                logger.info(f"MLX server already running at {base_url}")
                os.environ.setdefault("MEM_AGENT_BASE_URL", base_url)
                return
            except URLError as e:
                logger.debug(f"MLX server not reachable: {e}")

            logger.info(f"Starting MLX server at {host}:{port} with model {OPENROUTER_STRONG_MODEL}")
            
            # Create log file for MLX server
            mlx_log_file = log_dir / "mlx_server.log"
            mlx_error_file = log_dir / "mlx_server_errors.log"
            
            try:
                with open(mlx_log_file, "a") as log_f, open(mlx_error_file, "a") as err_f:
                    log_f.write(f"\n=== MLX server startup at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                    err_f.write(f"\n=== MLX server startup at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                    
                    subprocess.Popen(
                        [
                            "mlx_lm",
                            "serve",
                            OPENROUTER_STRONG_MODEL,
                            "--host",
                            host,
                            "--port",
                            str(port),
                            "--api",
                            "openai",
                        ],
                        stdout=log_f,
                        stderr=err_f,
                    )
                    logger.info("MLX server process started, waiting for it to be ready...")
                
                for i in range(10):
                    time.sleep(0.5)
                    try:
                        urlopen(f"{base_url}/models", timeout=0.5)
                        logger.info(f"MLX server is ready at {base_url}")
                        os.environ.setdefault("MEM_AGENT_BASE_URL", base_url)
                        return
                    except URLError:
                        logger.debug(f"Waiting for MLX server... ({i+1}/10)")
                        continue
                
                logger.warning(f"MLX server did not become ready after 5 seconds. Check {mlx_error_file}")
            except Exception as e:
                logger.error(f"Failed to start MLX server: {e}", exc_info=True)
                logger.info("Will attempt to use OpenRouter or configured OpenAI endpoint instead")

    def _add_message(self, message: Union[ChatMessage, dict]):
        """Add a message to the conversation history."""
        if isinstance(message, dict):
            self.messages.append(ChatMessage(**message))
        elif isinstance(message, ChatMessage):
            self.messages.append(message)
        else:
            raise ValueError("Invalid message type")

    def extract_response_parts(self, response: str) -> Tuple[str, str, str]:
        """
        Extract the thoughts, reply and python code from the response.

        Args:
            response: The response from the agent.

        Returns:
            A tuple of the thoughts, reply and python code.
        """
        thoughts = extract_thoughts(response)
        reply = extract_reply(response)
        python_code = extract_python_code(response)

        return thoughts, reply, python_code

    def chat(self, message: str) -> AgentResponse:
        """
        Chat with the agent.

        Args:
            message: The message to chat with the agent.

        Returns:
            The response from the agent.
        """
        logger.info(f"Chat started with message: {message[:100]}...")
        
        try:
            # Add the user message to the conversation history
            self._add_message(ChatMessage(role=Role.USER, content=message))

            # Get the response from the agent using this instance's clients
            logger.debug(f"Getting model response (model={self.model}, use_vllm={self.use_vllm})")
            response = get_model_response(
                messages=self.messages,
                model=self.model,  # Pass the model if specified
                client=self._client,
                use_vllm=self.use_vllm,
            )
        except Exception as e:
            logger.error(f"Error getting model response: {e}", exc_info=True)
            raise

        # Extract the thoughts, reply and python code from the response
        thoughts, reply, python_code = self.extract_response_parts(response)
        logger.debug(f"Extracted: thoughts={bool(thoughts)}, reply={bool(reply)}, python_code={bool(python_code)}")

        # Execute the code from the agent's response
        result = ({}, "")
        if python_code:
            logger.debug(f"Executing Python code: {python_code[:200]}...")
            try:
                create_memory_if_not_exists(self.memory_path)
                result = execute_sandboxed_code(
                    code=python_code,
                    allowed_path=self.memory_path,
                    import_module="src.agents.mcp.memory.mem_agent_impl.tools",
                )
                logger.debug(f"Code execution result: {result[0]}, error: {result[1]}")
            except Exception as e:
                logger.error(f"Error executing sandboxed code: {e}", exc_info=True)
                result = ({}, str(e))

        # Add the agent's response to the conversation history
        self._add_message(ChatMessage(role=Role.ASSISTANT, content=response))

        remaining_tool_turns = self.max_tool_turns
        logger.debug(f"Starting tool execution loop (max_turns={self.max_tool_turns})")
        while remaining_tool_turns > 0 and not reply:
            self._add_message(
                ChatMessage(role=Role.USER, content=format_results(result[0], result[1]))
            )
            response = get_model_response(
                messages=self.messages,
                model=self.model,  # Pass the model if specified
                client=self._client,
                use_vllm=self.use_vllm,
            )

            # Extract the thoughts, reply and python code from the response
            thoughts, reply, python_code = self.extract_response_parts(response)

            self._add_message(ChatMessage(role=Role.ASSISTANT, content=response))
            if python_code:
                create_memory_if_not_exists(self.memory_path)
                result = execute_sandboxed_code(
                    code=python_code,
                    allowed_path=self.memory_path,
                    import_module="src.agents.mcp.memory.mem_agent_impl.tools",
                )
            else:
                # Reset result when no Python code is executed
                result = ({}, "")
            remaining_tool_turns -= 1

        return AgentResponse(thoughts=thoughts, reply=reply, python_block=python_code)

    def save_conversation(self, log: bool = False, save_folder: str = None):
        """
        Save the conversation messages to a JSON file in
        the output/conversations directory.
        """
        if not os.path.exists(SAVE_CONVERSATION_PATH):
            os.makedirs(SAVE_CONVERSATION_PATH, exist_ok=True)

        unique_id = uuid.uuid4()
        if not save_folder:
            file_path = os.path.join(SAVE_CONVERSATION_PATH, f"convo_{unique_id}.json")
        else:
            folder_path = save_folder  # os.path.join(SAVE_CONVERSATION_PATH, save_folder)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            file_path = os.path.join(folder_path, f"convo_{unique_id}.json")

        # Convert the execution result messages to tool role
        messages = [
            (
                ChatMessage(role=Role.TOOL, content=message.content)
                if message.content.startswith("<result>")
                else ChatMessage(role=message.role, content=message.content)
            )
            for message in self.messages
        ]
        try:
            with open(file_path, "w") as f:
                json.dump([message.model_dump() for message in messages], f, indent=4)
        except Exception as e:
            if log:
                print(f"Error saving conversation: {e}")
        if log:
            print(f"Conversation saved to {file_path}")
