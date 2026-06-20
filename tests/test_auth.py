import time
import httpx
import respx
import pytest
from mango.sources.mangadex.auth import AuthSession, login, refresh, AUTH_URL


@respx.mock
async def test_login_posts_password_grant_and_parses_tokens():
    route = respx.post(AUTH_URL).mock(return_value=httpx.Response(200, json={
        "access_token": "AT", "refresh_token": "RT", "expires_in": 900,
    }))
    async with httpx.AsyncClient() as client:
        s = await login(client, client_id="cid", client_secret="sec",
                        username="u", password="p")
    form = dict(httpx.QueryParams(route.calls[0].request.content.decode()))
    assert form["grant_type"] == "password"
    assert form["username"] == "u" and form["client_id"] == "cid"
    assert s.access_token == "AT" and s.refresh_token == "RT"
    assert s.client_id == "cid" and s.client_secret == "sec"
    assert s.expires_at > time.time()


@respx.mock
async def test_refresh_uses_refresh_token_grant():
    respx.post(AUTH_URL).mock(return_value=httpx.Response(200, json={
        "access_token": "AT2", "refresh_token": "RT2", "expires_in": 900,
    }))
    old = AuthSession("AT", "RT", "cid", "sec", expires_at=0.0)
    async with httpx.AsyncClient() as client:
        s = await refresh(client, old)
    assert s.access_token == "AT2" and s.refresh_token == "RT2"
    assert s.client_id == "cid"  # carried over
