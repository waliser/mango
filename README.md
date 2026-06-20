# mango

Terminal manga reader. Pulls from MangaDex and draws pages inline with kitty's
graphics protocol, so chapters show up as actual images instead of ascii.

It only runs in kitty — it checks `$TERM` on startup and bails out otherwise.

## Install

From source:

```
git clone https://github.com/waliser/mango
cd mango
pip install .
```

Arch (AUR):

```
yay -S mango
```

Then run `mango` (or `mango-tui`, same thing).

## What it does

- search MangaDex and read chapters
- a local library with the usual reading states (reading, completed, on hold, plan to read, dropped, re-reading)
- download chapters to read offline
- optional MangaDex login, only used to import the titles you already follow

## Keys

The home screen is a menu — arrows to move, enter to pick. Inside the screens:

| screen    | keys                                              |
|-----------|---------------------------------------------------|
| reader    | `h`/`l` or arrows to flip pages, `n` next chapter |
| search    | type to search, `enter` to open, `a` to add it    |
| library   | arrows to move, `enter` to open, `r` to refresh   |
| chapters  | `enter` to read, `d` to download                  |
| downloads | `enter` to read, `x` to delete, `r` to re-fetch   |
| anywhere  | `esc` goes back, `q` quits                         |

## Where it keeps things

Follows the XDG dirs:

- config — `~/.config/mango`
- library db + data — `~/.local/share/mango`
- downloads — `~/.local/share/mango/downloads`
- cache — `~/.cache/mango`

Login is optional. If you want it, make a "personal API client" in your MangaDex
account settings and log in from the app. The tokens are written to
`~/.local/share/mango/auth.json` with `600` perms and never leave your machine.

## Hacking on it

```
pip install -e ".[dev]"
pytest
```

Sources live behind a small `Source` interface (`mango/sources/`), MangaDex being
the only one implemented so far. Rendering is in `mango/render/`, screens in
`mango/tui/screens/`.

## License

MIT — see [LICENSE](LICENSE).
