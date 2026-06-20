# mango/mango/tui/screens/library.py
from __future__ import annotations
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Footer, Tabs, Tab, Static
from mango.library_models import STATUS_ORDER, ReadingStatus
from mango.models import Manga
from mango.tui.widgets.manga_card import MangaCard

GRID_COLS = 4


class LibraryScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("r", "refresh", "Refresh"),
        ("up", "up", "Up"),
        ("down", "down", "Down"),
        ("left", "left", "Left"),
        ("right", "right", "Right"),
        ("k", "up", "Up"),
        ("j", "down", "Down"),
        ("h", "left", "Left"),
        ("l", "right", "Right"),
        ("enter", "open", "Read"),
        ("tab", "next_tab", "Next tab"),
        ("shift+tab", "prev_tab", "Prev tab"),
        ("]", "next_tab", "Next tab"),
        ("[", "prev_tab", "Prev tab"),
    ]

    CSS = """
    #grid { layout: grid; grid-size: 4; grid-rows: auto; }
    .empty { padding: 2 2; color: $text-muted; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._cards: list[MangaCard] = []
        self._sel = 0
        self._zone = "tabs"  # "tabs" (navigating status tabs) or "grid" (navigating cards)

    def compose(self) -> ComposeResult:
        yield Tabs(*[Tab(s.label, id=f"tab-{s.value}") for s in STATUS_ORDER])
        yield ScrollableContainer(id="grid")
        yield Footer()

    def on_mount(self) -> None:
        # keep focus off the Tabs so arrow keys drive card navigation, not tabs
        self.query_one(Tabs).can_focus = False
        self.set_focus(None)
        # preload every cover across all status tabs in the background so the
        # first paint and tab switches are instant (each cover fetched once)
        urls = [
            e.cover_url
            for s in STATUS_ORDER
            for e in self.app.library.list(s)
        ]
        self.run_worker(self.app.covers.preload(urls), exclusive=False)

    # Tabs activates its first tab on mount, firing on_tabs_tab_activated — that
    # event drives the initial load, so no on_mount refresh is needed.
    async def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        status = ReadingStatus(event.tab.id.removeprefix("tab-"))
        await self._refresh(status)

    def _switch_tab(self, step: int) -> None:
        tabs = self.query_one(Tabs)
        order = [f"tab-{s.value}" for s in STATUS_ORDER]
        cur = tabs.active or order[0]
        tabs.active = order[(order.index(cur) + step) % len(order)]

    def action_next_tab(self) -> None:
        self._switch_tab(1)

    def action_prev_tab(self) -> None:
        self._switch_tab(-1)

    @property
    def _current_status(self) -> ReadingStatus:
        active = self.query_one(Tabs).active_tab
        return ReadingStatus(active.id.removeprefix("tab-")) if active else STATUS_ORDER[0]

    async def _refresh(self, status: ReadingStatus | None = None) -> None:
        status = status or self._current_status
        grid = self.query_one("#grid", ScrollableContainer)
        await grid.remove_children()
        self._cards = []
        self._sel = 0
        self._zone = "tabs"  # switching tab returns navigation to the tab row
        entries = self.app.library.list(status)
        if not entries:
            await grid.mount(Static(f"No titles in {status.label}.", classes="empty"))
            return
        for entry in entries:
            card = MangaCard(entry)
            self._cards.append(card)
            await grid.mount(card)
        self.set_focus(None)  # screen handles arrow keys, not the Tabs/grid
        self._highlight()

    def _highlight(self) -> None:
        # a card is only highlighted while navigating the grid
        for i, card in enumerate(self._cards):
            card.set_class(self._zone == "grid" and i == self._sel, "-selected")
        if self._zone == "grid" and self._cards:
            self._cards[self._sel].scroll_visible()

    def action_left(self) -> None:
        if self._zone == "tabs":
            self._switch_tab(-1)
        elif self._cards and self._sel > 0:
            self._sel -= 1
            self._highlight()

    def action_right(self) -> None:
        if self._zone == "tabs":
            self._switch_tab(1)
        elif self._cards and self._sel < len(self._cards) - 1:
            self._sel += 1
            self._highlight()

    def action_down(self) -> None:
        if self._zone == "tabs":
            if self._cards:  # drop into the grid at the first card
                self._zone = "grid"
                self._sel = 0
                self._highlight()
        else:
            new = self._sel + GRID_COLS
            if new < len(self._cards):
                self._sel = new
                self._highlight()

    def action_up(self) -> None:
        if self._zone != "grid":
            return
        if self._sel < GRID_COLS:  # top row -> back up to the tabs
            self._zone = "tabs"
            self._highlight()
        else:
            self._sel -= GRID_COLS
            self._highlight()

    async def action_open(self) -> None:
        if self._zone != "grid" or not self._cards:
            return
        entry = self._cards[self._sel].entry
        chapters = await self.app.source.get_chapters(entry.manga_id)
        if not chapters:
            self.notify("No English chapters found.", severity="warning")
            return
        manga = Manga(id=entry.manga_id, title=entry.title, description=entry.description)
        picker = self.app.get_screen("chapters")
        await self.app.push_screen("chapters")
        await picker.load(manga, chapters)

    async def action_refresh(self) -> None:
        await self._refresh()
