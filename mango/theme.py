from __future__ import annotations
import json
from pathlib import Path
from textual.theme import Theme

# matugen regenerates this structured palette on every profile/wallpaper change.
DEFAULT_MATUGEN_JSON = Path.home() / ".config/hypr/scripts/quickshell/qs_colors.json"

# Fallback palette (used when matugen output is unavailable) so callers always
# get a complete set of keys.
_FALLBACK: dict[str, str] = {
    "base": "#100d12", "mantle": "#1e1a20", "crust": "#151218",
    "text": "#e8e0e8", "subtext0": "#ccc4cf",
    "surface0": "#221e24", "surface1": "#2c292e", "surface2": "#373339",
    "blue": "#dabafa", "green": "#d0c1da", "peach": "#f3b7bf",
    "red": "#ffb4ab", "accentDeep": "#7d20d3",
}


def load_matugen_colors(path: Path | None = None) -> dict[str, str]:
    """Load matugen's quickshell color JSON merged over fallbacks. Always returns
    a complete palette, so callers never KeyError on a missing role."""
    colors = dict(_FALLBACK)
    p = Path(path) if path is not None else DEFAULT_MATUGEN_JSON
    try:
        colors.update(json.loads(p.read_text()))
    except (OSError, json.JSONDecodeError):
        pass
    return colors


ACCENT_LIGHTEN = 0.25  # how far the accent is pushed toward white from primary


def _lighten(hex_color: str, amount: float) -> str:
    """Blend a #rrggbb colour toward white by `amount` (0..1) for a pastel tint."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = round(r + (255 - r) * amount)
    g = round(g + (255 - g) * amount)
    b = round(b + (255 - b) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def build_theme(colors: dict[str, str], name: str = "mango-auto") -> Theme:
    """Build a Textual theme from a matugen palette.

    Role mapping: primary=blue, secondary=green, accent=a pastel-lightened primary
    (so accents track the profile's primary colour rather than the tertiary).
    """
    accent = _lighten(colors["blue"], ACCENT_LIGHTEN)
    return Theme(
        name=name,
        primary=colors["blue"],
        secondary=colors["green"],
        accent=accent,
        foreground=colors["text"],
        background=colors["base"],
        surface=colors["surface0"],
        panel=colors["surface1"],
        error=colors["red"],
        success=colors["green"],
        warning=colors["peach"],
        dark=True,
        variables={
            "block-cursor-background": colors["blue"],
            "block-cursor-foreground": colors["base"],
            "footer-key-foreground": accent,
            "footer-description-foreground": colors["subtext0"],
        },
    )
