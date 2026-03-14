# Configuration Guide

Milo supports two config sources:

1. Environment variables, including values loaded from `.env`
2. Local `config.json`

Environment variables take priority.

## Required

- `DISCORD_TOKEN`
  Description: Discord bot token.
  Required: yes.

## AI Chat

- `OPENAI_API_KEY`
  Description: default API key used when a guild has not provided its own key.
  Required: no.
  Note: if omitted, `/chat` only works in guilds where admins set a server-specific key.

- `OPENAI_API_BASE`
  Description: base URL for the chat completion API.
  Default: `https://api.openai.com/v1`

- `ALLOW_USER_KEYS`
  Description: whether guild admins may store their own API key with `/chat-config set-key`.
  Default: `true`
  Values: `true` or `false`

- `DEFAULT_CHAT_MODEL`
  Description: model used when the user does not specify one.
  Default: `gpt-4o-mini`

- `ALLOWED_CHAT_MODELS`
  Description: comma-separated environment value or JSON array in `config.json`.
  Default: `gpt-4o-mini,gpt-4o`
  Note: `/chat` rejects models outside this allowlist.

## Google Custom Search

- `GOOGLE_API_KEY`
- `GOOGLE_CSE_ID`

Description: enable optional live web search for `/chat`.

Important:

- Both values must be present for web search to be enabled.
- These services may incur cost depending on your Google account setup.

## Example `.env`

```env
DISCORD_TOKEN=your_discord_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
ALLOW_USER_KEYS=true
DEFAULT_CHAT_MODEL=gpt-4o-mini
ALLOWED_CHAT_MODELS=gpt-4o-mini,gpt-4o
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id_here
```

## Example `config.json`

```json
{
  "DISCORD_TOKEN": "your_discord_token_here",
  "OPENAI_API_KEY": "your_openai_api_key_here",
  "OPENAI_API_BASE": "https://api.openai.com/v1",
  "ALLOW_USER_KEYS": true,
  "DEFAULT_CHAT_MODEL": "gpt-4o-mini",
  "ALLOWED_CHAT_MODELS": ["gpt-4o-mini", "gpt-4o"],
  "GOOGLE_API_KEY": "your_google_api_key_here",
  "GOOGLE_CSE_ID": "your_custom_search_engine_id_here"
}
```

## Secret Handling

- Do not commit real values to git.
- Prefer `.env` for local development.
- Keep `config.json` local and gitignored if you use it for secrets.
- Rotate any credential immediately if it is exposed.
