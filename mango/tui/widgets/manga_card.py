from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Vertical, Container
from textual.widgets import Static
from textual.events import Resize
from textual_image.widget import Image
from mango.library_models import LibraryEntry


class MangaCard(Vertical):
    """Uniform, responsive card: title -> cover -> description + progress.

    Every part has a fixed height so cards in the grid are the same size at a
    given width (no ragged layout). The cover slot reserves space so covers fill
    a consistent box as they load. When the card is too narrow the cover and
    description are dropped and only the title shows. Dimming of unselected cards
    is colour/border based (NOT opacity — terminal images vanish at <100%).
    """

    CELL_ASPECT = 2.0  # terminal cells are ~2x taller than wide

    DEFAULT_CSS = """
    MangaCard {
        width: 1fr;
        max-width: 30;
        height: auto;
        border: round $surface;
        padding: 1 1;
        margin: 1 1;
    }
    MangaCard.-selected { border: round $accent; }
    MangaCard > .card-title {
        height: 3; text-style: bold; color: $text-muted; overflow: hidden;
    }
    MangaCard.-selected > .card-title { color: $text; }
    MangaCard > #cover-slot { align: center middle; }
    MangaCard > .card-desc { height: 2; color: $text-muted; overflow: hidden; }
    MangaCard > .card-foot { height: 1; color: $accent; }
    """

    def __init__(self, entry: LibraryEntry) -> None:
        super().__init__()
        self.entry = entry
        self._pil = None
        self._img: Image | None = None

    def compose(self) -> ComposeResult:
        yield Static(self.entry.title, classes="card-title")
        yield Container(id="cover-slot")
        desc = (self.entry.description or "").replace("\n", " ")[:80]
        yield Static(desc, classes="card-desc")
        foot = f"ch {self.entry.last_chapter or '-'}"
        if self.entry.unread:
            foot += f"  ·{self.entry.unread} new"
        yield Static(foot, classes="card-foot")

    async def on_mount(self) -> None:
        url = self.entry.cover_url
        if url:
            self._pil = self.app.covers.cached(url) or await self.app.covers.get(url)
        await self._apply_cover()

    async def on_resize(self, event: Resize) -> None:
        await self._apply_cover()

    def _cover_height(self) -> int:
        """Uniform cover height in cells from the card's width (0 = title only)."""
        w = self.size.width
        if w >= 24:
            return 12
        if w >= 18:
            return 8
        if w >= 12:
            return 5
        return 0

    async def _apply_cover(self) -> None:
        h = self._cover_height()
        title_only = h <= 0
        # title-only mode hides description + footer
        for sel in (".card-desc", ".card-foot"):
            node = self.query(sel)
            if node:
                node.first().display = not title_only

        slot = self.query_one("#cover-slot", Container)
        # reserve a uniform box (0 collapses the slot in title-only mode)
        slot.styles.height = h if not title_only else 0

        if self._pil is None or title_only:
            if self._img is not None:
                await self._img.remove()
                self._img = None
            return

        ratio = self._pil.width / self._pil.height if self._pil.height else 0.7
        cw = max(1, round(h * ratio * self.CELL_ASPECT))
        cw = min(cw, max(1, self.size.width - 2))  # never wider than the card
        if self._img is None:
            self._img = Image(self._pil, classes="cover")
            await slot.mount(self._img)
        self._img.styles.width = cw
        self._img.styles.height = h
