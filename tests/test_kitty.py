from mango.render.kitty import encode_image


def test_encode_emits_kitty_graphics_sequence():
    seq = encode_image(b"\x89PNG\r\n\x1a\nFAKEPNGDATA", cols=20, rows=30)
    # kitty graphics: ESC _G ... ESC \  ; transmit+display action a=T, PNG format f=100
    assert seq.startswith("\x1b_G")
    assert seq.endswith("\x1b\\")
    assert "f=100" in seq and "a=T" in seq
    assert "c=20" in seq and "r=30" in seq
