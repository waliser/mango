from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static
from textual_image.widget import Image
from mango.models import Manga


class SearchResultCard(Horizontal):
    """A MangaDex-style search row: cover thumbnail + title, rating/follows,
    tags and a short description."""

    CELL_ASPECT = 2.0

    DEFAULT_CSS = """
    SearchResultCard {
        height: 7;
        width: 1fr;
        border: round $surface;
        padding: 0 1;
        margin: 0 1;
    }
    SearchResultCard.-selected { border: round $accent; }
    SearchResultCard > #thumb { width: 12; height: 1fr; align: center middle; }
    SearchResultCard > #info { width: 1fr; height: 1fr; padding: 0 1; }
    SearchResultCard .sr-title { height: 1; text-style: bold; color: $text; }
    SearchResultCard .sr-meta { height: 1; }
    SearchResultCard .sr-tags { height: 1; color: $secondary; }
    SearchResultCard .sr-desc { height: 1fr; color: $text-muted; }
    """

    # semantic colours (pastel)
    GOLD = "#e8cf8f"
    BOOKMARK = "#a7d3dd"
    RED = "#efb0b3"
    ORANGE = "#f1c89a"
    BLUE = "#acc7ef"
    STATUS_COLORS = {
        "ongoing": "#b6e0a3", "completed": "#acc7ef",
        "hiatus": "#f1c89a", "cancelled": "#efb0b3",
    }
    SENSITIVE_TAGS = {"sexual violence", "gore"}
    # powerline rounded caps for pill ends
    PILL_L = ""
    PILL_R = ""

    def __init__(self, manga: Manga) -> None:
        super().__init__()
        self.manga = manga
        self._img: Image | None = None

    def _meta_markup(self) -> str:
        m = self.manga
        rating = f"{m.rating:.2f}" if m.rating is not None else "N/A"
        follows = f"{m.follows:,}" if m.follows is not None else "N/A"
        parts = [f"[{self.GOLD}]★ {rating}[/]", f"[{self.BOOKMARK}]🔖 {follows}[/]"]
        if m.status:
            col = self.STATUS_COLORS.get(m.status.lower(), "$text-muted")
            parts.append(f"[{col}]{m.status.title()}[/]")
        return "   ".join(parts)

    def _tags_markup(self) -> str:
        """Overlapping/stacked pills: only the first pill has a left cap, every
        pill has a right cap, so each tucks behind the previous — (===)===)===).
        Special genres are their own coloured pills; the remaining genres form a
        final theme-coloured pill with dim `|` dividers between names."""
        m = self.manga
        colors = getattr(self.app, "mango_colors", {})
        base = colors.get("base", "#16131a")        # dark text on coloured pills
        surf = colors.get("surface2", "#373339")     # theme pill bg
        txt = colors.get("text", "#e8e0e8")          # theme pill text
        muted = colors.get("subtext1", "#958e98")    # faint divider
        cr = m.content_rating.lower()

        segs: list[tuple[str, str, str]] = []  # (inner_markup, bg, fg)
        if cr == "suggestive":
            segs.append(("Suggestive", self.ORANGE, base))
        elif cr in ("erotica", "pornographic"):
            segs.append((cr.title(), self.RED, base))

        special: set[str] = set()
        for t in m.tags:
            tl = t.lower()
            if tl == "award winning":
                segs.append((t, self.BLUE, base))
                special.add(tl)
            elif tl in self.SENSITIVE_TAGS:
                segs.append((t, self.RED, base))
                special.add(tl)

        normal = [t for t in m.tags if t.lower() not in special]
        if normal:
            inner = f" [{muted}]|[/] ".join(normal)  # dim divider, bg inherited
            segs.append((inner, surf, txt))
        if not segs:
            return ""

        out: list[str] = []
        for i, (inner, bg, fg) in enumerate(segs):
            if i == 0:
                out.append(f"[{bg}]{self.PILL_L}[/]")        # left cap only on first
            out.append(f"[{fg} on {bg}] {inner} [/]")
            # right cap in this pill's colour, but on the NEXT pill's background so
            # the rounded corner overlaps onto it (last pill rounds onto nothing)
            if i < len(segs) - 1:
                out.append(f"[{bg} on {segs[i + 1][1]}]{self.PILL_R}[/]")
            else:
                out.append(f"[{bg}]{self.PILL_R}[/]")
        return "".join(out)

    def compose(self) -> ComposeResult:
        m = self.manga
        desc = (m.description or "").replace("\n", " ")[:160]
        yield Container(id="thumb")
        with Vertical(id="info"):
            yield Static(m.title, classes="sr-title")
            yield Static(self._meta_markup(), classes="sr-meta")
            yield Static(self._tags_markup(), classes="sr-tags")
            yield Static(desc, classes="sr-desc")

    async def on_mount(self) -> None:
        url = self.app.source.cover_url(self.manga, size=256)
        if not url:
            return
        pil = self.app.covers.cached(url) or await self.app.covers.get(url)
        if pil is None:
            return
        h = 5
        ratio = pil.width / pil.height if pil.height else 0.7
        w = max(1, round(h * ratio * self.CELL_ASPECT))
        self._img = Image(pil)
        self._img.styles.width = w
        self._img.styles.height = h
        await self.query_one("#thumb", Container).mount(self._img)
