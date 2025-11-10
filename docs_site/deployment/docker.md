## Docker Deployment

This project provides ready-to-use Docker images and a compose file to run the bot and the MCP hub. The bot image now includes the Qwen Code CLI, so no extra host setup is required.

### Services

- **tg-note-bot**: Telegram bot with built-in Qwen Code CLI
- **tg-note-hub**: MCP Hub server with lightweight dependencies (memory tools, MCP registry)
- **docling-mcp**: Document processing server using official `docling-mcp` package (PDF, DOCX, images, OCR)
- **vllm-server**: Optional LLM inference server for mem-agent storage type (vLLM or SGLang)

**Architecture**: The mem-agent system uses a **Docker-first approach**. Heavy ML dependencies (transformers, vLLM, MLX) are **not** installed in the hub or bot containers. Instead, LLM inference is handled by dedicated containers (vLLM/SGLang) or external services (LM Studio).

### Prerequisites

- Docker and Docker Compose
- `.env` populated with required tokens (e.g. `TELEGRAM_BOT_TOKEN`)

### Build and Run

```bash
docker compose up -d --build
```

### Qwen CLI inside the bot

- The bot image installs Node.js 20 and `@qwen-code/qwen-code` globally. The `qwen` binary is available in the container PATH.
- Qwen authentication and CLI settings are persisted via a bind mount: host `~/.qwen` -> container `/root/.qwen`.

Authenticate once inside the running bot container:

```bash
docker exec -it tg-note-bot bash -lc "qwen"
```

Follow the OAuth prompts. Then set approval mode for unattended operation:

```bash
docker exec -it tg-note-bot bash -lc "qwen <<<'/approval-mode yolo --project'"
```

Notes:
- You may choose a less permissive mode like `auto-edit`, but the bot is designed for fully automated operation and expects no interactive approvals.
- If you prefer to authenticate via OpenAI-compatible API instead of OAuth, set `OPENAI_API_KEY` and `OPENAI_BASE_URL` in the bot environment.

### Volumes

- `./knowledge_base:/app/knowledge_base` — user notes and files
- `./data:/app/data` — processed messages, user settings
- `./logs:/app/logs` — logs
- `~/.qwen:/root/.qwen` — Qwen CLI auth and settings

### Health and Troubleshooting

- Verify CLI presence: `docker exec tg-note-bot qwen --version`
- If CLI says not authenticated, re-run: `docker exec -it tg-note-bot qwen`
- If approvals block commands, re-apply: `docker exec -it tg-note-bot bash -lc "qwen <<<'/approval-mode yolo --project'"`

For more details on the CLI itself, see the agent guide: [Qwen Code CLI](../agents/qwen-code-cli.md)
