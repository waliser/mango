from __future__ import annotations
import httpx
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Button, Static, Footer
from mango.services.importer import LibraryImporter


class LoginScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    CSS = """
    #login { width: 60; height: auto; align: center middle; padding: 1 2; }
    #login Input { margin-bottom: 1; }
    #login-status { height: auto; color: $accent; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="login"):
            yield Static("Log in to MangaDex (personal API client)")
            yield Input(placeholder="client_id", id="client_id")
            yield Input(placeholder="client_secret", password=True, id="client_secret")
            yield Input(placeholder="username", id="username")
            yield Input(placeholder="password", password=True, id="password")
            yield Button("Log in & import", id="submit", variant="primary")
            yield Static("", id="login-status")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        await self._submit()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self._submit()

    async def _submit(self) -> None:
        status = self.query_one("#login-status", Static)

        def val(wid: str) -> str:
            return self.query_one(f"#{wid}", Input).value.strip()

        cid, sec = val("client_id"), val("client_secret")
        user, pw = val("username"), val("password")
        if not all([cid, sec, user, pw]):
            status.update("All four fields are required.")
            return
        status.update("Logging in…")
        try:
            await self.app.source.login(
                client_id=cid, client_secret=sec, username=user, password=pw,
            )
        except httpx.HTTPStatusError:
            status.update("Login failed — check your credentials / client status.")
            return
        except httpx.HTTPError as exc:
            status.update(f"Network error: {exc}")
            return
        status.update("Logged in. Importing library…")
        try:
            count = await LibraryImporter(self.app.source, self.app.library).run()
        except httpx.HTTPError as exc:
            status.update(f"Logged in, but import failed: {exc}")
            return
        self.app.notify(f"Imported {count} titles into your library.")
        self.app.pop_screen()  # back to Home (now showing the logged-in checkmark)
