# mango/tests/test_tokens.py
import stat
from pathlib import Path
from mango.sources.mangadex.auth import AuthSession
from mango.storage import tokens


def test_save_load_clear_roundtrip(tmp_path: Path):
    p = tmp_path / "auth.json"
    s = AuthSession("AT", "RT", "cid", "sec", expires_at=123.0)
    tokens.save_session(s, path=p)
    loaded = tokens.load_session(path=p)
    assert loaded == s
    # file is private (0600)
    assert stat.S_IMODE(p.stat().st_mode) == 0o600
    tokens.clear_session(path=p)
    assert tokens.load_session(path=p) is None


def test_load_missing_returns_none(tmp_path: Path):
    assert tokens.load_session(path=tmp_path / "nope.json") is None
