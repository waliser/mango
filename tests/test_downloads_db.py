# mango/tests/test_downloads_db.py
from pathlib import Path
from mango.storage.db import Database
from mango.download_models import DownloadedManga, DownloadedChapter


def _ch(cid="c1", mid="m1", number="1", bytes_=100, status="complete") -> DownloadedChapter:
    return DownloadedChapter(
        chapter_id=cid, manga_id=mid, number=number, title=f"T{cid}",
        language="en", group="G", page_count=3, bytes=bytes_, status=status,
    )


def test_download_index_roundtrip(tmp_path: Path):
    db = Database(tmp_path / "t.db")
    assert db.list_downloaded_manga() == []
    assert db.downloaded_chapter_ids("m1") == set()
    assert db.downloaded_chapter("c1") is None

    db.add_downloaded_manga(DownloadedManga("m1", "Alpha", "cv/m1"))
    db.add_downloaded_chapter(_ch("c1", "m1", "1"))
    db.add_downloaded_chapter(_ch("c2", "m1", "2"))

    assert db.downloaded_chapter_ids("m1") == {"c1", "c2"}
    got = db.downloaded_chapter("c1")
    assert got is not None and got.number == "1" and got.bytes == 100
    assert [m.title for m in db.list_downloaded_manga()] == ["Alpha"]
    chs = db.list_downloaded_chapters("m1")
    assert [c.chapter_id for c in chs] == ["c1", "c2"]  # ordered by number
    db.close()


def test_download_index_upsert_and_delete(tmp_path: Path):
    db = Database(tmp_path / "t.db")
    db.add_downloaded_manga(DownloadedManga("m1", "Alpha"))
    db.add_downloaded_chapter(_ch("c1", "m1", "1", bytes_=100, status="partial"))
    # re-adding the same chapter updates it in place
    db.add_downloaded_chapter(_ch("c1", "m1", "1", bytes_=250, status="complete"))
    got = db.downloaded_chapter("c1")
    assert got.bytes == 250 and got.status == "complete"

    db.delete_downloaded_chapter("m1", "c1")
    assert db.downloaded_chapter("c1") is None
    assert db.downloaded_chapter_ids("m1") == set()

    db.delete_downloaded_manga("m1")
    assert db.list_downloaded_manga() == []
    db.close()
