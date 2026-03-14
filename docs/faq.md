# FAQ

## Does Milo support AI chat in DMs?

Yes. `/chat` and `/chat-reset` work in DMs. Server configuration commands under `/chat-config` are guild-only.

## Is the economy shared across all servers?

No. Economy balances, leaderboards, and farming progress are stored per guild.

## Do reminders survive bot restarts?

Yes. Reminders are stored in SQLite and replayed after startup.

## Do I need OpenAI credentials?

Only if you want AI chat features. The rest of the bot can run without OpenAI credentials.

## Do I need Google API credentials?

Only if you want web-enabled search in AI chat. Both `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` must be configured.

## Where should I put secrets?

Use `.env` or a gitignored local `config.json`. Do not commit real secrets to the repository.

## What Python version should I use?

Python 3.9 or newer.

## What database does Milo use?

SQLite, stored locally at `database/main.db`.

## Can I host Milo on a VPS?

Yes. A small VPS or any machine that can keep a Python process online is enough for typical usage.

## Can I use a Python-capable hosting provider or panel?

Yes, as long as the hosting environment can:

- run Python 3.9 or newer
- keep a long-running process online
- write to local storage for SQLite
- access Discord and any external APIs you enable

Examples include VPS providers, Python app hosting platforms, Pterodactyl-style panels, and self-hosted Linux servers.

The main limitation is that Milo is a persistent Discord bot process, so it is not a fit for serverless-only platforms that cannot keep a worker running continuously.

## Is this project production-ready?

It is suitable for self-hosted real usage, but it is still a small open-source bot project. It does not yet have a full automated test suite or enterprise-style operational tooling.
