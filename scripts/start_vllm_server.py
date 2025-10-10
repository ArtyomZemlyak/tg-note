#!/usr/bin/env python3
"""
vLLM Server Wrapper with Logging

This script starts a vLLM server for mem-agent with proper logging configuration.
It wraps the vLLM server process and captures all output to log files.

Usage:
    python scripts/start_vllm_server.py [--model MODEL] [--host HOST] [--port PORT]

Default:
    Model: driaforall/mem-agent
    Host: 127.0.0.1
    Port: 8001
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir: Path):
    """Setup logging directory and files"""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"vllm_server_{timestamp}.log"
    error_log_file = log_dir / f"vllm_server_{timestamp}.error.log"
    
    # Create symlinks to latest logs
    latest_log = log_dir / "vllm_server_latest.log"
    latest_error_log = log_dir / "vllm_server_latest_error.log"
    
    if latest_log.exists():
        latest_log.unlink()
    if latest_error_log.exists():
        latest_error_log.unlink()
    
    latest_log.symlink_to(log_file.name)
    latest_error_log.symlink_to(error_log_file.name)
    
    return log_file, error_log_file


def main():
    parser = argparse.ArgumentParser(
        description="vLLM Server for mem-agent with logging"
    )
    parser.add_argument(
        "--model",
        default="driaforall/mem-agent",
        help="Model to load (default: driaforall/mem-agent)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to bind to (default: 8001)",
    )
    parser.add_argument(
        "--tensor-parallel-size",
        type=int,
        default=1,
        help="Tensor parallel size for multi-GPU (default: 1)",
    )
    parser.add_argument(
        "--gpu-memory-utilization",
        type=float,
        default=0.9,
        help="GPU memory utilization (default: 0.9)",
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        help="Max model length (optional)",
    )
    parser.add_argument(
        "--log-dir",
        default="logs/mcp_servers",
        help="Log directory (default: logs/mcp_servers)",
    )
    parser.add_argument(
        "--dtype",
        choices=["auto", "half", "float16", "bfloat16", "float32"],
        default="auto",
        help="Model dtype (default: auto)",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_dir = Path(args.log_dir)
    log_file, error_log_file = setup_logging(log_dir)
    
    print(f"Starting vLLM server for {args.model}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Log file: {log_file}")
    print(f"Error log file: {error_log_file}")
    print("")
    
    # Build vLLM command
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", args.model,
        "--host", args.host,
        "--port", str(args.port),
        "--tensor-parallel-size", str(args.tensor_parallel_size),
        "--gpu-memory-utilization", str(args.gpu_memory_utilization),
        "--dtype", args.dtype,
    ]
    
    if args.max_model_len:
        cmd.extend(["--max-model-len", str(args.max_model_len)])
    
    print("Command:", " ".join(cmd))
    print("")
    
    # Open log files
    with open(log_file, "w") as stdout_log, open(error_log_file, "w") as stderr_log:
        # Write header
        header = f"vLLM Server Log - Started at {datetime.now().isoformat()}\n"
        header += f"Model: {args.model}\n"
        header += f"Host: {args.host}:{args.port}\n"
        header += "=" * 80 + "\n\n"
        
        stdout_log.write(header)
        stdout_log.flush()
        stderr_log.write(header)
        stderr_log.flush()
        
        # Start vLLM server
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
            )
            
            print(f"vLLM server started with PID: {process.pid}")
            print(f"Monitor logs: tail -f {log_file}")
            print(f"Monitor errors: tail -f {error_log_file}")
            print("")
            print("Press Ctrl+C to stop the server")
            print("")
            
            # Stream output to both console and log files
            import threading
            
            def stream_output(pipe, log_file, prefix=""):
                for line in pipe:
                    # Write to log file
                    log_file.write(f"{prefix}{line}")
                    log_file.flush()
                    
                    # Also print to console (can be disabled with --quiet flag)
                    print(f"{prefix}{line}", end="")
            
            # Start threads to capture stdout and stderr
            stdout_thread = threading.Thread(
                target=stream_output,
                args=(process.stdout, stdout_log),
            )
            stderr_thread = threading.Thread(
                target=stream_output,
                args=(process.stderr, stderr_log, "[ERROR] "),
            )
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for process
            process.wait()
            
            # Join threads
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            
            if process.returncode != 0:
                print(f"\nvLLM server exited with code {process.returncode}")
                print(f"Check error log: {error_log_file}")
                sys.exit(process.returncode)
            
        except KeyboardInterrupt:
            print("\n\nShutting down vLLM server...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing vLLM server...")
                process.kill()
            print("vLLM server stopped")
            
        except Exception as e:
            print(f"\nError running vLLM server: {e}")
            stderr_log.write(f"\nFatal error: {e}\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
