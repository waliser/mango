# mango/tests/test_db.py
from pathlib import Path
from mango.storage.db import Database
from mango.library_models import ReadingStatus, LibraryEntry


def _entry(mid="m1", status=ReadingStatus.READING, title="T1") -> LibraryEntry:
    return LibraryEntry(
        manga_id=mid, source_id="mangadex", title=title, description="d",
        cover_url="http://x/c.jpg", status=status,
    )


def test_read_chapter_tracking(tmp_path: Path):
    db = Database(tmp_path / "t.db")
    assert db.read_chapter_ids("m1") == set()
    db.mark_chapter_read("m1", "c1")
    db.mark_chapter_read("m1", "c2")
    db.mark_chapter_read("m1", "c1")  # idempotent
    assert db.read_chapter_ids("m1") == {"c1", "c2"}
    assert db.read_chapter_ids("m2") == set()
    db.close()


def test_upsert_and_list_by_status(tmp_path: Path):
    db = Database(tmp_path / "t.db")
    db.upsert_entry(_entry("m1", ReadingStatus.READING, "Alpha"))
    db.upsert_entry(_entry("m2", ReadingStatus.READING, "Beta"))
    db.upsert_entry(_entry("m3", ReadingStatus.DROPPED, "Gamma"))

    reading = db.list_by_status(ReadingStatus.READING)
    assert {e.manga_id for e in reading} == {"m1", "m2"}
    assert [e.title for e in reading] == ["Alpha", "Beta"]  # ordered by title
    assert {e.manga_id for e in db.list_by_status(ReadingStatus.DROPPED)} == {"m3"}

    # upsert again with a new status moves it
    db.upsert_entry(_entry("m1", ReadingStatus.COMPLETED, "Alpha"))
    assert {e.manga_id for e in db.list_by_status(ReadingStatus.READING)} == {"m2"}
    assert {e.manga_id for e in db.list_by_status(ReadingStatus.COMPLETED)} == {"m1"}
    db.close()


def test_set_progress(tmp_path: Path):
    db = Database(tmp_path / "t.db")
    db.upsert_entry(_entry("m1"))
    db.set_progress("m1", last_chapter="12", unread=3)
    e = db.list_by_status(ReadingStatus.READING)[0]
    assert e.last_chapter == "12" and e.unread == 3
    db.close()
