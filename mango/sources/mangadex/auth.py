from __future__ import annotations
import time
from dataclasses import dataclass
import httpx

AUTH_URL = (
    "https://auth.mangadex.org/realms/mangadex/protocol/openid-connect/token"
)


@dataclass
class AuthSession:
    access_token: str
    refresh_token: str
    client_id: str
    client_secret: str
    expires_at: float  # epoch seconds when the access token expires


def _session_from_response(data: dict, client_id: str, client_secret: str) -> AuthSession:
    # refresh 30s early to avoid edge-of-expiry 401s
    expires_at = time.time() + float(data.get("expires_in", 900)) - 30
    return AuthSession(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        client_id=client_id,
        client_secret=client_secret,
        expires_at=expires_at,
    )


async def login(client: httpx.AsyncClient, *, client_id: str, client_secret: str,
                username: str, password: str) -> AuthSession:
    resp = await client.post(AUTH_URL, data={
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    resp.raise_for_status()
    return _session_from_response(resp.json(), client_id, client_secret)


async def refresh(client: httpx.AsyncClient, session: AuthSession) -> AuthSession:
    resp = await client.post(AUTH_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": session.refresh_token,
        "client_id": session.client_id,
        "client_secret": session.client_secret,
    })
    resp.raise_for_status()
    return _session_from_response(resp.json(), session.client_id, session.client_secret)
