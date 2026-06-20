from __future__ import annotations
import os
import sys
from mango.tui.app import MangoApp


def main() -> None:
    if os.environ.get("TERM") != "xterm-kitty" and "KITTY_WINDOW_ID" not in os.environ:
        print("mango requires the kitty terminal (graphics protocol).", file=sys.stderr)
        sys.exit(1)
    MangoApp().run()


if __name__ == "__main__":
    main()
