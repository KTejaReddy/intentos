"""IntentOS backend configuration.

Loads environment variables, wires the IntentLang compiler onto the import
path, and owns the on-disk data directory layout:

    DATA_DIR/
      settings.json          provider + IDE settings
      plugins.json           plugin enable state
      projects/<slug>/
        source/*.intentlang  user IntentLang sources
        generated/           compiler artifacts
        runtime/<name>.db    applied database for the DB viewer
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# -- compiler wiring -------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]          # repo root
COMPILER_DIR = ROOT_DIR / "compiler"
if str(COMPILER_DIR) not in sys.path:
    sys.path.insert(0, str(COMPILER_DIR))

VERSION = "1.0.0"

# -- data dir ---------------------------------------------------------------
DATA_DIR = Path(os.environ.get("INTENTOS_DATA_DIR", ROOT_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    "provider": "offline",          # offline | openrouter | ollama
    "api_key": "",
    "base_url": "http://localhost:11434",
    "model": "qwen2.5:7b",
    "openrouter_model": "qwen/qwen-2.5-72b-instruct",
    "cors_origins": ["http://localhost:7432", "http://127.0.0.1:7432"],
}

DEFAULT_PLUGIN_STATE = {
    "pwa": True,
    "seo": False,
}


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_settings() -> dict:
    settings = load_json(DATA_DIR / "settings.json", {})
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings)
    return merged


def save_settings(settings: dict) -> None:
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings)
    save_json(DATA_DIR / "settings.json", merged)


def get_plugin_state() -> dict:
    state = load_json(DATA_DIR / "plugins.json", {})
    merged = dict(DEFAULT_PLUGIN_STATE)
    merged.update(state)
    return merged


def save_plugin_state(state: dict) -> None:
    save_json(DATA_DIR / "plugins.json", state)


def project_root() -> Path:
    return ROOT_DIR
