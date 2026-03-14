import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


CONFIG_PATH = Path("config.json")
DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_ALLOWED_MODELS = [DEFAULT_CHAT_MODEL, "gpt-4o"]


def _load_file_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}

    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _get_bool(name: str, default: bool, file_config: dict[str, Any]) -> bool:
    value = os.getenv(name)
    if value is None:
        value = file_config.get(name, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}

    return bool(value)


def _get_list(name: str, default: list[str], file_config: dict[str, Any]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        value = file_config.get(name, default)

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    return list(default)


def load_runtime_config() -> dict[str, Any]:
    load_dotenv()
    file_config = _load_file_config()

    return {
        "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN", file_config.get("DISCORD_TOKEN", "")),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", file_config.get("OPENAI_API_KEY", "")),
        "OPENAI_API_BASE": os.getenv("OPENAI_API_BASE", file_config.get("OPENAI_API_BASE", DEFAULT_API_BASE)),
        "ALLOW_USER_KEYS": _get_bool("ALLOW_USER_KEYS", True, file_config),
        "DEFAULT_CHAT_MODEL": os.getenv(
            "DEFAULT_CHAT_MODEL", file_config.get("DEFAULT_CHAT_MODEL", DEFAULT_CHAT_MODEL)
        ),
        "ALLOWED_CHAT_MODELS": _get_list("ALLOWED_CHAT_MODELS", DEFAULT_ALLOWED_MODELS, file_config),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", file_config.get("GOOGLE_API_KEY", "")),
        "GOOGLE_CSE_ID": os.getenv("GOOGLE_CSE_ID", file_config.get("GOOGLE_CSE_ID", "")),
    }
