# mango/mango/services/library.py
from __future__ import annotations
from typing import Callable
from mango.models import Manga
from mango.storage.db import Database
from mango.library_models import ReadingStatus, LibraryEntry


class LibraryService:
    """Manages the local library. `cover_url_fn` resolves a Manga to a cover URL
    (provided by the active Source so the service stays source-agnostic)."""

    def __init__(self, db: Database, cover_url_fn: Callable[[Manga], str | None],
                 source_id: str = "mangadex") -> None:
        self._db = db
        self._cover_url_fn = cover_url_fn
        self._source_id = source_id

    def add(self, manga: Manga,
            status: ReadingStatus = ReadingStatus.PLAN_TO_READ) -> None:
        self._db.upsert_entry(LibraryEntry(
            manga_id=manga.id, source_id=self._source_id, title=manga.title,
            description=manga.description, cover_url=self._cover_url_fn(manga),
            status=status,
        ))

    def set_status(self, manga_id: str, status: ReadingStatus) -> None:
        e = self._db.get_entry(manga_id)
        if e is None:
            raise KeyError(f"manga_id {manga_id!r} not in library")
        self._db.upsert_entry(LibraryEntry(
            manga_id=e.manga_id, source_id=e.source_id, title=e.title,
            description=e.description, cover_url=e.cover_url, status=status,
            last_chapter=e.last_chapter, unread=e.unread,
        ))

    def set_progress(self, manga_id: str, last_chapter: str, unread: int = 0) -> None:
        self._db.set_progress(manga_id, last_chapter=last_chapter, unread=unread)

    def list(self, status: ReadingStatus) -> list[LibraryEntry]:
        return self._db.list_by_status(status)
