# Headless integration tests for DownloadsScreen.
# DownloadsScreen renders only Labels (no textual-image Image), so unlike the
# Home/reader screens it runs fine under Textual's `run_test` harness. A stub
# "reader" screen records load() calls so we can assert navigation without
# rendering page images.
from pathlib import Path
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static
from mango.storage.db import Database
from mango.services.downloads import DownloadService
from mango.download_models import DownloadedManga, DownloadedChapter
from mango.tui.screens.downloads import DownloadsScreen


class FakeReader(Screen):
    """Stand-in for the real reader: records what it was asked to open."""
    def __init__(self) -> None:
        super().__init__()
        self.loaded = None

    def compose(self) -> ComposeResult:
        yield Static("")

    async def load(self, manga, chapters, start_index) -> None:
        self.loaded = (manga, chapters, start_index)


class DLApp(App):
    def __init__(self, db: Database, root: Path) -> None:
        super().__init__()
        self._db = db
        self._root = root
        self.fake_reader = FakeReader()

    def on_mount(self) -> None:
        self.downloads = DownloadService(self._db, None, root=self._root)
        self.install_screen(self.fake_reader, name="reader")
        self.install_screen(DownloadsScreen(), name="downloads")
        self.push_screen("downloads")


def _seed(db: Database) -> None:
    db.add_downloaded_manga(DownloadedManga("m1", "Alpha"))
    db.add_downloaded_chapter(DownloadedChapter(
        "c1", "m1", "1", title="Start", language="en", group="G",
        page_count=2, bytes=2048, status="complete"))


async def _wait_populated(pilot, screen) -> None:
    for _ in range(10):
        await pilot.pause()
        if screen._rows:
            return


async def test_downloads_screen_lists_and_enter_opens_reader(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    app = DLApp(db, tmp_path / "dl")
    async with app.run_test() as pilot:
        screen = app.screen
        assert isinstance(screen, DownloadsScreen)
        await _wait_populated(pilot, screen)
        assert len(screen._rows) == 1

        # Enter must open the reader. ListView consumes Enter via Selected, so
        # this exercises the on_list_view_selected -> action_open path.
        await pilot.press("enter")
        for _ in range(10):
            await pilot.pause()
            if app.fake_reader.loaded is not None:
                break
        assert app.fake_reader.loaded is not None
        manga, chapters, j = app.fake_reader.loaded
        assert manga.id == "m1"
        assert chapters[j].id == "c1"
    db.close()


async def test_downloads_screen_delete_removes_row(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    app = DLApp(db, tmp_path / "dl")
    async with app.run_test() as pilot:
        screen = app.screen
        await _wait_populated(pilot, screen)
        assert len(screen._rows) == 1

        await pilot.press("x")  # delete selected chapter
        for _ in range(10):
            await pilot.pause()
            if not screen._rows:
                break
        assert screen._rows == []
        assert db.list_downloaded_manga() == []  # last chapter gone -> series dropped
    db.close()
