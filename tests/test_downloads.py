# mango/tests/test_downloads.py
import importlib
from pathlib import Path


def test_downloads_dir_under_data_and_created(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    import mango.config as config
    importlib.reload(config)  # re-evaluate module-level paths under patched env

    assert config.DOWNLOADS_DIR == config.DATA_DIR / "downloads"
    assert not config.DOWNLOADS_DIR.exists()
    config.ensure_dirs()
    assert config.DOWNLOADS_DIR.is_dir()
    importlib.reload(config)  # restore real paths for other tests


import pytest
from mango.services.downloads import human_bytes


@pytest.mark.parametrize("n,expected", [
    (0, "0 B"),
    (512, "512 B"),
    (1024, "1.0 KB"),
    (1536, "1.5 KB"),
    (1048576, "1.0 MB"),
    (5 * 1048576, "5.0 MB"),
    (1073741824, "1.0 GB"),
])
def test_human_bytes(n, expected):
    assert human_bytes(n) == expected


import httpx
import respx
from mango.models import Manga, Chapter, Page
from mango.storage.db import Database
from mango.services.downloads import DownloadService


def _manga() -> Manga:
    return Manga(id="m1", title="Alpha", cover_file_name="cov")


def _chapter() -> Chapter:
    return Chapter(id="c1", number="1", title="Start", language="en", group="G")


def _pages(base="https://cdn.test/data/h") -> list[Page]:
    return [
        Page(url=f"{base}/0-a.png", index=0),
        Page(url=f"{base}/1-b.jpg", index=1),
    ]


@respx.mock
async def test_download_chapter_writes_files_and_indexes(tmp_path):
    respx.get("https://cdn.test/data/h/0-a.png").mock(
        return_value=httpx.Response(200, content=b"PNGDATA"))
    respx.get("https://cdn.test/data/h/1-b.jpg").mock(
        return_value=httpx.Response(200, content=b"JPGDATA!!"))
    db = Database(tmp_path / "t.db")
    async with httpx.AsyncClient() as http:
        svc = DownloadService(db, http, root=tmp_path / "downloads")
        seen = []
        rec = await svc.download_chapter(
            _manga(), _chapter(), _pages(),
            progress=lambda done, total: seen.append((done, total)),
        )

    assert rec.status == "complete" and rec.page_count == 2
    assert rec.bytes == len(b"PNGDATA") + len(b"JPGDATA!!")
    cdir = (tmp_path / "downloads" / "m1" / "c1")
    assert (cdir / "000.png").read_bytes() == b"PNGDATA"
    assert (cdir / "001.jpg").read_bytes() == b"JPGDATA!!"
    assert svc.is_downloaded("c1") is True
    assert svc.downloaded_chapter_ids("m1") == {"c1"}
    assert seen[-1] == (2, 2)  # progress reported completion
    db.close()


@respx.mock
async def test_local_pages_returns_ordered_disk_paths(tmp_path):
    respx.get(url__regex=r"https://cdn\.test/.*").mock(
        return_value=httpx.Response(200, content=b"X"))
    db = Database(tmp_path / "t.db")
    async with httpx.AsyncClient() as http:
        svc = DownloadService(db, http, root=tmp_path / "downloads")
        await svc.download_chapter(_manga(), _chapter(), _pages())
        pages = svc.local_pages("c1")

    assert [p.index for p in pages] == [0, 1]
    assert pages[0].url.endswith("000.png") and "://" not in pages[0].url
    assert all(__import__("os").path.isfile(p.url) for p in pages)
    db.close()


@respx.mock
async def test_delete_chapter_removes_files_and_rows(tmp_path):
    respx.get(url__regex=r"https://cdn\.test/.*").mock(
        return_value=httpx.Response(200, content=b"X"))
    db = Database(tmp_path / "t.db")
    async with httpx.AsyncClient() as http:
        svc = DownloadService(db, http, root=tmp_path / "downloads")
        await svc.download_chapter(_manga(), _chapter(), _pages())
        svc.delete_chapter("m1", "c1")

    assert svc.is_downloaded("c1") is False
    assert not (tmp_path / "downloads" / "m1" / "c1").exists()
    # last chapter gone -> series row also dropped
    assert db.list_downloaded_manga() == []
    db.close()


@respx.mock
async def test_list_library_groups_chapters_by_series(tmp_path):
    respx.get(url__regex=r"https://cdn\.test/.*").mock(
        return_value=httpx.Response(200, content=b"X"))
    db = Database(tmp_path / "t.db")
    async with httpx.AsyncClient() as http:
        svc = DownloadService(db, http, root=tmp_path / "downloads")
        await svc.download_chapter(_manga(), _chapter(), _pages())
        await svc.download_chapter(
            _manga(), Chapter(id="c2", number="2"), _pages("https://cdn.test/data/h2"))
        groups = svc.list_library()

    assert len(groups) == 1
    manga, chapters = groups[0]
    assert manga.manga_id == "m1" and manga.title == "Alpha"
    assert [c.chapter_id for c in chapters] == ["c1", "c2"]
    db.close()


async def test_local_pages_missing_dir_returns_empty(tmp_path):
    # DB row exists but the files were removed on disk — must not raise.
    from mango.download_models import DownloadedManga, DownloadedChapter
    db = Database(tmp_path / "t.db")
    db.add_downloaded_manga(DownloadedManga("m1", "Alpha"))
    db.add_downloaded_chapter(DownloadedChapter(
        "c1", "m1", "1", page_count=2, bytes=10, status="complete"))
    async with httpx.AsyncClient() as http:
        svc = DownloadService(db, http, root=tmp_path / "downloads")
        assert svc.local_pages("c1") == []   # dir never created
        assert svc.local_pages("nope") == []  # unknown chapter
    db.close()
