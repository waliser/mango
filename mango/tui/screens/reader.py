from __future__ import annotations
import io
import asyncio
from pathlib import Path
import httpx
from PIL import Image as PILImage
from textual.screen import Screen
from textual.widgets import Static, Footer
from textual.containers import Container
from textual.app import ComposeResult
from textual_image.widget import Image
from mango.models import Manga, Chapter, Page


class ReaderScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("l", "next_page", "Next"),
        ("right", "next_page", "Next"),
        ("h", "prev_page", "Prev"),
        ("left", "prev_page", "Prev"),
        ("n", "next_chapter", "Next ch"),
        ("p", "prev_chapter", "Prev ch"),
        ("s", "toggle_saver", "Data-saver"),
    ]

    CELL_ASPECT = 2.0  # cells are ~2x taller than wide

    CSS = """
    #page-slot { width: 100%; height: 1fr; align: center middle; }
    #reader-status { dock: bottom; height: 1; color: $accent; background: $surface; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._cache: dict[str, bytes] = {}
        self._manga: Manga | None = None
        self._chapters: list[Chapter] = []
        self._chapter_idx = 0
        self._pages: list[Page] = []
        self._page_idx = 0
        self._data_saver = False

    def compose(self) -> ComposeResult:
        yield Container(id="page-slot")
        yield Static("", id="reader-status")
        yield Footer()

    async def load(self, manga: Manga, chapters: list[Chapter], start_index: int) -> None:
        self._manga = manga
        self._chapters = chapters
        self._chapter_idx = start_index
        await self._load_chapter()

    async def _load_chapter(self) -> None:
        ch = self._chapters[self._chapter_idx]
        if self.app.downloads.is_downloaded(ch.id):
            self._pages = self.app.downloads.local_pages(ch.id)
        else:
            self._pages = await self.app.source.get_pages(
                ch.id, data_saver=self._data_saver)
        self._page_idx = 0
        if self._manga is not None:  # mark this chapter read as soon as it's opened
            self.app.db.mark_chapter_read(self._manga.id, ch.id)
        await self._show_page()

    def _fit(self, pil, slot) -> tuple[int, int]:
        """Fit the page into the slot (cells) preserving aspect — no stretch."""
        sw = max(1, slot.size.width)
        sh = max(1, slot.size.height)
        ratio = pil.width / pil.height if pil.height else 0.7
        # image's cell-aspect (width/height in cells) = pixel ratio * cell aspect
        cell_ratio = ratio * self.CELL_ASPECT
        h = sh
        w = round(h * cell_ratio)
        if w > sw:
            w = sw
            h = round(w / cell_ratio)
        return max(1, w), max(1, h)

    async def _fetch(self, page: Page) -> bytes:
        if page.url not in self._cache:
            if "://" in page.url:  # remote page
                resp = await self.app.http_client.get(page.url)
                resp.raise_for_status()
                self._cache[page.url] = resp.content
            else:                  # downloaded page on disk
                self._cache[page.url] = Path(page.url).read_bytes()
        return self._cache[page.url]

    async def _show_page(self) -> None:
        slot = self.query_one("#page-slot", Container)
        status = self.query_one("#reader-status", Static)
        if not self._pages:
            await slot.remove_children()
            status.update("No pages in this chapter.")
            return
        page = self._pages[self._page_idx]
        try:
            data = await self._fetch(page)
            pil = PILImage.open(io.BytesIO(data))
        except (httpx.HTTPError, OSError) as exc:
            status.update(f"Failed to load page: {exc}")
            return
        await slot.remove_children()
        img = Image(pil, classes="page")
        cw, ch_cells = self._fit(pil, slot)
        img.styles.width = cw
        img.styles.height = ch_cells
        await slot.mount(img)
        ch = self._chapters[self._chapter_idx]
        status.update(
            f"{self._manga.title}  ch {ch.number}  page {self._page_idx + 1}/{len(self._pages)}"
        )
        self._prefetch()

    def _prefetch(self) -> None:
        for j in (self._page_idx + 1, self._page_idx + 2):
            if j < len(self._pages):
                asyncio.create_task(self._fetch(self._pages[j]))

    async def action_next_page(self) -> None:
        if self._page_idx + 1 < len(self._pages):
            self._page_idx += 1
            await self._show_page()
        else:
            await self.action_next_chapter()

    async def action_prev_page(self) -> None:
        if self._page_idx > 0:
            self._page_idx -= 1
            await self._show_page()

    async def action_next_chapter(self) -> None:
        if self._chapter_idx + 1 < len(self._chapters):
            self._chapter_idx += 1
            await self._load_chapter()

    async def action_prev_chapter(self) -> None:
        if self._chapter_idx > 0:
            self._chapter_idx -= 1
            await self._load_chapter()

    async def action_toggle_saver(self) -> None:
        self._data_saver = not self._data_saver
        self._cache.clear()
        await self._load_chapter()
