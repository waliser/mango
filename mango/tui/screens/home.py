from __future__ import annotations
from textual.screen import Screen
from textual.widgets import Static, ListView, ListItem, Label, Footer
from textual.containers import Vertical, Container
from textual.app import ComposeResult
from textual_image.widget import Image
from PIL import Image as PILImage
from mango.config import ASSETS_DIR

MAID_PATH = ASSETS_DIR / "maid.png"


def _load_maid() -> PILImage.Image | None:
    """Load the maid art and crop away fully-transparent margins (alpha bbox),
    so any clean cut-out drops in tight. Cropping preserves the content's
    aspect ratio; textual-image then fits it without stretching."""
    try:
        img = PILImage.open(MAID_PATH).convert("RGBA")
    except (OSError, ValueError):
        return None
    bbox = img.getchannel("A").getbbox()  # bounds of non-transparent pixels
    return img.crop(bbox) if bbox else img

BANNER = r"""
 ███╗   ███╗ █████╗ ███╗   ██╗ ██████╗  ██████╗
 ████╗ ████║██╔══██╗████╗  ██║██╔════╝ ██╔═══██╗
 ██╔████╔██║███████║██╔██╗ ██║██║  ███╗██║   ██║
 ██║╚██╔╝██║██╔══██║██║╚██╗██║██║   ██║██║   ██║
 ██║ ╚═╝ ██║██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝
 ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝
"""

# (label, nerd-font glyph, matugen color role) — glyph is tinted per item.
MENU = [
    ("Search", "", "blue"),      # nf-fa-search       (primary)
    ("Library", "", "green"),    # nf-fa-book         (secondary)
    ("Downloads", "", "peach"),  # nf-fa-download     (tertiary)
    ("Login", "", "blue"),  # nf-fa-sign_in      (primary)
    ("Exit", "", "red"),         # nf-fa-sign_out     (error)
]


class HomeScreen(Screen):
    BINDINGS = [("q", "app.quit", "Quit")]

    def compose(self) -> ComposeResult:
        self._labels: list[Label] = []
        items = []
        for i, (name, glyph, role) in enumerate(MENU):
            label = Label(self._markup(name, glyph, role, selected=(i == 0)),
                          classes="menu-label")
            self._labels.append(label)
            items.append(ListItem(label, id=f"menu-{name.lower()}"))
        maid = _load_maid()
        with Vertical(id="home"):
            with Container(id="header"):
                # banner is centred; maid is on a separate layer, offset to its left,
                # so the maid never shifts MANGO off-centre.
                yield Static(BANNER, id="banner")
                if maid is not None:
                    with Container(id="maid-slot"):
                        yield Image(maid, id="maid")
            with Container(id="menu-wrap"):
                yield ListView(*items, id="menu")
        yield Footer()

    def _markup(self, name: str, glyph: str, role: str, *, selected: bool) -> str:
        color = self.app.mango_colors[role]
        marker = ">" if selected else " "
        body = f"[{color}]{glyph}[/]  {name}"
        # green check next to Login once a MangaDex session exists
        if name == "Login" and getattr(self.app.source, "is_logged_in", False):
            green = self.app.mango_colors["green"]
            body += f"  [{green}]✓[/]"
        if selected:
            body = f"[b]{body}[/]"
        return f"{marker} {body}"

    def _refresh_labels(self) -> None:
        idx = self.query_one("#menu", ListView).index
        for i, (name, glyph, role) in enumerate(MENU):
            self._labels[i].update(self._markup(name, glyph, role, selected=(i == idx)))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._refresh_labels()

    def on_screen_resume(self) -> None:
        # returning from Login: reflect the (possibly new) logged-in checkmark
        self._refresh_labels()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        choice = event.item.id.removeprefix("menu-")
        if choice == "exit":
            self.app.exit()
        elif choice == "search":
            self.app.push_screen("search")
        elif choice == "library":
            self.app.push_screen("library")
        elif choice == "login":
            self.app.push_screen("login")
        elif choice == "downloads":
            self.app.push_screen("downloads")
        else:
            self.app.bell()
