# mango/mango/storage/db.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from mango.library_models import ReadingStatus, LibraryEntry
from mango.download_models import DownloadedManga, DownloadedChapter

SCHEMA = """
CREATE TABLE IF NOT EXISTS library (
    manga_id    TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    cover_url   TEXT,
    status      TEXT NOT NULL,
    last_chapter TEXT NOT NULL DEFAULT '',
    unread      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS read_chapters (
    manga_id   TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    PRIMARY KEY (manga_id, chapter_id)
);
CREATE TABLE IF NOT EXISTS downloaded_manga (
    manga_id  TEXT PRIMARY KEY,
    title     TEXT NOT NULL,
    cover_url TEXT
);
CREATE TABLE IF NOT EXISTS downloaded_chapters (
    chapter_id TEXT PRIMARY KEY,
    manga_id   TEXT NOT NULL,
    number     TEXT NOT NULL,
    title      TEXT NOT NULL DEFAULT '',
    language   TEXT NOT NULL DEFAULT 'en',
    group_name TEXT NOT NULL DEFAULT '',
    page_count INTEGER NOT NULL DEFAULT 0,
    bytes      INTEGER NOT NULL DEFAULT 0,
    status     TEXT NOT NULL DEFAULT 'complete'
);
"""


class Database:
    def __init__(self, path: Path | str) -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def upsert_entry(self, e: LibraryEntry) -> None:
        self._conn.execute(
            """
            INSERT INTO library
                (manga_id, source_id, title, description, cover_url, status,
                 last_chapter, unread)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(manga_id) DO UPDATE SET
                source_id=excluded.source_id, title=excluded.title,
                description=excluded.description, cover_url=excluded.cover_url,
                status=excluded.status
            """,
            (e.manga_id, e.source_id, e.title, e.description, e.cover_url,
             e.status.value, e.last_chapter, e.unread),
        )
        self._conn.commit()

    def set_progress(self, manga_id: str, *, last_chapter: str, unread: int) -> None:
        cur = self._conn.execute(
            "UPDATE library SET last_chapter=?, unread=? WHERE manga_id=?",
            (last_chapter, unread, manga_id),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            raise KeyError(f"manga_id {manga_id!r} not in library")

    def get_entry(self, manga_id: str) -> LibraryEntry | None:
        row = self._conn.execute(
            "SELECT * FROM library WHERE manga_id=?", (manga_id,)
        ).fetchone()
        return self._row(row) if row else None

    def list_by_status(self, status: ReadingStatus) -> list[LibraryEntry]:
        rows = self._conn.execute(
            "SELECT * FROM library WHERE status=? ORDER BY title COLLATE NOCASE",
            (status.value,),
        ).fetchall()
        return [self._row(r) for r in rows]

    def mark_chapter_read(self, manga_id: str, chapter_id: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO read_chapters (manga_id, chapter_id) VALUES (?, ?)",
            (manga_id, chapter_id),
        )
        self._conn.commit()

    def read_chapter_ids(self, manga_id: str) -> set[str]:
        rows = self._conn.execute(
            "SELECT chapter_id FROM read_chapters WHERE manga_id=?", (manga_id,)
        ).fetchall()
        return {r["chapter_id"] for r in rows}

    # --- download index -------------------------------------------------
    def add_downloaded_manga(self, m: DownloadedManga) -> None:
        self._conn.execute(
            """
            INSERT INTO downloaded_manga (manga_id, title, cover_url)
            VALUES (?, ?, ?)
            ON CONFLICT(manga_id) DO UPDATE SET
                title=excluded.title, cover_url=excluded.cover_url
            """,
            (m.manga_id, m.title, m.cover_url),
        )
        self._conn.commit()

    def add_downloaded_chapter(self, c: DownloadedChapter) -> None:
        self._conn.execute(
            """
            INSERT INTO downloaded_chapters
                (chapter_id, manga_id, number, title, language, group_name,
                 page_count, bytes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chapter_id) DO UPDATE SET
                manga_id=excluded.manga_id, number=excluded.number,
                title=excluded.title, language=excluded.language,
                group_name=excluded.group_name, page_count=excluded.page_count,
                bytes=excluded.bytes, status=excluded.status
            """,
            (c.chapter_id, c.manga_id, c.number, c.title, c.language, c.group,
             c.page_count, c.bytes, c.status),
        )
        self._conn.commit()

    def downloaded_chapter(self, chapter_id: str) -> DownloadedChapter | None:
        r = self._conn.execute(
            "SELECT * FROM downloaded_chapters WHERE chapter_id=?", (chapter_id,)
        ).fetchone()
        return self._dl_chapter(r) if r else None

    def downloaded_chapter_ids(self, manga_id: str) -> set[str]:
        rows = self._conn.execute(
            "SELECT chapter_id FROM downloaded_chapters WHERE manga_id=?", (manga_id,)
        ).fetchall()
        return {r["chapter_id"] for r in rows}

    def list_downloaded_manga(self) -> list[DownloadedManga]:
        rows = self._conn.execute(
            "SELECT * FROM downloaded_manga ORDER BY title COLLATE NOCASE"
        ).fetchall()
        return [DownloadedManga(r["manga_id"], r["title"], r["cover_url"]) for r in rows]

    def list_downloaded_chapters(self, manga_id: str) -> list[DownloadedChapter]:
        rows = self._conn.execute(
            "SELECT * FROM downloaded_chapters WHERE manga_id=? "
            "ORDER BY CAST(number AS REAL), number",
            (manga_id,),
        ).fetchall()
        return [self._dl_chapter(r) for r in rows]

    def delete_downloaded_chapter(self, manga_id: str, chapter_id: str) -> None:
        self._conn.execute(
            "DELETE FROM downloaded_chapters WHERE manga_id=? AND chapter_id=?",
            (manga_id, chapter_id),
        )
        self._conn.commit()

    def delete_downloaded_manga(self, manga_id: str) -> None:
        self._conn.execute("DELETE FROM downloaded_chapters WHERE manga_id=?", (manga_id,))
        self._conn.execute("DELETE FROM downloaded_manga WHERE manga_id=?", (manga_id,))
        self._conn.commit()

    def _dl_chapter(self, r) -> DownloadedChapter:
        return DownloadedChapter(
            chapter_id=r["chapter_id"], manga_id=r["manga_id"], number=r["number"],
            title=r["title"], language=r["language"], group=r["group_name"],
            page_count=r["page_count"], bytes=r["bytes"], status=r["status"],
        )

    def _row(self, r: sqlite3.Row) -> LibraryEntry:
        return LibraryEntry(
            manga_id=r["manga_id"], source_id=r["source_id"], title=r["title"],
            description=r["description"], cover_url=r["cover_url"],
            status=ReadingStatus(r["status"]), last_chapter=r["last_chapter"],
            unread=r["unread"],
        )

    def close(self) -> None:
        self._conn.close()
