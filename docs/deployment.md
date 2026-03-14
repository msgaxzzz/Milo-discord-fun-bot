# Deployment Guide

This guide covers practical ways to run Milo outside a local development shell.

## Requirements

- Python 3.9+
- Persistent disk access for `database/main.db`
- Network access to Discord
- Network access to optional upstream APIs if you enable them

## Minimal Host Requirements

Milo is lightweight enough for a small VPS or home server.

You need:

- one persistent process
- a writable working directory
- a way to restart the bot after crashes or machine reboot

## Recommended Layout

```text
Milo-discord-fun-bot/
  .env
  database/
    main.db
  cogs/
  docs/
  main.py
```

## Linux With `systemd`

Example unit file:

```ini
[Unit]
Description=Milo Discord Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/Milo-discord-fun-bot
EnvironmentFile=/opt/Milo-discord-fun-bot/.env
ExecStart=/opt/Milo-discord-fun-bot/.venv/bin/python /opt/Milo-discord-fun-bot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Typical flow:

1. Create the virtual environment
2. Install dependencies
3. Place secrets in `.env`
4. Create the `database/` directory if it does not exist
5. Start and enable the service

## Containers

If you containerize Milo:

- mount persistent storage for `database/main.db`
- inject secrets through environment variables
- do not bake real keys into the image

## Upgrading A Running Instance

1. Stop the process
2. Pull the latest code
3. Reinstall dependencies if `requirements.txt` changed
4. Start the process again
5. Watch logs for migrations or failed cog loads

## Backups

Back up:

- `database/main.db`
- `.env` if used
- local `config.json` if used

## Operational Warnings

- SQLite is fine for small and medium self-hosted usage, but it is not designed for horizontally scaled multi-writer deployments
- OpenAI and Google integrations can produce external cost
- user-supplied API keys are stored locally when that feature is enabled
