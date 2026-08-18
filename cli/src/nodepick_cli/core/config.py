import os
import json
import keyring
from pathlib import Path
from typing import Optional, Dict, Any

CONFIG_DIR = Path.home() / ".nodepick"
CONFIG_FILE = CONFIG_DIR / "config.json"

KEYRING_SERVICE = "nodepick-cli"
KEYRING_API_KEY  = "api_key"

_base_url_override: Optional[str] = None


def set_base_url_override(url: Optional[str]) -> None:
    global _base_url_override
    _base_url_override = url.rstrip("/") if url else None


def get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        os.chmod(CONFIG_FILE, 0o600)
    return CONFIG_DIR


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    os.chmod(CONFIG_FILE, 0o600)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: Dict[str, Any]) -> None:
    get_config_dir()
    config = load_config()
    config.update(data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)


def _keyring_get(key_name: str) -> Optional[str]:
    try:
        return keyring.get_password(KEYRING_SERVICE, key_name) or None
    except Exception:
        return None


def get_api_key(override: Optional[str] = None) -> Optional[str]:
    if override:
        return override
    # 1. Environment variable
    env_key = os.getenv("NODEPICK_API_KEY")
    if env_key:
        return env_key
    # 2. OS keyring (set via 'np auth configure')
    return _keyring_get(KEYRING_API_KEY)


def get_base_url() -> str:
    if _base_url_override:
        return _base_url_override
    # 1. Environment variable
    env_url = os.getenv("NODEPICK_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    # 2. Config file
    return load_config().get("base_url", "https://api.nodepick.ai").rstrip("/")
