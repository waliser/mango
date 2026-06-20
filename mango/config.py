from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass


def _xdg(env: str, default: str) -> Path:
    return Path(os.environ.get(env, str(Path.home() / default)))


CONFIG_DIR = _xdg("XDG_CONFIG_HOME", ".config") / "mango"
DATA_DIR = _xdg("XDG_DATA_HOME", ".local/share") / "mango"
CACHE_DIR = _xdg("XDG_CACHE_HOME", ".cache") / "mango"
DOWNLOADS_DIR = DATA_DIR / "downloads"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


@dataclass
class Settings:
    language: str = "en"
    data_saver: bool = False


def ensure_dirs() -> None:
    for d in (CONFIG_DIR, DATA_DIR, CACHE_DIR, DOWNLOADS_DIR):
        d.mkdir(parents=True, exist_ok=True)
