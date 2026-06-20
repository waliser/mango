from __future__ import annotations
from textual.screen import Screen
from textual.widgets import Input, Footer, Static
from textual.containers import ScrollableContainer
from textual.app import ComposeResult
from mango.models import Manga
from mango.tui.widgets.search_result import SearchResultCard


class SearchScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("down", "down", "Down"),
        ("up", "up", "Up"),
        ("enter", "open", "Open"),
        ("a", "add", "Add to library"),
    ]

    CSS = """
    #q { margin: 1 1; }
    #status { height: 1; padding: 0 2; color: $text-muted; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._results: list[Manga] = []
        self._cards: list[SearchResultCard] = []
        self._sel = 0
        self._zone = "input"  # "input" (typing) or "list" (navigating results)

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search MangaDex…", id="q")
        yield Static("", id="status")
        yield ScrollableContainer(id="results")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        status = self.query_one("#status", Static)
        status.update("Searching…")
        self._results = await self.app.source.search(event.value)
        results = self.query_one("#results", ScrollableContainer)
        await results.remove_children()
        self._cards = []
        self._sel = 0
        self._zone = "input"
        for m in self._results:
            card = SearchResultCard(m)
            self._cards.append(card)
            await results.mount(card)
        status.update(f"{len(self._results)} results  ·  ↓ to browse")
        # preload thumbnails so they appear together
        urls = [self.app.source.cover_url(m, size=256) for m in self._results]
        self.run_worker(self.app.covers.preload(urls), exclusive=False)

    def _highlight(self) -> None:
        for i, card in enumerate(self._cards):
            card.set_class(self._zone == "list" and i == self._sel, "-selected")
        if self._zone == "list" and self._cards:
            self._cards[self._sel].scroll_visible()

    def action_down(self) -> None:
        if self._zone == "input":
            if self._cards:  # leave the input, start browsing results
                self._zone = "list"
                self._sel = 0
                self.set_focus(None)
                self._highlight()
        elif self._sel < len(self._cards) - 1:
            self._sel += 1
            self._highlight()

    def action_up(self) -> None:
        if self._zone != "list":
            return
        if self._sel == 0:  # back up into the search box
            self._zone = "input"
            self.query_one("#q", Input).focus()
            self._highlight()
        else:
            self._sel -= 1
            self._highlight()

    async def action_open(self) -> None:
        # Enter in the input box submits the search (handled by on_input_submitted);
        # this only fires when browsing the results list.
        if self._zone != "list" or not self._cards:
            return
        manga = self._cards[self._sel].manga
        chapters = await self.app.source.get_chapters(manga.id)
        if not chapters:
            self.query_one("#status", Static).update("No English chapters found.")
            return
        picker = self.app.get_screen("chapters")
        await self.app.push_screen("chapters")
        await picker.load(manga, chapters)

    def action_add(self) -> None:
        # only meaningful while browsing results (the input eats letter keys)
        if self._zone != "list" or not self._cards:
            return
        manga = self._cards[self._sel].manga
        self.app.library.add(manga)
        self.notify(f"Added “{manga.title}” to library.")
