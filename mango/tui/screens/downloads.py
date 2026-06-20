from __future__ import annotations
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Static, Footer
from mango.models import Manga, Chapter
from mango.services.downloads import human_bytes
from mango.tui.screens.chapters import flag


class DownloadsScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("enter", "open", "Read"),
        ("x", "delete", "Delete"),
        ("r", "redownload", "Re-download"),
    ]

    CSS = """
    #dl-header { height: 1; padding: 0 2; text-style: bold; color: $accent; }
    #downloads { height: 1fr; }
    .dl-empty { padding: 2 2; color: $text-muted; }
    """

    def __init__(self) -> None:
        super().__init__()
        # parallel to the ListView rows: (manga, chapters_of_series, index_in_series)
        self._rows: list[tuple[Manga, list[Chapter], int]] = []

    def compose(self) -> ComposeResult:
        yield Static("Downloads", id="dl-header")
        yield ListView(id="downloads")
        yield Footer()

    def on_screen_resume(self) -> None:
        self.run_worker(self._populate(), exclusive=True)

    async def _populate(self) -> None:
        lv = self.query_one("#downloads", ListView)
        await lv.clear()
        self._rows = []
        groups = self.app.downloads.list_library()
        if not groups:
            await lv.append(ListItem(Label(
                "No downloads yet. Press [b]d[/] on a chapter to download it.",
                classes="dl-empty")))
            return
        i = 0
        for dmanga, dchapters in groups:
            manga = Manga(id=dmanga.manga_id, title=dmanga.title)
            chapters = [
                Chapter(id=c.chapter_id, number=c.number, title=c.title,
                        language=c.language, group=c.group)
                for c in dchapters
            ]
            for j, (c, dc) in enumerate(zip(chapters, dchapters)):
                series = f"[b]{dmanga.title}[/]  " if j == 0 else "  "
                size = human_bytes(dc.bytes)
                partial = "  [$error]partial[/]" if dc.status != "complete" else ""
                title = f"Ch. {c.number}" + (f"  {c.title}" if c.title else "")
                label = (f"{series}{flag(c.language)}  {title}  "
                         f"[$text-muted]· {size}[/]{partial}")
                await lv.append(ListItem(Label(label), id=f"dl-{i}"))
                self._rows.append((manga, chapters, j))
                i += 1
        # Rows are appended after mount, so the ListView has no cursor yet;
        # highlight the first row so Enter/x/r act on it without a prior keypress.
        lv.index = 0
        lv.focus()

    def _selected(self) -> tuple[Manga, list[Chapter], int] | None:
        lv = self.query_one("#downloads", ListView)
        idx = lv.index
        if idx is None or not self._rows or idx >= len(self._rows):
            return None
        return self._rows[idx]

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        # ListView consumes Enter (posts Selected) before the screen's `enter`
        # binding can fire, so open from the Selected event instead.
        await self.action_open()

    async def action_open(self) -> None:
        sel = self._selected()
        if sel is None:
            return
        manga, chapters, j = sel
        reader = self.app.get_screen("reader")
        await self.app.push_screen("reader")
        await reader.load(manga, chapters, start_index=j)

    async def action_delete(self) -> None:
        sel = self._selected()
        if sel is None:
            return
        manga, chapters, j = sel
        ch = chapters[j]
        self.app.downloads.delete_chapter(manga.id, ch.id)
        self.notify(f"Deleted Ch. {ch.number}")
        await self._populate()

    async def action_redownload(self) -> None:
        sel = self._selected()
        if sel is None:
            return
        manga, chapters, j = sel
        ch = chapters[j]
        self.notify(f"Re-downloading Ch. {ch.number}…")
        try:
            pages = await self.app.source.get_pages(ch.id)
            rec = await self.app.downloads.download_chapter(manga, ch, pages)
        except Exception as exc:  # network/source failure — never crash the TUI
            self.notify(f"Re-download failed: {exc}", severity="error")
            return
        self.notify(f"Re-downloaded Ch. {ch.number} "
                    f"({rec.page_count} pages, {human_bytes(rec.bytes)})")
        await self._populate()
