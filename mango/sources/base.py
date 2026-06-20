from __future__ import annotations
from abc import ABC, abstractmethod
from mango.models import Manga, Chapter, Page


class Source(ABC):
    id: str
    name: str
    supports_auth: bool = False

    @abstractmethod
    async def search(self, query: str, *, limit: int = 20, offset: int = 0) -> list[Manga]: ...

    @abstractmethod
    async def get_chapters(self, manga_id: str, *, language: str = "en") -> list[Chapter]: ...

    @abstractmethod
    async def get_pages(self, chapter_id: str, *, data_saver: bool = False) -> list[Page]: ...

    @abstractmethod
    def cover_url(self, manga: Manga, *, size: int = 512) -> str | None: ...

    async def aclose(self) -> None:  # optional override
        return None


class Registry:
    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}

    def register(self, source: Source) -> None:
        self._sources[source.id] = source

    def get(self, source_id: str) -> Source:
        return self._sources[source_id]

    def all(self) -> list[Source]:
        return list(self._sources.values())
