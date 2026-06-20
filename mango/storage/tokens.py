from __future__ import annotations
import os
import json
from pathlib import Path
from dataclasses import asdict
from mango.config import DATA_DIR
from mango.sources.mangadex.auth import AuthSession

DEFAULT_PATH = DATA_DIR / "auth.json"


def save_session(session: AuthSession, *, path: Path | None = None) -> None:
    p = path or DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(session)))
    os.chmod(p, 0o600)


def load_session(*, path: Path | None = None) -> AuthSession | None:
    p = path or DEFAULT_PATH
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    try:
        return AuthSession(**data)
    except TypeError:
        return None


def clear_session(*, path: Path | None = None) -> None:
    p = path or DEFAULT_PATH
    p.unlink(missing_ok=True)
