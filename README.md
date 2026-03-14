# Milo

Milo is an open-source Discord bot for community operations, support, and lightweight moderation, built with `discord.py`, `aiosqlite`, and `aiohttp`.

It combines:

- AI-assisted community help with optional web search
- Moderation, announcements, reminders, and server utility workflows
- Per-server progression systems and engagement features
- Self-hosted infrastructure for small online communities

## Why This Project Exists

Milo is intended to be a practical bot for real online communities, not a one-command demo or a closed hosted service. The project focuses on tools that help small servers stay active, organized, and easier to support:

- AI-assisted help for common community questions
- reminders, announcements, and lightweight operations workflows
- simple moderation and safety helpers
- self-hosted engagement features that communities can adapt to their own needs

## Project Model

- License: MIT
- Runtime target: Python 3.9+
- Storage: SQLite
- Secrets: environment variables first, then local `config.json`
- Distribution: free and open source
- Maintenance model: community-maintained and intended for self-hosted, non-closed deployments

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

- open-source project servers
- small online communities that need self-hosted tooling
- learning groups, support communities, and volunteer-run servers
- maintainers who want a compact `discord.py` codebase to extend

## What Milo Includes

- AI chat with configurable model allowlists and optional Google Custom Search
- Chat safety controls for cooldowns, channel rules, role allowlists, and daily usage caps
- Utility commands for persisted reminders, recurring reminders, AFK management, help, and server info
- Community tooling for welcome messages, leave messages, scheduled announcements, and mod logs
- Moderation tooling for warnings, invite/link filters, bad word filters, and channel whitelists
- Economy commands with per-guild balances and leaderboards
- Admin tools for managing server economy balances
- Farming progression tied to the server economy
- Games like `/guess`, `/tictactoe`, `/roll`, and `/rps`
- Fun and media commands for polls, memes, avatars, GIF interactions, and image generation

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

## Project Site

The repository includes a static project site in [`site/`](./site) that is intended for Cloudflare Pages deployment.

Typical deployment flow:

```bash
wrangler pages project create milo-discord-bot
wrangler pages deploy site --project-name milo-discord-bot
```

The site is designed to act as a public project page, documentation index, and Cloudflare-facing overview for the bot.

## Contributors

Milo is community-maintained. See the full contributor list on GitHub:

- [Contributors Graph](https://github.com/msgaxzzz/Milo-discord-fun-bot/graphs/contributors)
- Sascha Buehrle ([`@saschabuehrle`](https://github.com/saschabuehrle)) has submitted community fixes for interaction message formatting and poll permission handling through pull requests [#39](https://github.com/msgaxzzz/Milo-discord-fun-bot/pull/39) and [#40](https://github.com/msgaxzzz/Milo-discord-fun-bot/pull/40).

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
