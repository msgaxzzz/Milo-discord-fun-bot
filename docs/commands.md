# Command Reference

This document summarizes the current slash commands exposed by Milo.

## AI Chat

- `/chat`
  Purpose: talk to the configured AI model, optionally with web search.
  Works in: servers and DMs.
  Inputs: `prompt`, optional `model`, optional `search_web`.

- `/chat-reset`
  Purpose: clear the current conversation context.
  Works in: servers and DMs.

- `/chat-config set-key`
  Purpose: store a server-specific OpenAI API key.
  Works in: servers only.
  Permission: `Manage Server`.

- `/chat-config set-persona`
  Purpose: set a server-specific system persona for chat.
  Works in: servers only.
  Permission: `Manage Server`.

- `/chat-config view`
  Purpose: inspect the current server chat configuration.
  Works in: servers only.
  Permission: `Manage Server`.

- `/chat-config set-enabled`
- `/chat-config set-cooldown`
- `/chat-config set-usage-cap`
- `/chat-config allow-channel`
- `/chat-config block-channel`
- `/chat-config clear-channel-rules`
- `/chat-config allow-role`
- `/chat-config remove-role`
- `/chat-config clear-role-rules`
  Purpose: control where AI chat can be used, who can use it, and how often.
  Works in: servers only.
  Permission: `Manage Server`.

- `/chat-config test`
  Purpose: validate the effective API key for the current server.
  Works in: servers only.
  Permission: `Manage Server`.

- `/chat-config models`
  Purpose: show the default model and the allowlisted models.
  Works in: servers only.
  Permission: `Manage Server`.

## Economy

All economy data is per guild.

- `/balance`
  Purpose: view your balance or another member's balance.
  Works in: servers only.

- `/daily`
  Purpose: claim the daily reward.
  Works in: servers only.

- `/jobs freelance`
- `/jobs regular`
- `/jobs crime`
  Purpose: earn coins through cooldown-based work commands.
  Works in: servers only.

- `/gamble`
  Purpose: wager coins on a simple chance outcome.
  Works in: servers only.

- `/slots`
  Purpose: use the slot machine.
  Works in: servers only.

- `/leaderboard`
  Purpose: show the richest users in the current server.
  Works in: servers only.

- `/transfer`
  Purpose: send coins to another member.
  Works in: servers only.

- `/rob`
  Purpose: attempt to steal coins from another member.
  Works in: servers only.

- `/economy-admin add`
- `/economy-admin remove`
- `/economy-admin set`
- `/economy-admin reset-guild`
  Purpose: administrative balance management for the current guild.
  Works in: servers only.
  Permission: `Manage Server` or stronger depending on the command.

## Farming

All farming progress is per guild and uses the local economy balance.

- `/farm profile`
  Purpose: inspect current farm progress, land type, and crop status.

- `/farm shop`
  Purpose: view crop unlocks, costs, rewards, and XP.

- `/farm plant`
  Purpose: plant a crop if you have enough coins and the required farm level.

- `/farm harvest`
  Purpose: collect crop rewards and farm XP.

- `/farm upgrade`
  Purpose: buy better land to reduce growth time.

## Games

- `/eightball`
  Purpose: answer a question with a random eight-ball response.

- `/coinflip`
  Purpose: flip a coin.

- `/roll`
  Purpose: roll dice in `NdN` form.

- `/guess`
  Purpose: run a timed number guessing game in the current channel.

- `/rps`
  Purpose: play rock-paper-scissors against the bot.

- `/tictactoe`
  Purpose: challenge another member to a button-based tic-tac-toe game.

## Fun

- `/joke`
- `/fact`
- `/avatar`
- `/love`
- `/emojify`
- `/poll`
- `/clap`
- `/tweet`

Purpose: lightweight entertainment, formatting, and image-generation features.

## Interactions

- `/hug`
- `/pat`
- `/slap`
- `/kiss`
- `/cuddle`
- `/poke`

Purpose: social reaction commands backed by external GIF APIs.

## Media

- `/meme`
- `/cat`
- `/dog`

Purpose: fetch random media from public APIs.

## Utility

- `/ping`
- `/ping_raw`
  Purpose: inspect websocket and basic API latency.

- `/memberinfo`
  Works in: servers only.
  Purpose: inspect a member profile.

- `/clear`
  Works in: servers only.
  Permission: `Manage Messages`.
  Purpose: bulk-delete recent messages.

- `/serverinfo`
  Works in: servers only.
  Purpose: inspect guild metadata.

- `/botinfo`
- `/uptime`
  Purpose: inspect runtime information.

- `/help all`
- `/help command`
  Purpose: list commands or show detail for one command.

- `/remindme`
  Purpose: create a persisted reminder.
  Works in: servers and DMs.

- `/reminders recurring`
  Purpose: create a recurring reminder with a repeat interval.
  Works in: servers and DMs.

- `/reminders list`
- `/reminders cancel`
- `/reminders clear`
- `/reminders snooze`
  Purpose: manage your existing reminders, including snoozing one into the future.
  Works in: servers and DMs.

- `/afk`
  Purpose: set AFK state until your next server message in that guild.
  Works in: servers only.

- `/afk-clear`
  Purpose: clear your AFK status manually.
  Works in: servers only.

## Community

- `/server-config view`
- `/server-config set-welcome-channel`
- `/server-config set-goodbye-channel`
- `/server-config set-announcement-channel`
- `/server-config set-modlog-channel`
- `/server-config set-welcome-message`
- `/server-config set-goodbye-message`
- `/server-config preview-welcome`
- `/server-config preview-goodbye`
- `/server-config reset-message`
- `/server-config reset-channel`
  Purpose: manage server community automation.
  Works in: servers only.
  Permission: `Manage Server`.

- `/announce`
  Purpose: send an announcement to the configured announcement channel or the current channel.
  Works in: servers only.
  Permission: `Manage Server`.

- `/announcements schedule`
- `/announcements list`
- `/announcements cancel`
  Purpose: manage scheduled server announcements.
  Works in: servers only.
  Permission: `Manage Server`.

## Moderation

- `/automod view`
- `/automod toggle-invites`
- `/automod toggle-links`
- `/automod set-action`
- `/automod set-bad-words`
- `/automod clear-bad-words`
- `/automod whitelist-channel`
- `/automod remove-whitelist-channel`
  Purpose: configure invite filtering, link filtering, blocked words, channel exemptions, and automod actions.
  Works in: servers only.
  Permission: `Manage Server`.

- `/warn`
- `/warnings`
- `/clear-warning`
  Purpose: manage per-guild warning history and moderation notes.
  Works in: servers only.
  Permission: `Manage Messages`.

## Notes

- Cooldowns are enforced on many commands.
- Some commands call third-party APIs and may fail if those services are unavailable.
- Chat, media, and interaction commands depend on external services and configuration.
