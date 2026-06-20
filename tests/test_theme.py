import json
from mango.theme import load_matugen_colors, build_theme


def test_load_falls_back_when_file_missing(tmp_path):
    colors = load_matugen_colors(tmp_path / "nope.json")
    # complete palette even with no file
    assert colors["blue"].startswith("#")
    assert colors["base"].startswith("#")


def test_load_reads_file_and_fills_missing_roles(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"blue": "#123456", "green": "#abcdef"}))
    colors = load_matugen_colors(p)
    assert colors["blue"] == "#123456"
    assert colors["green"] == "#abcdef"
    # a role absent from the file is filled from the fallback
    assert colors["base"].startswith("#")


def test_build_theme_maps_roles_and_pastel_accent():
    from mango.theme import _lighten, ACCENT_LIGHTEN
    colors = load_matugen_colors(None)
    colors["blue"], colors["green"], colors["peach"] = "#111111", "#222222", "#333333"
    theme = build_theme(colors)
    assert theme.name == "mango-auto"
    assert theme.primary == "#111111"
    assert theme.secondary == "#222222"
    # accent is the primary lightened toward white (pastel), not the tertiary
    assert theme.accent == _lighten("#111111", ACCENT_LIGHTEN)
    assert theme.accent != "#333333"
