## Changelog

**v1.0.4** – 2026-03-20
- Added bounded reminder and scheduled announcement polling, plus admin diagnostics for failed announcements.
- Added cleanup for stale chat cooldown state and retained message logs with periodic pruning.
- Hardened media commands against upstream API failures and clarified automod handling for thread channels.
- Reduced economy lock contention to per-guild scope and added length guards for reminders and announcements.
- Prevented `/help all` embed overflows and added regression tests covering the issue backlog fixes.

**v1.0.3** – 2026-03-14
- Isolated guild chat history per user and added server-side AI chat safety controls.
- Added basic automod, warning history commands, and better moderation logging support.
- Added scheduled announcements, welcome/goodbye previews, recurring reminders, and reminder snoozing.
- Fixed reminder delivery loss, guild economy cooldown scope, and anti-spam isolation issues.


**v1.0.2** – 2025-07-28
- Improved the installation script with added support for Windows environments.


**v1.0.1** – 2025-07-23
- Initial public release
