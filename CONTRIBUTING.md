# Contributing to Milo

Thanks for contributing. Keep changes small, reviewable, and easy to test.

## Before You Start

- Read [README.md](./README.md) for setup instructions.
- Do not commit real secrets, tokens, or API keys.
- Prefer opening an issue before large feature work or schema changes.

## Development Setup

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Configure secrets with `.env` or a local `config.json`.
5. Start the bot:

```bash
python3 main.py
```

Milo targets Python 3.9+.

## Project Expectations

- Target Python 3.10+ when possible, while preserving current runtime compatibility.
- Keep commands responsive. Avoid blocking I/O in command handlers.
- Treat database updates as stateful operations. For economy and farming changes, avoid race-prone read/modify/write patterns.
- Server-specific features must stay isolated per guild unless the behavior is explicitly global.
- Any feature that touches secrets, external APIs, or moderation behavior should include a short note in the PR description explaining the risk.

## Code Style

- Follow the existing module layout under `cogs/`.
- Use clear names and keep functions focused.
- Add comments only when the code is not obvious from the implementation.
- Reuse shared config and HTTP session handling instead of creating new global clients per cog.

## Pull Requests

Open a pull request with:

- A short summary of the problem
- The approach you took
- Any database or config changes
- Manual test steps
- Screenshots or command examples if user-facing behavior changed

Good PRs are narrow. Avoid mixing refactors, feature work, and formatting-only changes in one branch.

## Testing

There is no full automated test suite yet, so every PR should include manual verification.

At minimum:

- Run a syntax check:

```bash
python3 -m compileall .
```

- Exercise the changed slash commands in a test server.
- Verify that no secrets were added to tracked files.

## Security

Do not report security issues in public issues or pull requests. Follow [SECURITY.md](./SECURITY.md).
