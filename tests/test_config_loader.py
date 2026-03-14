import json

from config_loader import load_runtime_config


def test_load_runtime_config_prefers_env_over_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCORD_TOKEN", "env-token")
    monkeypatch.setenv("ALLOW_USER_KEYS", "false")
    monkeypatch.setenv("ALLOWED_CHAT_MODELS", "gpt-4o-mini,gpt-4o")

    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "DISCORD_TOKEN": "file-token",
                "ALLOW_USER_KEYS": True,
                "ALLOWED_CHAT_MODELS": ["file-model"],
            }
        ),
        encoding="utf-8",
    )

    config = load_runtime_config()

    assert config["DISCORD_TOKEN"] == "env-token"
    assert config["ALLOW_USER_KEYS"] is False
    assert config["ALLOWED_CHAT_MODELS"] == ["gpt-4o-mini", "gpt-4o"]


def test_load_runtime_config_falls_back_to_config_json(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in (
        "DISCORD_TOKEN",
        "OPENAI_API_KEY",
        "OPENAI_API_BASE",
        "ALLOW_USER_KEYS",
        "DEFAULT_CHAT_MODEL",
        "ALLOWED_CHAT_MODELS",
        "GOOGLE_API_KEY",
        "GOOGLE_CSE_ID",
    ):
        monkeypatch.delenv(key, raising=False)

    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "DISCORD_TOKEN": "file-token",
                "OPENAI_API_KEY": "openai-key",
                "OPENAI_API_BASE": "https://example.invalid/v1",
                "ALLOW_USER_KEYS": False,
                "DEFAULT_CHAT_MODEL": "gpt-test",
                "ALLOWED_CHAT_MODELS": ["gpt-test", "gpt-other"],
                "GOOGLE_API_KEY": "google-key",
                "GOOGLE_CSE_ID": "search-id",
            }
        ),
        encoding="utf-8",
    )

    config = load_runtime_config()

    assert config["DISCORD_TOKEN"] == "file-token"
    assert config["OPENAI_API_KEY"] == "openai-key"
    assert config["OPENAI_API_BASE"] == "https://example.invalid/v1"
    assert config["ALLOW_USER_KEYS"] is False
    assert config["DEFAULT_CHAT_MODEL"] == "gpt-test"
    assert config["ALLOWED_CHAT_MODELS"] == ["gpt-test", "gpt-other"]
    assert config["GOOGLE_API_KEY"] == "google-key"
    assert config["GOOGLE_CSE_ID"] == "search-id"
