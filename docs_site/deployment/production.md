# Production Checklist

Use this checklist to deploy tg-note to production reliably.

## Prerequisites

- Docker and Docker Compose installed
- Git repository prepared for your knowledge base
- `.env` populated (at minimum `TELEGRAM_BOT_TOKEN`)

## Steps

1. Build and start services:
   ```bash
   docker compose up -d --build
   ```
2. Authenticate Qwen CLI inside the bot container (if using `qwen_code_cli`):
   ```bash
   docker exec -it tg-note-bot bash -lc "qwen"
   docker exec -it tg-note-bot bash -lc "qwen <<<'/approval-mode yolo --project'"
   ```
3. Validate health:
   ```bash
   docker ps
   docker logs -f tg-note-bot
   curl http://localhost:8765/health
   ```

## Hardening

- Set `ALLOWED_USER_IDS` to restrict access
- Rotate API keys regularly
- Configure log rotation on host
- For vector search with Qdrant, set API keys (see vector guide)

## Operations

- Update:
  ```bash
  git pull && docker compose build --no-cache && docker compose up -d
  ```
- Backup knowledge base and data directories regularly

## Troubleshooting

- Check bot logs: `docker logs -f tg-note-bot`
- Check MCP Hub health: `curl http://localhost:8765/health`
- Verify `.env` and `config.yaml` are mounted as expected
