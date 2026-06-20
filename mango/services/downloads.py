from __future__ import annotations
import shutil
from pathlib import Path
from urllib.parse import urlparse
from typing import Callable
import httpx
from mango.config import DOWNLOADS_DIR
from mango.models import Manga, Chapter, Page
from mango.storage.db import Database
from mango.download_models import DownloadedManga, DownloadedChapter


def human_bytes(n: int) -> str:
    """Compact human-readable size: bytes as integer, KB/MB/GB to one decimal."""
    if n < 1024:
        return f"{n} B"
    size = float(n)
    for unit in ("KB", "MB", "GB", "TB"):
        size /= 1024
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
    return f"{size:.1f} TB"  # pragma: no cover - loop always returns first


def _suffix(url: str) -> str:
    return Path(urlparse(url).path).suffix or ".jpg"


class DownloadService:
    """Saves chapter pages to disk and indexes them for offline reading.

    Source-agnostic: callers resolve `pages` from the active Source and pass
    them in (mirroring how LibraryService takes cover_url_fn). The shared
    httpx client is reused so the rate limiter / connection pool are shared.
    """

    def __init__(self, db: Database, http: httpx.AsyncClient,
                 root: Path = DOWNLOADS_DIR) -> None:
        self._db = db
        self._http = http
        self._root = Path(root)

    def chapter_dir(self, manga_id: str, chapter_id: str) -> Path:
        return self._root / manga_id / chapter_id

    def is_downloaded(self, chapter_id: str) -> bool:
        rec = self._db.downloaded_chapter(chapter_id)
        return rec is not None and rec.status == "complete"

    def downloaded_chapter_ids(self, manga_id: str) -> set[str]:
        return self._db.downloaded_chapter_ids(manga_id)

    async def download_chapter(
        self, manga: Manga, chapter: Chapter, pages: list[Page], *,
        progress: Callable[[int, int], None] | None = None,
    ) -> DownloadedChapter:
        total = len(pages)
        cdir = self.chapter_dir(manga.id, chapter.id)
        cdir.mkdir(parents=True, exist_ok=True)
        written = 0
        status = "complete"
        try:
            for page in pages:
                dest = cdir / f"{page.index:03d}{_suffix(page.url)}"
                resp = await self._http.get(page.url)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                written += len(resp.content)
                if progress is not None:
                    progress(page.index + 1, total)
        except (httpx.HTTPError, OSError):
            status = "partial"
        rec = DownloadedChapter(
            chapter_id=chapter.id, manga_id=manga.id, number=chapter.number,
            title=chapter.title, language=chapter.language, group=chapter.group,
            page_count=total, bytes=written, status=status,
        )
        self._db.add_downloaded_manga(DownloadedManga(manga.id, manga.title))
        self._db.add_downloaded_chapter(rec)
        return rec

    def local_pages(self, chapter_id: str) -> list[Page]:
        rec = self._db.downloaded_chapter(chapter_id)
        if rec is None:
            return []
        cdir = self.chapter_dir(rec.manga_id, chapter_id)
        if not cdir.is_dir():  # files removed on disk while the DB row remains
            return []
        files = sorted(p for p in cdir.iterdir() if p.is_file())
        return [Page(url=str(p), index=i) for i, p in enumerate(files)]

    def delete_chapter(self, manga_id: str, chapter_id: str) -> None:
        shutil.rmtree(self.chapter_dir(manga_id, chapter_id), ignore_errors=True)
        self._db.delete_downloaded_chapter(manga_id, chapter_id)
        if not self._db.downloaded_chapter_ids(manga_id):
            self._db.delete_downloaded_manga(manga_id)

    def list_library(self) -> list[tuple[DownloadedManga, list[DownloadedChapter]]]:
        return [
            (m, self._db.list_downloaded_chapters(m.manga_id))
            for m in self._db.list_downloaded_manga()
        ]
