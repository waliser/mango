# mango/tests/test_library_service.py
from pathlib import Path
from mango.storage.db import Database
from mango.services.library import LibraryService
from mango.library_models import ReadingStatus
from mango.models import Manga


def _svc(tmp_path: Path) -> LibraryService:
    return LibraryService(Database(tmp_path / "lib.db"), cover_url_fn=lambda m: f"cv/{m.id}")


def test_add_manga_defaults_to_plan_to_read(tmp_path: Path):
    svc = _svc(tmp_path)
    manga = Manga(id="m1", title="Alpha", description="d")
    svc.add(manga)
    plan = svc.list(ReadingStatus.PLAN_TO_READ)
    assert len(plan) == 1
    assert plan[0].title == "Alpha" and plan[0].cover_url == "cv/m1"


def test_set_status_moves_entry(tmp_path: Path):
    svc = _svc(tmp_path)
    svc.add(Manga(id="m1", title="Alpha"))
    svc.set_status("m1", ReadingStatus.READING)
    assert svc.list(ReadingStatus.PLAN_TO_READ) == []
    assert svc.list(ReadingStatus.READING)[0].manga_id == "m1"
