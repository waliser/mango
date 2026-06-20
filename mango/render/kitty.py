from __future__ import annotations
import base64


def encode_image(png_bytes: bytes, *, cols: int, rows: int) -> str:
    """Encode PNG bytes as a kitty graphics escape sequence that transmits and
    displays the image sized to `cols` x `rows` terminal cells.

    Uses chunked transmission (m=1 until the final chunk) per the kitty
    graphics protocol so large images don't overflow escape-sequence limits.
    """
    payload = base64.standard_b64encode(png_bytes).decode("ascii")
    chunk_size = 4096
    chunks = [payload[i:i + chunk_size] for i in range(0, len(payload), chunk_size)] or [""]
    out: list[str] = []
    for idx, chunk in enumerate(chunks):
        first = idx == 0
        last = idx == len(chunks) - 1
        if first:
            ctrl = f"a=T,f=100,c={cols},r={rows},m={0 if last else 1}"
        else:
            ctrl = f"m={0 if last else 1}"
        out.append(f"\x1b_G{ctrl};{chunk}\x1b\\")
    return "".join(out)
