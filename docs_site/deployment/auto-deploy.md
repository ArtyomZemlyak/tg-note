# Auto-deploy via Git + Docker Compose

This guide shows how to enable automatic deployments on a single Linux host using Git and Docker Compose. It works with cron or systemd timers and focuses on safety: if certain critical files change (e.g., `.env` or `docker-compose.yml`), the deployment is blocked to avoid breaking production.

## Features

- Detects updates in the remote Git branch
- Blocks deployment if critical files changed (configurable via blocklist)
- Builds images using one or more Compose files
- Deploys using `docker compose up -d` or restarts services
- Supports logs and a file lock to prevent overlapping runs

## Files

- `scripts/auto_deploy.sh` — main script
- `scripts/auto_deploy.conf.example` — example configuration to copy and adjust
- `scripts/auto_deploy.blocklist` — default glob patterns treated as critical changes

## Install

1. Copy the example config and edit paths and options:

```bash
cp scripts/auto_deploy.conf.example scripts/auto_deploy.conf
$EDITOR scripts/auto_deploy.conf
```

2. Ensure the script is executable:

```bash
chmod +x scripts/auto_deploy.sh
```

3. Make sure the repo is cloned on the host and the configured branch exists (default `main`).

## Configuration

The config is bash-sourced by the script. Key options:

- `REPO_DIR`: absolute path to your repo clone
- `REMOTE`, `BRANCH`: Git remote and branch to track
- `AUTO_CHECKOUT`: switch to `BRANCH` automatically if different
- `COMPOSE_FILES`: one or multiple compose files, colon-separated
- `SERVICES`: optional space-separated list of services to limit build/deploy
- `BUILD_FLAGS`: flags for `compose build` (e.g., `--pull`, `--no-cache`)
- `DEPLOY_COMMAND`: `up` (default) or `restart`
- `UP_FLAGS`: flags passed to `compose up` when `DEPLOY_COMMAND=up`
- `PRUNE_AFTER`: `true`/`false` to prune dangling images after deploy
- `CRITICAL_PATHS_FILE`: path to blocklist file
- `CRITICAL_PATHS`: comma-separated glob patterns; complements the file
- `LOG_FILE`, `LOCK_FILE`: where to write logs and lock
- `COMPOSE_CMD_OVERRIDE`: force `docker-compose` if needed

## Safety: Critical Changes

If any changed file matches the blocklist, deployment is skipped with exit code 10. You can edit `scripts/auto_deploy.blocklist` or specify extra patterns via `CRITICAL_PATHS` in the config.

Common critical patterns:

- `.env*`
- `config/**`
- `docker-compose*.yml`
- `Dockerfile*`
- `requirements*.txt`, `pyproject.toml`, `poetry.lock`

## Cron Setup

Edit your user crontab with `crontab -e` and add:

```cron
*/5 * * * * /bin/bash -lc 'cd /path/to/your/repo && scripts/auto_deploy.sh -c scripts/auto_deploy.conf >> logs/cron.tail 2>&1'
```

This runs every 5 minutes. The script itself writes a detailed log to `LOG_FILE` (configured), and uses a lock file to prevent overlap.

## Systemd Timer (alternative)

Create `/etc/systemd/system/auto-deploy.service`:

```ini
[Unit]
Description=Auto Deploy Service
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/your/repo
Environment=CONFIG_FILE=/path/to/your/repo/scripts/auto_deploy.conf
ExecStart=/bin/bash -lc 'scripts/auto_deploy.sh -c "$CONFIG_FILE"'
```

Create `/etc/systemd/system/auto-deploy.timer`:

```ini
[Unit]
Description=Run Auto Deploy every 5 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
Unit=auto-deploy.service

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now auto-deploy.timer
```

## Exit Codes

- `0`: No changes or deployment completed successfully
- `10`: Critical change detected, deployment skipped
- `1`: Error (e.g., unclean working tree, git fetch/pull error, compose missing)

## Notes

- The script expects a clean working tree and a fast-forwardable branch.
- If the local branch is ahead of remote, the script aborts to avoid force-pushing from automation.
- For legacy environments without `docker compose`, set `COMPOSE_CMD_OVERRIDE="docker-compose"`.
