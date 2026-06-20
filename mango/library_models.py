# mango/mango/library_models.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ReadingStatus(str, Enum):
    READING = "reading"
    PLAN_TO_READ = "plan_to_read"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    RE_READING = "re_reading"
    DROPPED = "dropped"

    @property
    def label(self) -> str:
        return {
            "reading": "Reading",
            "plan_to_read": "Plan To Read",
            "completed": "Completed",
            "on_hold": "On Hold",
            "re_reading": "Re-reading",
            "dropped": "Dropped",
        }[self.value]


# Tab order shown in the LibraryScreen
STATUS_ORDER: tuple[ReadingStatus, ...] = (
    ReadingStatus.READING,
    ReadingStatus.PLAN_TO_READ,
    ReadingStatus.COMPLETED,
    ReadingStatus.ON_HOLD,
    ReadingStatus.RE_READING,
    ReadingStatus.DROPPED,
)


@dataclass(frozen=True)
class LibraryEntry:
    manga_id: str
    source_id: str
    title: str
    description: str
    cover_url: str | None
    status: ReadingStatus
    last_chapter: str = ""   # last chapter number read, e.g. "34"
    unread: int = 0          # count of unread chapters (0 if unknown)
