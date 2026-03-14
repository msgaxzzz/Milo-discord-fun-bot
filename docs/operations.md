# Operations Notes

This document covers behavior that matters when hosting or maintaining Milo.

## Runtime Requirements

- Python 3.9+
- Network access for Discord and any external APIs you enable
- Writable filesystem access for `database/main.db`

## Storage

Milo uses SQLite at:

```text
database/main.db
```

At startup, the bot creates or migrates tables as needed.

## Data Behavior

- Economy balances are stored per guild
- Farming progress is stored per guild
- Chat configuration is stored per guild
- Reminders are persisted and replayed after restart
- Message metadata is stored for spam detection and migration support

## External Services

Optional services:

- OpenAI-compatible chat API
- Google Custom Search
- Meme and animal image APIs
- GIF APIs for social interaction commands

If any external service fails, affected commands may return an error or degraded response.

## Upgrades

When updating the bot:

1. Stop the running process
2. Pull the latest code
3. Reinstall dependencies if needed
4. Restart the bot
5. Watch startup logs for schema migration or API errors

## Logging

Logging is configured in the main process and writes to stdout.

Watch for:

- configuration load failures
- failed cog loads
- database migration problems
- external API errors

## Backup

For a simple backup strategy, copy:

- `database/main.db`
- local `.env` if you are using it
- local `config.json` if you are using it

Do not commit these backups to the repository.

## Security and Cost

- OpenAI and Google integrations can create ongoing cost
- User-provided API keys are stored in SQLite when enabled
- Rotate leaked keys immediately
- Keep public logs and screenshots free of secrets
