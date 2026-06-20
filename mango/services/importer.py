from __future__ import annotations
from mango.library_models import ReadingStatus
from mango.services.library import LibraryService


class LibraryImporter:
    """One-way import of a MangaDex account's library into the local library.

    `source` must provide get_reading_statuses(), get_follow_ids(),
    get_manga_batch(ids) — satisfied by an authenticated MangaDexSource.
    """

    def __init__(self, source, library: LibraryService) -> None:
        self._source = source
        self._library = library

    async def run(self) -> int:
        statuses = await self._source.get_reading_statuses()
        follow_ids = await self._source.get_follow_ids()
        all_ids = list(dict.fromkeys([*statuses.keys(), *follow_ids]))
        if not all_ids:
            return 0
        manga = await self._source.get_manga_batch(all_ids)
        for m in manga:
            raw = statuses.get(m.id)
            status = ReadingStatus(raw) if raw else ReadingStatus.PLAN_TO_READ
            self._library.add(m, status)
        return len(manga)
