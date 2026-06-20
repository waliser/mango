# mango/mango/download_models.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadedManga:
    manga_id: str
    title: str
    cover_url: str | None = None


@dataclass(frozen=True)
class DownloadedChapter:
    chapter_id: str
    manga_id: str
    number: str                 # "12" or "12.5"
    title: str = ""
    language: str = "en"
    group: str = ""
    page_count: int = 0
    bytes: int = 0
    status: str = "complete"    # "complete" | "partial"
