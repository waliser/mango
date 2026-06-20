import httpx
import respx
import pytest
from mango.sources.mangadex.client import MangaDexClient


@respx.mock
async def test_get_retries_on_429_then_succeeds():
    route = respx.get("https://api.mangadex.org/ping").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    client = MangaDexClient(base_url="https://api.mangadex.org")
    data = await client.get_json("/ping")
    await client.aclose()
    assert data == {"ok": True}
    assert route.call_count == 2
    assert "mango" in route.calls[0].request.headers["user-agent"].lower()
