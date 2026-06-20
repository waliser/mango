from __future__ import annotations
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Static, Footer
from mango.models import Manga, Chapter

# language code -> flag emoji (fallback: the code in brackets)
_FLAGS = {
    "en": "🇬🇧", "ja": "🇯🇵", "ko": "🇰🇷", "zh": "🇨🇳", "zh-hk": "🇭🇰",
    "es": "🇪🇸", "es-la": "🇲🇽", "pt-br": "🇧🇷", "pt": "🇵🇹", "fr": "🇫🇷",
    "de": "🇩🇪", "it": "🇮🇹", "ru": "🇷🇺", "id": "🇮🇩", "vi": "🇻🇳",
    "th": "🇹🇭", "ar": "🇸🇦", "pl": "🇵🇱", "tr": "🇹🇷",
}


def flag(lang: str) -> str:
    return _FLAGS.get(lang.lower(), f"[{lang}]")


class ChapterListScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back"), ("d", "download", "Download")]

    CSS = """
    #ch-header { height: 1; padding: 0 2; text-style: bold; color: $accent; }
    #chapters { height: 1fr; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._manga: Manga | None = None
        self._chapters: list[Chapter] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="ch-header")
        yield ListView(id="chapters")
        yield Footer()

    async def load(self, manga: Manga, chapters: list[Chapter]) -> None:
        self._manga = manga
        self._chapters = chapters
        self.query_one("#ch-header", Static).update(manga.title)
        read = self.app.db.read_chapter_ids(manga.id)
        # chapter_id -> "complete" | "partial", so the marker reflects real state
        dl_status = {c.chapter_id: c.status
                     for c in self.app.db.list_downloaded_chapters(manga.id)}
        lv = self.query_one("#chapters", ListView)
        await lv.clear()
        for i, ch in enumerate(chapters):
            mark = "[$success]●[/]" if ch.id in read else "[$text-muted]○[/]"
            title = f"Ch. {ch.number}"
            if ch.title:
                title += f"  {ch.title}"
            group = f"  [$text-muted]· {ch.group}[/]" if ch.group else ""
            st = dl_status.get(ch.id)
            dl = ("[$success]⭳[/] " if st == "complete"
                  else "[$warning]⭳[/] " if st else "")
            label = f"{mark} {dl} {flag(ch.language)}  {title}{group}"
            await lv.append(ListItem(Label(label), id=f"ch-{i}"))
        # Highlight the first row so `d` (download) acts on it without a prior
        # keypress — items appended after mount leave the cursor unset.
        if chapters:
            lv.index = 0
        lv.focus()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = int(event.item.id.removeprefix("ch-"))
        reader = self.app.get_screen("reader")
        await self.app.push_screen("reader")
        await reader.load(self._manga, self._chapters, start_index=idx)

    async def action_download(self) -> None:
        lv = self.query_one("#chapters", ListView)
        idx = lv.index
        if idx is None or self._manga is None:
            return
        ch = self._chapters[idx]
        if self.app.downloads.is_downloaded(ch.id):
            self.notify(f"Ch. {ch.number} already downloaded")
            return
        self.notify(f"Downloading Ch. {ch.number}…")
        try:
            pages = await self.app.source.get_pages(ch.id)
            rec = await self.app.downloads.download_chapter(self._manga, ch, pages)
        except Exception as exc:  # never crash the TUI on a network/source error
            self.notify(f"Download failed: {exc}", severity="error")
            return
        from mango.services.downloads import human_bytes
        self.notify(f"Downloaded Ch. {ch.number} "
                    f"({rec.page_count} pages, {human_bytes(rec.bytes)})")
        await self.load(self._manga, self._chapters)  # refresh markers
