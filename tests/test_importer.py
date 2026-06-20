# mango/tests/test_importer.py
from pathlib import Path
from mango.storage.db import Database
from mango.services.library import LibraryService
from mango.services.importer import LibraryImporter
from mango.library_models import ReadingStatus
from mango.models import Manga


class FakeSource:
    def __init__(self):
        self._statuses = {"m1": "reading", "m2": "dropped"}
        self._follows = ["m1", "m3"]  # m3 followed but no status
        self._manga = {
            "m1": Manga(id="m1", title="One"),
            "m2": Manga(id="m2", title="Two"),
            "m3": Manga(id="m3", title="Three"),
        }

    async def get_reading_statuses(self):
        return dict(self._statuses)

    async def get_follow_ids(self):
        return list(self._follows)

    async def get_manga_batch(self, ids):
        return [self._manga[i] for i in ids]

    def cover_url(self, manga, *, size=512):
        return f"cv/{manga.id}"


async def test_import_sorts_into_status_tabs(tmp_path: Path):
    db = Database(tmp_path / "lib.db")
    lib = LibraryService(db, cover_url_fn=lambda m: f"cv/{m.id}")
    importer = LibraryImporter(FakeSource(), lib)

    count = await importer.run()

    assert count == 3
    assert {e.manga_id for e in lib.list(ReadingStatus.READING)} == {"m1"}
    assert {e.manga_id for e in lib.list(ReadingStatus.DROPPED)} == {"m2"}
    # followed but statusless -> Plan To Read
    assert {e.manga_id for e in lib.list(ReadingStatus.PLAN_TO_READ)} == {"m3"}
    db.close()
