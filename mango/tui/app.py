from __future__ import annotations
import httpx
from textual.app import App
from mango.config import ensure_dirs, DATA_DIR
from mango.sources.base import Registry
from mango.sources.mangadex.source import MangaDexSource
from mango.tui.screens.home import HomeScreen
from mango.tui.screens.search import SearchScreen
from mango.tui.screens.reader import ReaderScreen
from mango.storage.db import Database
from mango.services.library import LibraryService
from mango.services.covers import CoverCache
from mango.tui.screens.library import LibraryScreen
from mango.tui.screens.login import LoginScreen
from mango.tui.screens.chapters import ChapterListScreen
from mango.services.downloads import DownloadService
from mango.tui.screens.downloads import DownloadsScreen
from mango.theme import load_matugen_colors, build_theme


class MangoApp(App):
    CSS = """
    #home { height: 100%; }
    /* header: MANGO locked to screen centre (base layer); maid floats on a
       separate layer, offset left, so it never shifts the wordmark. */
    #header { width: 100%; height: 10; margin-top: 2; layers: base front;
              align: center middle; }
    #banner { layer: base; color: $accent; content-align: center middle;
              width: auto; height: auto; }
    #maid-slot { layer: front; width: 14; height: 8; offset: -32 0; }
    #maid { width: 100%; height: 100%; }
    /* menu block centred horizontally, anchored near the top of the area so the
       first item never clips at small window heights (offset-from-centre did) */
    #menu-wrap { width: 100%; height: 1fr; align: center top; }
    #menu { width: 18; height: auto; margin-top: 2; background: transparent;
            border: none; padding: 0; }
    #menu > ListItem { width: 100%; background: transparent; padding: 0; color: $foreground; }
    #menu > ListItem.-highlight { background: transparent; color: $foreground; text-style: none; }
    .menu-label { width: 100%; text-align: left; }
    """

    def __init__(self) -> None:
        super().__init__()
        ensure_dirs()
        self.registry = Registry()
        self.registry.register(MangaDexSource())
        self.source = self.registry.get("mangadex")
        self.db = Database(DATA_DIR / "mango.db")
        self.library = LibraryService(self.db, cover_url_fn=self.source.cover_url)
        self.http_client = httpx.AsyncClient(timeout=20.0)
        self.covers = CoverCache(self.http_client)
        self.downloads = DownloadService(self.db, self.http_client)
        # matugen palette: read once at launch so the UI follows the active profile
        self.mango_colors = load_matugen_colors()

    def on_mount(self) -> None:
        theme = build_theme(self.mango_colors)
        self.register_theme(theme)
        self.theme = theme.name
        self.install_screen(SearchScreen(), name="search")
        self.install_screen(ReaderScreen(), name="reader")
        self.install_screen(LibraryScreen(), name="library")
        self.install_screen(LoginScreen(), name="login")
        self.install_screen(ChapterListScreen(), name="chapters")
        self.install_screen(DownloadsScreen(), name="downloads")
        self.push_screen(HomeScreen())

    async def on_unmount(self) -> None:
        await self.source.aclose()
        await self.http_client.aclose()
        self.db.close()
