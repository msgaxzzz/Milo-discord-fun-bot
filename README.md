# Milo

Milo is an open-source Discord bot built with `discord.py`, `aiosqlite`, and `aiohttp`.

It combines:

- AI chat with optional web search
- Per-server economy and farming systems
- Games, media, and social interaction commands
- Utility and moderation helpers

## Why This Project Exists

Milo is meant to be a practical community bot rather than a single-purpose demo. The project focuses on features that are useful in real Discord servers:

- lightweight AI-assisted conversations
- server-local progression systems
- simple moderation helpers
- low-friction entertainment and engagement commands

## Status

- License: MIT
- Runtime target: Python 3.9+
- Storage: SQLite
- Secrets: environment variables first, then local `config.json`

## Quick Start

```bash
git clone https://github.com/msgaxzzz/Milo-discord-fun-bot.git
cd Milo-discord-fun-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 main.py
```

Fill in `.env` before starting the bot.

## Who It Is For

- personal Discord servers
- small online communities
- friend groups that want a self-hosted bot
- maintainers who want a compact `discord.py` codebase to extend

## What Milo Includes

- AI chat with configurable model allowlists and optional Google Custom Search
- Chat safety controls for cooldowns, channel rules, role allowlists, and daily usage caps
- Economy commands with per-guild balances and leaderboards
- Admin tools for managing server economy balances
- Farming progression tied to the server economy
- Games like `/guess`, `/tictactoe`, `/roll`, and `/rps`
- Fun and media commands for polls, memes, avatars, GIF interactions, and image generation
- Utility commands for persisted reminders, recurring reminders, AFK management, help, moderation, and server info
- Community tooling for welcome messages, leave messages, scheduled announcements, and mod logs
- Moderation tooling for warnings, invite/link filters, bad word filters, and channel whitelists

## Important Behavior

- Economy and farming data are isolated per guild
- AI chat works in servers and DMs, but server configuration commands are guild-only
- Guild chat history is isolated per user instead of being shared by the whole channel
- Reminders are persisted in SQLite, survive restarts, and can be recurring
- AFK status is stored per guild and cleared on your next message in that server
- Real secrets should never be committed to git

## Configuration

Milo loads config in this order:

1. Environment variables from the current shell or `.env`
2. Local `config.json`

Required:

- `DISCORD_TOKEN`

Optional:

- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `ALLOW_USER_KEYS`
- `DEFAULT_CHAT_MODEL`
- `ALLOWED_CHAT_MODELS`
- `GOOGLE_API_KEY`
- `GOOGLE_CSE_ID`

See:

- [Configuration Guide](./docs/configuration.md)
- [.env.example](./.env.example)

## Documentation

- [Command Reference](./docs/commands.md)
- [Configuration Guide](./docs/configuration.md)
- [Deployment Guide](./docs/deployment.md)
- [Operations Notes](./docs/operations.md)
- [FAQ](./docs/faq.md)
- [Contributing](./CONTRIBUTING.md)
- [Code of Conduct](./CODE_OF_CONDUCT.md)
- [Security Policy](./SECURITY.md)
- [Support](./SUPPORT.md)

## Installation Scripts

The repository includes:

- [install.sh](./install.sh) for Linux/macOS-style environments
- [install.bat](./install.bat) for Windows

Both installers are intended for local setup and will generate a local `config.json`.

## Manual Setup

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python3 main.py
```

### Windows

```bat
py -3.9 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
python main.py
```

## Deployment

For a small self-hosted setup, any machine that can:

- run Python 3.9+
- keep a long-lived process online
- write to local disk
- access Discord and optional external APIs

is enough.

Common options:

- a VPS
- a home server
- a cloud VM
- a container host

See [Deployment Guide](./docs/deployment.md) for process management and environment notes.

## FAQ

Common questions:

- Does Milo support DMs for AI chat? Yes.
- Is the economy global across all servers? No, it is isolated per guild.
- Do reminders survive restarts? Yes.
- Can I schedule recurring reminders and server announcements? Yes.
- Do I need OpenAI credentials to run the bot? Only for AI chat features.

See the full [FAQ](./docs/faq.md).

## Development Notes

- Slash commands are loaded from modules in `cogs/`
- Shared HTTP access is managed centrally by the bot process
- SQLite schema is created and migrated at startup
- The project currently relies on manual verification rather than a full automated test suite

## Security

- Never commit real Discord, OpenAI, or Google API credentials
- Use `.env` or a gitignored local `config.json`
- Report vulnerabilities privately according to [SECURITY.md](./SECURITY.md)

## Project Structure

```text
main.py
config_loader.py
cogs/
docs/
```

## Roadmap

Near-term improvements that would strengthen the project:

- automated tests for economy, farming, reminder, and automod flows
- richer reporting around reminder delivery failures and scheduled announcement failures
- structured logging and better runtime error reporting
- richer deployment examples
- command reference generation from source metadata
