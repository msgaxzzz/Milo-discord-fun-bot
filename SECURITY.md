# Security Policy

## Supported Versions

Only the latest code on `main` should be assumed to receive security fixes.

## Reporting a Vulnerability

Do not open a public issue for security problems.

Report vulnerabilities privately with:

- A clear description of the issue
- Steps to reproduce
- Impact
- Any suggested fix or mitigation

## What to Report

Examples:

- Token or API key exposure
- Permission bypass
- Unsafe handling of user-provided API keys
- Remote code execution or command injection
- Database corruption or multi-guild data leakage
- Abuse paths in moderation features

## Response Goals

The maintainer should aim to:

- Acknowledge valid reports promptly
- Reproduce and assess impact
- Patch privately when reasonable
- Credit the reporter if they want attribution

## Secret Handling

- Never commit real `DISCORD_TOKEN`, OpenAI keys, or Google API keys
- Use `.env` or a gitignored local `config.json`
- Rotate any credential immediately if it is exposed in git history, logs, or screenshots
