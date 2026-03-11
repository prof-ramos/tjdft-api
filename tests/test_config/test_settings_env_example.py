"""Tests to keep .env.example aligned with Settings fields."""

from pathlib import Path

import pytest

from app.config import Settings

pytestmark = pytest.mark.unit


def _read_env_keys(env_path: Path) -> set[str]:
    keys: set[str] = set()
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _ = line.split("=", 1)
        keys.add(key.strip())
    return keys


def test_env_example_matches_settings_fields():
    env_path = Path(".env.example")
    env_keys = _read_env_keys(env_path)
    settings_keys = {field_name.upper() for field_name in Settings.model_fields}

    missing_in_example = settings_keys - env_keys
    extra_in_example = env_keys - settings_keys

    assert not missing_in_example, "Missing keys in .env.example: " + ", ".join(
        sorted(missing_in_example)
    )
    assert (
        not extra_in_example
    ), "Unknown keys in .env.example (not in Settings): " + ", ".join(
        sorted(extra_in_example)
    )
