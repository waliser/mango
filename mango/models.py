from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Manga:
    id: str
    title: str
    description: str = ""
    status: str = ""              # ongoing / completed / ...
    tags: tuple[str, ...] = ()
    cover_file_name: str | None = None
    content_rating: str = ""      # safe / suggestive / erotica
    rating: float | None = None   # bayesian rating (statistics endpoint)
    follows: int | None = None    # follow count (statistics endpoint)


@dataclass(frozen=True)
class Chapter:
    id: str
    number: str                   # "12" or "12.5"; chapters can be non-integer
    title: str = ""
    language: str = "en"
    group: str = ""


@dataclass(frozen=True)
class Page:
    url: str
    index: int                    # 0-based position within the chapter
